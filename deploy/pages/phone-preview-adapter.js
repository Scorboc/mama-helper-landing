/* Pages only: no real accounts, uploads, analytics, remote writes or persistent records. */
(() => {
  'use strict';
  const base='/mama-helper-landing/';
  const realFetch=window.fetch.bind(window);
  const demo=globalThis.MamaDemoModel.createDemo(()=>Date.now(),globalThis.MamaDemoHints || {});
  const response=(body,status=200)=>new Response(JSON.stringify(body),{status,headers:{'Content-Type':'application/json'}});
  const target=new URL(location.href).searchParams.get('__route');
  if (target?.startsWith('/') && !target.startsWith('//')) history.replaceState(null,'',base.replace(/\/$/,'')+target);
  window.fetch=async (input,options={})=>{
    const url=new URL(input instanceof URL ? input.href : typeof input==='string' ? input : input.url,location.href);
    if (url.origin!==location.origin) return realFetch(input,options);
    if (url.pathname==='/app-config.json' || url.pathname===base+'app-config.json') return response({apiUrl:base+'__preview-api',publicDemo:true});
    if (url.pathname!==base+'__preview-api') return realFetch(input,options);
    let data;try { data=JSON.parse(options.body || '{}'); } catch { return response({error:'Проверьте запрос.'},400); }
    const result=demo.dispatch(data);return response(result.body,result.status);
  };
  function notice(){
    const aside=document.createElement('aside');aside.id='mama-public-demo-notice';aside.setAttribute('aria-label','Режим демонстрации');
    aside.textContent='Демонстрация MAMA. Используйте вымышленные данные. Записи живут только в памяти этой вкладки и исчезнут после обновления. Настоящие аккаунты, ИИ и оплата не подключены.';
    const style=document.createElement('style');style.textContent='#mama-public-demo-notice{padding:12px 18px;background:#fff8ed;color:#263e35;font:14px/1.5 sans-serif;border-bottom:2px solid #d8c6a5} .room-chat-intro::after{content:" · демо";font-size:11px} @media print{#mama-public-demo-notice{display:none}}';
    document.head.append(style);document.body.prepend(aside);
  }
  if(document.readyState==='loading') document.addEventListener('DOMContentLoaded',notice,{once:true});else notice();
})();
