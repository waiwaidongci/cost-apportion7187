from fastapi import APIRouter,Depends,HTTPException
from fastapi.responses import Response
from src.config.database import database
from src.controllers.auth import current,editor,admin
from src.models.release import ReleaseProfile,Release
from src.schemas.requests import ProfileInput,ReleaseInput
from src.services import release as svc
from src.services.export import csv_text
from src.utils.serialize import row
router=APIRouter()
@router.get('/release-profiles')
def profiles(db=Depends(database),u=Depends(current)): return [row(x) for x in db.query(ReleaseProfile).order_by(ReleaseProfile.id).all()]
@router.post('/release-profiles')
def save_profile(b:ProfileInput,db=Depends(database),u=Depends(admin)): return row(svc.save_profile(db,u,b))
@router.get('/releases')
def releases(db=Depends(database),u=Depends(current)):
 items=db.query(Release).order_by(Release.id.desc()).limit(200).all()
 if u.role=='viewer': items=[x for x in items if x.status!='rejected']
 return [row(x) for x in items]
@router.post('/releases')
def publish(b:ReleaseInput,db=Depends(database),u=Depends(editor)): return row(svc.publish(db,u,b))
@router.get('/releases/verify/{checksum}')
def verify(checksum:str,db=Depends(database),u=Depends(editor)): return svc.verify(db,u,checksum)
@router.post('/releases/{id}/withdraw')
def withdraw(id:int,db=Depends(database),u=Depends(admin)): return row(svc.withdraw(db,u,id))
@router.get('/releases/{id}/csv')
def download(id:int,db=Depends(database),u=Depends(current)):
 obj=db.get(Release,id)
 if not obj or obj.status=='rejected': raise HTTPException(404,'发布记录不存在')
 if obj.status=='withdrawn': raise HTTPException(409,'该发布已撤回，不可下载')
 return Response(csv_text(obj.payload),media_type='text/csv',headers={'Content-Disposition':f'attachment; filename="release-{id}.csv"'})
