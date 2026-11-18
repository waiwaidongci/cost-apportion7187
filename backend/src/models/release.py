from sqlalchemy import Column,Integer,String,JSON,Text,Float
from src.config.database import Base
class ReleaseProfile(Base):
 __tablename__='release_profiles'
 id=Column(Integer,primary_key=True); checksum=Column(String(64),unique=True); run_id=Column(Integer)
 departments=Column(JSON); confidential=Column(JSON); note=Column(Text,default='')
 created=Column(Float); updated=Column(Float)
class Release(Base):
 __tablename__='release_publications'
 id=Column(Integer,primary_key=True); request_key=Column(String(80),unique=True); checksum=Column(String(64))
 run_id=Column(Integer); name=Column(String(120)); coefficients=Column(JSON); value=Column(Text)
 status=Column(String(20)); reason=Column(Text,default=''); derivation=Column(JSON); payload=Column(JSON)
 created=Column(Float); created_by=Column(String(120)); withdrawn=Column(Float); withdrawn_by=Column(String(120),default='')
