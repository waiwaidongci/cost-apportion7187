import time
from fractions import Fraction
from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError
from src.models.run import Run
from src.models.release import ReleaseProfile,Release
from src.services.audit import log
from src.services.release_math import parse_coefficient,department_amounts,adjudicate
from src.services import release_verify
ACTIVE=('published','withdrawn')
def departments_of(run):
 amounts=department_amounts(run.result)
 if not amounts: raise HTTPException(409,'报告尚无部门透视结果')
 return sorted(amounts),amounts
def equations_of(db,checksum):
 """同版历史发布（含已撤回）方程：撤回记录仍参与联立检查。"""
 rows=db.query(Release).filter(Release.checksum==checksum,Release.status.in_(ACTIVE)).order_by(Release.id).all()
 return [{'coefficients':{d:parse_coefficient(c) for d,c in x.coefficients.items()},'value':Fraction(x.value),'label':f'#{x.id} {x.name}'} for x in rows]
def save_profile(db,user,body):
 run=db.get(Run,body.run_id)
 if not run or run.status!='completed': raise HTTPException(409,'仅可为已完成报告配置保密部门')
 departments,_=departments_of(run)
 confidential=[]
 for name in body.confidential:
  if name not in departments: raise HTTPException(422,f'部门「{name}」不在该冻结版本中')
  if name not in confidential: confidential.append(name)
 obj=db.query(ReleaseProfile).filter_by(checksum=run.checksum).first();now=time.time()
 if obj:
  obj.run_id=run.id;obj.departments=departments;obj.confidential=confidential;obj.note=body.note;obj.updated=now
 else:
  obj=ReleaseProfile(checksum=run.checksum,run_id=run.id,departments=departments,confidential=confidential,note=body.note,created=now,updated=now)
  db.add(obj)
 log(db,user.email,'release.profile.save',f"{run.checksum[:12]} 保密部门:{'、'.join(confidential) or '无'}")
 db.commit();return obj
def _normalize(body):
 parsed={}
 for name,raw in body.coefficients.items():
  coef=parse_coefficient(raw)
  if coef: parsed[name]=coef
 return parsed
def _check_dup(dup,run_id,parsed):
 if dup.run_id!=run_id or dup.coefficients!={d:str(c) for d,c in parsed.items()}: raise HTTPException(409,'幂等键已被其他请求使用')
 return dup
def publish(db,user,body):
 run=db.get(Run,body.run_id)
 if not run or run.status!='completed': raise HTTPException(409,'仅可引用已完成报告')
 checksum=run.checksum;parsed=_normalize(body)
 dup=db.query(Release).filter_by(request_key=body.request_key).first()
 if dup: return _check_dup(dup,run.id,parsed)
 profile=db.query(ReleaseProfile).filter_by(checksum=checksum).with_for_update().first()
 if not profile: raise HTTPException(409,'该冻结版本尚未配置保密部门，请先在组合发布页配置')
 dup=db.query(Release).filter_by(request_key=body.request_key).first()
 if dup: return _check_dup(dup,run.id,parsed)
 departments=profile.departments
 for name in parsed:
  if name not in departments: raise HTTPException(422,f'部门「{name}」不在该冻结版本中')
 if not parsed: raise HTTPException(422,'至少需要一个非零系数')
 _,amounts=departments_of(run)
 value=sum((coef*amounts[name] for name,coef in parsed.items()),Fraction(0))
 history=equations_of(db,checksum)
 candidate={'coefficients':parsed,'value':value,'label':'本次组合'}
 decision=adjudicate(departments,profile.confidential,history,candidate)
 if decision['allowed']:
  status='published';derivation=[]
  reason='与历史发布线性相关，未新增可解信息，放行' if decision['dependent'] else f'联立{len(history)}条历史发布后未唯一解出任何保密部门，放行'
 else:
  status='rejected';derivation=decision['leaks']
  reason=f"联立{len(history)}条历史发布与本次组合后可唯一解出保密部门{'、'.join('「'+x['department']+'」' for x in decision['leaks'])}，拒绝"
 payload=None
 if status=='published':
  rows=[{'条目':'发布名称','内容':body.name},{'条目':'口径版本','内容':run.snapshot['policy']['version']},{'条目':'冻结校验','内容':checksum}]
  rows+=[{'条目':f'系数·{d}','内容':str(c)} for d,c in parsed.items()]
  rows+=[{'条目':'组合金额（分）','内容':str(value)}]
  payload={'rows':rows,'name':body.name,'value':str(value)}
 obj=Release(request_key=body.request_key,checksum=checksum,run_id=run.id,name=body.name,coefficients={d:str(c) for d,c in parsed.items()},value=str(value),status=status,reason=reason,derivation=derivation,payload=payload,created=time.time(),created_by=user.email)
 db.add(obj);log(db,user.email,'release.publish' if status=='published' else 'release.reject',f'{body.name} → {reason}')
 try: db.commit()
 except IntegrityError:
  db.rollback()
  dup=db.query(Release).filter_by(request_key=body.request_key).first()
  if dup: return _check_dup(dup,run.id,parsed)
  raise
 return obj
def withdraw(db,user,id):
 obj=db.get(Release,id)
 if not obj: raise HTTPException(404,'发布记录不存在')
 if obj.status!='published': raise HTTPException(409,'仅可撤回已发布记录')
 obj.status='withdrawn';obj.withdrawn=time.time();obj.withdrawn_by=user.email
 log(db,user.email,'release.withdraw',f'#{id} {obj.name}（方程仍参与后续联立检查）')
 db.commit();return obj
def verify(db,user,checksum):
 profile=db.query(ReleaseProfile).filter_by(checksum=checksum).first()
 if not profile: raise HTTPException(404,'该冻结版本尚未配置保密部门')
 equations=equations_of(db,checksum)
 result=release_verify.verify(profile.departments,profile.confidential,equations)
 verdict='safe' if not result['leaks'] else 'leaked'
 log(db,user.email,'release.verify',f'{checksum[:12]} → {verdict}（{len(equations)}条方程）');db.commit()
 return {'checksum':checksum,'departments':profile.departments,'confidential':profile.confidential,'equations':len(equations),'rank':result['rank'],'verdict':verdict,'leaks':result['leaks']}
def guard_viewer_download(db,checksum):
 """阅读者原有取数入口遵守同一限制：已配置保密部门的冻结版本关闭整表下载。"""
 profile=db.query(ReleaseProfile).filter_by(checksum=checksum).first()
 if profile and profile.confidential: raise HTTPException(403,'该冻结版本已配置保密部门，整表下载已关闭，请改用组合发布')
