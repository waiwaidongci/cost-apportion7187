from fractions import Fraction
def parse_coefficient(value):
 """解析有理数系数：接受整数字符串、小数字符串或 p/q 分数，拒绝布尔与非法值。"""
 if isinstance(value,bool): raise ValueError('系数不合法')
 if isinstance(value,(int,float)): value=str(value)
 if not isinstance(value,str) or not value.strip(): raise ValueError('系数不能为空')
 text=value.strip()
 try: result=Fraction(text)
 except Exception: raise ValueError(f'系数「{text}」不是合法有理数')
 if abs(result.numerator)>10**18 or result.denominator>10**18: raise ValueError('系数分子或分母过大')
 return result
def department_amounts(result):
 """从冻结报告结果按部门汇总整数分金额。"""
 amounts={}
 for row in (result or {}).get('rows',[]):
  dept,cents=row.get('部门'),row.get('分摊金额分')
  if isinstance(dept,str) and isinstance(cents,int) and not isinstance(cents,bool): amounts[dept]=amounts.get(dept,0)+cents
 return amounts
class RowSpace:
 """精确有理数行空间：每个基向量记录其对应的原始方程组合，用于给出泄密推导。"""
 def __init__(self,width,size):
  self.width=width;self.size=size;self.basis={}
 def _reduce(self,vector,combo,sign):
  vector={k:v for k,v in vector.items() if v};combo=list(combo)
  while True:
   shared=[c for c in vector if c in self.basis]
   if not shared: return vector,combo
   col=min(shared);pv,pc=self.basis[col];factor=vector[col]
   for k,v in pv.items():
    rest=vector.get(k,Fraction(0))-factor*v
    if rest: vector[k]=rest
    else: vector.pop(k,None)
   combo=[a+sign*factor*b for a,b in zip(combo,pc)]
 def add(self,vector,combo):
  vector,combo=self._reduce(vector,combo,-1)
  if not vector: return False
  col=min(vector);unit=vector[col]
  self.basis[col]=({k:v/unit for k,v in vector.items()},[x/unit for x in combo])
  return True
 def express(self,vector):
  residual,combo=self._reduce(vector,[Fraction(0)]*self.size,1)
  return None if residual else combo
def adjudicate(departments,confidential,equations,candidate):
 """联立同版历史发布与本次组合做精确消元裁决。
 equations/candidate形如{'coefficients':{部门:Fraction},'value':Fraction,'label':str}；
 任一保密部门单位向量落入行空间即判定可唯一解出，返回放行结论与泄密推导。"""
 index={name:i for i,name in enumerate(departments)}
 all_eqs=list(equations)+[candidate]
 space=RowSpace(len(departments),len(all_eqs));dependent=False
 for i,eq in enumerate(all_eqs):
  vector={index[d]:c for d,c in eq['coefficients'].items()}
  combo=[Fraction(1) if j==i else Fraction(0) for j in range(len(all_eqs))]
  if not space.add(vector,combo) and i==len(all_eqs)-1: dependent=True
 leaks=[]
 for dept in confidential:
  col=index.get(dept)
  if col is None: continue
  combo=space.express({col:Fraction(1)})
  if combo is None: continue
  value=sum((a*eq['value'] for a,eq in zip(combo,all_eqs)),Fraction(0))
  steps=[{'label':eq['label'],'coefficient':str(a)} for a,eq in zip(combo,all_eqs) if a]
  leaks.append({'department':dept,'value':str(value),'combination':steps})
 return {'allowed':not leaks,'dependent':dependent,'rank':len(space.basis),'leaks':leaks}
