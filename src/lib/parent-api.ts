import { ParentState } from './parent-model';
export type Session = {user:{id:string;email:string};state:ParentState;revision:number;recoveryCode?:string};
let endpoint:Promise<string>|undefined;
export class ApiError extends Error { constructor(message:string,public status:number){super(message);} }
async function apiUrl(){
  endpoint ??= fetch('/app-config.json',{cache:'no-store'}).then(async r=>{
    if(!r.ok)throw new Error(); const config=await r.json();
    const url=import.meta.env.VITE_APP_API_URL || config.apiUrl;
    if(typeof url!=='string'||!url)throw new ApiError('Сервис аккаунтов ещё не настроен. Попробуйте позже.',503);
    const parsed=new URL(url,window.location.origin);
    if(parsed.protocol!=='https:' && parsed.hostname!=='localhost' && parsed.hostname!=='127.0.0.1')throw new Error();
    return parsed.href;
  }).catch(error=>{endpoint=undefined;throw error instanceof ApiError?error:new ApiError('Не удалось подключиться к сервису аккаунтов. Попробуйте позже.',503);});
  return endpoint;
}
export async function api<T>(action:string,data:Record<string,unknown>={},timeoutMs=15000):Promise<T>{
  const url=await apiUrl();
  const controller=new AbortController();const timer=window.setTimeout(()=>controller.abort(),timeoutMs);
  try{
    const response=await fetch(url,{method:'POST',credentials:'include',headers:{'Content-Type':'application/json'},body:JSON.stringify({action,...data}),signal:controller.signal});
    const body=await response.json();
    if(!response.ok)throw new ApiError(typeof body.error==='string'?body.error:'Не удалось выполнить действие.',response.status);
    return body as T;
  }catch(error){if(error instanceof ApiError)throw error;throw new ApiError('Нет связи с сервером. Проверьте подключение. Изменения могли не сохраниться.',503);}
  finally{window.clearTimeout(timer);}
}