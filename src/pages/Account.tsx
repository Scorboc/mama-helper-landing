import { FormEvent, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { Heart, ArrowLeft, Eye, EyeOff } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Checkbox } from '@/components/ui/checkbox';
import { Tabs, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { api, Session } from '@/lib/parent-api';
import { Fox } from '@/components/Critters';
import './parent-app.css';
import './calm-theme.css';

export default function Account(){
  const [mode,setMode]=useState('register');const [email,setEmail]=useState('');
  const [password,setPassword]=useState('');const [recovery,setRecovery]=useState('');
  const [consent,setConsent]=useState(false);const [visible,setVisible]=useState(false);
  const [busy,setBusy]=useState(false);const [error,setError]=useState('');const [newCode,setNewCode]=useState('');
  const navigate=useNavigate();
  async function submit(e:FormEvent){e.preventDefault();if(busy)return;setBusy(true);setError('');
    try{
      if(mode==='login'&&email.trim()==='логин-1'&&password==='1'){
        sessionStorage.setItem('mh_demo_access','1');setPassword('');navigate('/demo');return;
      }
      const result=await api<Session>(mode,{email,password,consent,recoveryCode:recovery});setPassword('');setRecovery('');
      if(result.recoveryCode)setNewCode(result.recoveryCode);else navigate('/cabinet');
    }catch(err){setError((err as Error).message);}finally{setBusy(false);}
  }
  return <main className="account-page"><Link className="back-link" to="/"><ArrowLeft size={18}/> На главную</Link><div className="account-card tile">
    <Fox className="mx-auto mb-4 h-20 w-20"/><h1>{newCode?'Ваш аккаунт готов':'Своя маленькая опора'}</h1><p className="muted">Личный кабинет для мам и пап. На время теста — без оплаты.</p>
    {newCode?<div className="space-y-4 mt-6"><h2>Сохраните код восстановления</h2><p>Письма пока не отправляются. Этот личный код позволит сменить пароль. Храните его отдельно и никому не передавайте.</p><code className="recovery-code">{newCode}</code><p className="muted">Код показывается один раз. После восстановления прежний код больше не работает.</p><Button className="w-full" onClick={()=>{setNewCode('');navigate('/cabinet');}}>Код сохранён — перейти в кабинет</Button></div>:<>
    <Tabs value={mode} onValueChange={v=>{setMode(v);setError('');}} className="mt-6"><TabsList className="w-full"><TabsTrigger value="register" className="flex-1">Регистрация</TabsTrigger><TabsTrigger value="login" className="flex-1">Вход</TabsTrigger><TabsTrigger value="recover" className="flex-1">Восстановить</TabsTrigger></TabsList></Tabs>
    <form onSubmit={submit} className="space-y-5 mt-6"><label className="form-field">{mode==='login'?'Почта или тестовый логин':'Электронная почта'}<Input type={mode==='login'?'text':'email'} autoComplete={mode==='login'?'username':'email'} required maxLength={254} value={email} onChange={e=>setEmail(e.target.value)} placeholder={mode==='login'?'Например, логин-1':''}/></label>
    {mode==='recover'&&<label className="form-field">Личный код восстановления<Input autoComplete="off" value={recovery} onChange={e=>setRecovery(e.target.value)} required maxLength={100}/></label>}
    <label className="form-field">{mode==='recover'?'Новый пароль':'Пароль'}<div className="password-field"><Input type={visible?'text':'password'} required minLength={mode==='login'?1:12} maxLength={128} autoComplete={mode==='login'?'current-password':'new-password'} value={password} onChange={e=>setPassword(e.target.value)}/><button type="button" onClick={()=>setVisible(v=>!v)} aria-label={visible?'Скрыть пароль':'Показать пароль'}>{visible?<EyeOff size={19}/>:<Eye size={19}/>}</button></div><span className="muted text-sm">{mode==='login'?'Для тестового входа: логин-1 и пароль 1. Для личного аккаунта — от 12 символов.':'От 12 символов. Можно использовать длинную фразу.'}</span></label>
    {mode==='register'&&<div className="flex gap-3 items-start"><Checkbox id="consent" checked={consent} onCheckedChange={v=>setConsent(v===true)}/><label htmlFor="consent" className="text-sm leading-relaxed">Мне исполнилось 18 лет. Я принимаю <Link to="/privacy" className="underline">условия тестирования и обработки данных</Link>.</label></div>}
    {error&&<p className="form-error" role="alert">{error}</p>}
    <Button className="w-full" type="submit" disabled={busy||(mode==='register'&&!consent)}>{busy?'Подождите…':mode==='register'?'Создать аккаунт':mode==='login'?'Войти':'Восстановить доступ'}</Button></form>
    {mode==='login'&&<p className="text-center text-sm mt-5 text-muted-foreground">Тестовый вход: <strong>логин-1</strong> · пароль: <strong>1</strong></p>}<p className="muted mt-4 text-sm flex gap-2"><Heart size={18} className="shrink-0"/>У каждого свой аккаунт, даже если вы родители одного малыша.</p></>}
  </div></main>;
}
