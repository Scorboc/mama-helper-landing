import { demoAnswer, emptyState, ParentState } from './parent-model';

export type Session = {user:{id:string;email:string};state:ParentState;revision:number;recoveryCode?:string};
type LocalAccount = {id:string;email:string;salt:string;passwordHash:string;recoveryHash:string;state:ParentState;revision:number};

const ACCOUNTS_KEY='mh_local_accounts_v1';
const SESSION_KEY='mh_local_session_v1';
let endpoint:Promise<string|null>|undefined;

export class ApiError extends Error { constructor(message:string,public status:number){super(message);} }

async function apiUrl(){
  endpoint ??= fetch('/app-config.json',{cache:'no-store'}).then(async r=>{
    if(!r.ok)throw new Error();
    const config=await r.json();
    const url=import.meta.env.VITE_APP_API_URL || config.apiUrl;
    if(!url)return null;
    if(typeof url!=='string')throw new Error();
    const parsed=new URL(url,window.location.origin);
    if(parsed.protocol!=='https:' && parsed.hostname!=='localhost' && parsed.hostname!=='127.0.0.1')throw new Error();
    return parsed.href;
  }).catch(()=>{endpoint=undefined;throw new ApiError('Не удалось подключиться к сервису аккаунтов. Попробуйте позже.',503);});
  return endpoint;
}

function readAccounts():LocalAccount[]{
  try{const parsed=JSON.parse(localStorage.getItem(ACCOUNTS_KEY)||'[]');return Array.isArray(parsed)?parsed:[];}
  catch{return [];}
}

function writeAccounts(accounts:LocalAccount[]){
  try{localStorage.setItem(ACCOUNTS_KEY,JSON.stringify(accounts));}
  catch{throw new ApiError('Браузер не разрешил сохранить данные. Проверьте настройки приватности.',503);}
}

function randomToken(bytes=18){
  const data=crypto.getRandomValues(new Uint8Array(bytes));
  return Array.from(data,b=>b.toString(16).padStart(2,'0')).join('');
}

async function hash(value:string,salt:string){
  const data=new TextEncoder().encode(`${salt}:${value}`);
  const digest=await crypto.subtle.digest('SHA-256',data);
  return Array.from(new Uint8Array(digest),b=>b.toString(16).padStart(2,'0')).join('');
}

function recoveryCode(){return Array.from({length:4},()=>randomToken(3).toUpperCase()).join('-');}

async function ensureDemoAccount(){
  const accounts=readAccounts();
  if(accounts.some(a=>a.email==='1'))return;
  const salt=randomToken();
  accounts.push({id:'demo-account',email:'1',salt,passwordHash:await hash('1',salt),recoveryHash:'',state:emptyState(),revision:0});
  writeAccounts(accounts);
}

function activeAccount(accounts=readAccounts()){
  const id=localStorage.getItem(SESSION_KEY);
  return accounts.find(a=>a.id===id);
}

function publicSession(account:LocalAccount,recovery?:string):Session{
  return {user:{id:account.id,email:account.email},state:account.state,revision:account.revision,...(recovery?{recoveryCode:recovery}:{})};
}

async function localApi<T>(action:string,data:Record<string,unknown>):Promise<T>{
  await ensureDemoAccount();
  let accounts=readAccounts();
  if(action==='register'){
    const email=String(data.email||'').trim().toLowerCase();const password=String(data.password||'');
    if(!data.consent)throw new ApiError('Подтвердите согласие с условиями тестирования.',400);
    if(!/^\S+@\S+\.\S+$/.test(email))throw new ApiError('Укажите корректную электронную почту.',400);
    if(password.length<12)throw new ApiError('Пароль должен содержать не меньше 12 символов.',400);
    if(accounts.some(a=>a.email===email))throw new ApiError('Аккаунт с такой почтой уже существует.',409);
    const salt=randomToken();const code=recoveryCode();
    const account:LocalAccount={id:crypto.randomUUID(),email,salt,passwordHash:await hash(password,salt),recoveryHash:await hash(code,salt),state:emptyState(),revision:0};
    accounts.push(account);writeAccounts(accounts);localStorage.setItem(SESSION_KEY,account.id);
    return publicSession(account,code) as T;
  }
  if(action==='login'){
    const email=String(data.email||'').trim().toLowerCase();const account=accounts.find(a=>a.email===email);
    if(!account||await hash(String(data.password||''),account.salt)!==account.passwordHash)throw new ApiError('Неверная почта или пароль.',401);
    localStorage.setItem(SESSION_KEY,account.id);return publicSession(account) as T;
  }
  if(action==='recover'){
    const email=String(data.email||'').trim().toLowerCase();const account=accounts.find(a=>a.email===email);const password=String(data.password||'');
    if(!account||!account.recoveryHash||await hash(String(data.recoveryCode||'').trim().toUpperCase(),account.salt)!==account.recoveryHash)throw new ApiError('Почта или код восстановления не совпадают.',401);
    if(password.length<12)throw new ApiError('Новый пароль должен содержать не меньше 12 символов.',400);
    const code=recoveryCode();account.passwordHash=await hash(password,account.salt);account.recoveryHash=await hash(code,account.salt);
    writeAccounts(accounts);localStorage.setItem(SESSION_KEY,account.id);return publicSession(account,code) as T;
  }
  if(action==='session'){
    const account=activeAccount(accounts);if(!account)throw new ApiError('Войдите в аккаунт.',401);return publicSession(account) as T;
  }
  if(action==='logout'){localStorage.removeItem(SESSION_KEY);return {ok:true} as T;}
  const account=activeAccount(accounts);if(!account)throw new ApiError('Войдите в аккаунт.',401);
  if(action==='save'){
    if(Number(data.revision)!==account.revision)throw new ApiError('Данные изменились в другой вкладке. Обновите страницу.',409);
    account.state=data.state as ParentState;account.revision+=1;writeAccounts(accounts);return {revision:account.revision} as T;
  }
  if(action==='chat')return {answer:demoAnswer(String(data.question||''),account.state.profile)} as T;
  if(action==='config')return {ok:true,chatConfigured:false,pushKey:'',storage:'local'} as T;
  if(action==='subscribe'||action==='unsubscribe')return {ok:true} as T;
  if(action==='health')return {ok:true,storage:'local'} as T;
  if(action==='delete'){
    if(await hash(String(data.password||''),account.salt)!==account.passwordHash)throw new ApiError('Неверный пароль.',401);
    accounts=accounts.filter(a=>a.id!==account.id);writeAccounts(accounts);localStorage.removeItem(SESSION_KEY);return {ok:true} as T;
  }
  throw new ApiError('Неизвестное действие.',400);
}

export async function api<T>(action:string,data:Record<string,unknown>={},timeoutMs=15000):Promise<T>{
  const url=await apiUrl();
  if(!url)return localApi<T>(action,data);
  const controller=new AbortController();const timer=window.setTimeout(()=>controller.abort(),timeoutMs);
  try{
    const response=await fetch(url,{method:'POST',credentials:'include',headers:{'Content-Type':'application/json'},body:JSON.stringify({action,...data}),signal:controller.signal});
    const body=await response.json();
    if(!response.ok)throw new ApiError(typeof body.error==='string'?body.error:'Не удалось выполнить действие.',response.status);
    return body as T;
  }catch(error){if(error instanceof ApiError)throw error;throw new ApiError('Нет связи с сервером. Проверьте подключение. Изменения могли не сохраниться.',503);}
  finally{window.clearTimeout(timer);}
}
