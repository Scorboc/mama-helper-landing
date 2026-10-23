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
})();
