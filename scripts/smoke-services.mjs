// Dedicated synthetic account. Never reads or changes testers' accounts.
import assert from 'node:assert/strict';
import {emptyCare,makeWeek,localDay} from '../ai-proxy/services.js';
const endpoint=process.env.MAMA_API_URL;
if(!endpoint||new URL(endpoint).protocol!=='https:')throw Error('Set MAMA_API_URL');
const origin='https://mama-helper-landing--preview.poehali.dev';
const password=crypto.randomUUID()+crypto.randomUUID(),email=`qa-${crypto.randomUUID()}@example.invalid`;
let token='',session;const report=[];
async function call(action,data={}){
 const start=performance.now();const r=await fetch(endpoint,{method:'POST',headers:{'Content-Type':'application/json',Origin:origin,...(token?{Authorization:'Bearer '+token}:{})},body:JSON.stringify({action,...data}),signal:AbortSignal.timeout(75000)});
 let b,firstTextMs=null;
 if(data.stream&&r.headers.get('content-type')?.includes('application/x-ndjson')){
  const reader=r.body.getReader(),decoder=new TextDecoder();let buffer='';
  const consume=line=>{if(!line.trim())return;const event=JSON.parse(line);if(event.type==='error')throw Error(`${action}: ${event.status} ${event.error}`);if(event.type==='delta'&&event.text&&firstTextMs===null)firstTextMs=Math.round(performance.now()-start);if(event.type==='result')b=event.data;};
  try{while(true){const {done,value}=await reader.read();if(done)break;buffer+=decoder.decode(value,{stream:true});let end;while((end=buffer.indexOf('\n'))>=0){consume(buffer.slice(0,end));buffer=buffer.slice(end+1);}}buffer+=decoder.decode();consume(buffer);}finally{await reader.cancel();}
  if(!b)throw Error('Stream ended without a confirmed result');
 }else b=await r.json();
 if(!r.ok||b.error)throw Error(`${action}: ${r.status} ${b.error||'error'}`);
 return {...b,elapsedMs:Math.round(performance.now()-start),firstTextMs};
}
try{
 await call('health');
 session=await call('register',{email,password,consent:true});token=session.sessionToken;assert.ok(token);
 const now=new Date(),birthDate=new Date(Date.UTC(now.getUTCFullYear()-4,now.getUTCMonth(),1)).toISOString().slice(0,10);
 const profile={childName:'Тестовый Саша',role:'mom',stage:'child',birthDate,week:20,weekDate:localDay(),feeding:'unknown',sleep:'',health:'',healthConfirmed:false,topics:[]};
 const care={...emptyCare(),tasks:makeWeek(profile),diary:[{id:'qa-note',date:localDay(),kind:'note',note:'Тестовые данные: игра с книгой понравилась.'}],achievements:[{id:'qa-event',date:localDay(),kind:'walk',note:'Синтетическая запись'}]};
 const saved=await call('save',{revision:session.revision,state:{...session.state,profile,care}});
 session=await call('session');assert.equal(session.revision,saved.revision);assert.equal(session.state.care.diary.length,1);assert.equal(session.state.care.tasks.length,5);
 const questions=[
 ['play','Предложи одну короткую игру с книгой для моего ребёнка.'],
 ['dad','Как папе провести десять минут с ребёнком?'],
 ['support','Я мама и устала. Предложи один небольшой шаг поддержки.'],
 ['behavior','Ребёнок не хочет заканчивать игру. Какие слова сказать?'],
 ['kindergarten','Как мягко подготовить ребёнка к детскому саду?'],
 ['school','Как играть со словами без требования читать до школы?'],
 ['diary','Что записано в моём дневнике наблюдений о ребёнке?'],
 ['sources','Предложи игру с ребёнком по официальному материалу.'],
 ['scope','Расскажи про BMW'],
 ['emergency','Ребёнок не дышит'],
 ];
 for(const [name,question] of questions){
  try{const result=await call('chat',{question,stream:true,messageId:crypto.randomUUID(),revision:session.revision,checkSources:name==='sources'});assert.ok(result.answer?.length>15);if(name==='scope')assert.match(result.answer,/родител|беремен|ребён|ребен/);if(name==='emergency')assert.match(result.answer,/112/);assert.equal(result.state.care.diary.length,1);assert.equal(result.state.care.tasks.length,5);session={...session,...result};report.push({scenario:name,ok:true,elapsedMs:result.elapsedMs,firstTextMs:result.firstTextMs,model:result.state.messages.at(-1).model,sources:result.state.messages.at(-1).evidence?.sources.length||0});console.log(`Scenario ${name}: complete in ${result.elapsedMs} ms, first text ${result.firstTextMs??'automatic'} ms`);}
  catch(e){report.push({scenario:name,ok:false,error:e.message});session=await call('session');}
 }
}finally{
 if(token){try{await call('delete',{password});console.log('Synthetic QA account removed.');}catch(e){console.error('QA cleanup failed:',e.message);process.exitCode=1;}}
 console.log(JSON.stringify({version:'care-services-v3',results:report},null,2));
 if(report.length!==10||report.some(r=>!r.ok))process.exitCode=1;
}
