import {request} from './client.js';
export const loadAll=async()=>{const keys=['sources','periods','policies','runs','schedules','deliveries','audits','releases'];const data=Object.fromEntries(await Promise.all(keys.map(async k=>[k,await request('/'+k)])));data.releaseProfiles=await request('/release-profiles');return data};
export const saveSource=(data,id)=>request('/sources'+(id?'/'+id:''),id?'PUT':'POST',{data});
export const savePolicy=data=>request('/policies','POST',{data});
export const submitRun=data=>request('/runs','POST',data);
export const approveRun=(id,note)=>request('/runs/'+id+'/approve','POST',{note});
export const saveProfile=data=>request('/release-profiles','POST',data);
export const publishRelease=data=>request('/releases','POST',data);
