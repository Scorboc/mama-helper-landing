// Fixed official pages only. No user text, profile or search query is sent to these sites.
export const sourceRegistry=[
 {id:'play',title:'NHS: совместные игры',url:'https://www.nhs.uk/baby/babys-development/play-and-learning/baby-and-toddler-play-ideas/',match:/игр|книг|реч|занят|развит/i},
 {id:'cry',title:'NHS: плач ребёнка и поддержка родителя',url:'https://www.nhs.uk/baby/caring-for-a-newborn/soothing-a-crying-baby/',match:/плач|плачет|устал|поддерж|стресс/i},
 {id:'behavior',title:'UNICEF: бережное воспитание',url:'https://www.unicef.org/parenting/child-care/how-discipline-your-child-smart-and-healthy-way',match:/поведен|истерик|эмоц|кус|ссор|пап/i},
 {id:'kindergarten',title:'UNICEF: подготовка к детскому саду',url:'https://www.unicef.org/parenting/child-care/how-prepare-your-child-preschool',match:/садик|детск.*сад|школ/i},
 {id:'documents',title:'Социальный фонд России: семьям с детьми',url:'https://sfr.gov.ru/grazhdanam/semyam_s_detmi/',match:/выплат|пособ|документ|льгот|материнск.*капитал/i},
];
export async function retrieveEvidence(question,requestFetch=fetch){
 const entry=sourceRegistry.find(s=>s.match.test(question));
 if(!entry)return {sources:[],text:'',limitation:'В каталоге пока нет подходящего источника. Проверка по источнику не выполнена.'};
 const controller=new AbortController(),timer=setTimeout(()=>controller.abort(),3500);
 try{
  const r=await requestFetch(entry.url,{signal:controller.signal,redirect:'error',headers:{Accept:'text/html'}});
  if(!r.ok||!r.headers.get('content-type')?.includes('text/html'))throw Error('unavailable');
  // Bounded reads also prevent a huge official page from exhausting the Worker.
  const reader=r.body.getReader(),decoder=new TextDecoder();let html='';
  try{while(html.length<180000){const {done,value}=await reader.read();if(done)break;html+=decoder.decode(value,{stream:true});}}finally{await reader.cancel();}
  const main=html.match(/<main\b[^>]*>([\s\S]*?)<\/main>/i)?.[1]||html;
  const plain=main.replace(/<(script|style|nav|header|footer)\b[^>]*>[\s\S]*?<\/\1>/gi,' ').replace(/<[^>]+>/g,' ').replace(/&(?:nbsp|amp|quot|lt|gt);/g,' ').replace(/\s+/g,' ').trim().slice(0,6500);
  if(plain.length<150)throw Error('empty');
  return {sources:[{title:entry.title,url:entry.url}],checkedAt:new Date().toISOString(),text:plain,limitation:'Загружена официальная страница, но это не проверка каждого утверждения и не заключение врача. Зарубежные материалы не определяют российские правила.'};
 }catch{return {sources:[],text:'',limitation:'Официальная страница сейчас недоступна. Онлайн-проверка не выполнена; не полагайтесь на ответ для медицинского или правового решения.'};}
 finally{clearTimeout(timer);}
}
