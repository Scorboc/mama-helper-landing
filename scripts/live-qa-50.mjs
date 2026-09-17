const API=process.env.MAMA_HELPER_API||'https://mama-helper-ai-proxy.reborntechsar.workers.dev';
const ORIGIN=process.env.MAMA_HELPER_ORIGIN||'https://mama-helper-landing--preview.poehali.dev';
const LOGIN=process.env.MAMA_HELPER_TEST_LOGIN;
const PASSWORD=process.env.MAMA_HELPER_TEST_PASSWORD;
if(!LOGIN||!PASSWORD)throw Error('Set MAMA_HELPER_TEST_LOGIN and MAMA_HELPER_TEST_PASSWORD.');
const questions=[
  'Ребёнок спит только на руках, как постепенно пробовать перекладывать?',
  'Просыпается сразу, как только я отхожу от кроватки. Что можно изменить?',
  'Как сделать спокойный ритуал перед сном без долгих уговоров?',
  'Как папе участвовать в укладывании, если ребёнок зовёт только маму?',
  'Ребёнок перепутал день и ночь, с чего начать менять режим?',
  'Не хочет пробовать новую еду. Как предлагать без давления?',
  'Как организовать семейный ужин, если ребёнок быстро уходит из-за стола?',
  'Что делать, если ребёнок просит только знакомую еду?',
  'Как вовлечь папу в кормление и не командовать каждым шагом?',
  'Как подготовить перекус ребёнку в дорогу?',
  'Во что поиграть дома без покупки новых игрушек?',
  'Какие спокойные игры подойдут перед сном?',
  'Как читать книгу, если ребёнок всё время перелистывает страницы?',
  'Что предложить ребёнку, если мне самой скучно играть?',
  'Какие игры помогают учиться ждать своей очереди?',
  'Как занять ребёнка, пока я готовлю ужин?',
  'Что можно сделать из картонной коробки для совместной игры?',
  'Как поддержать интерес к рисованию без требований сделать красиво?',
  'Ребёнок постоянно просит мультики. Как договориться спокойнее?',
  'Как завершать игру без истерики?',
  'Как собрать ребёнка в детский сад?',
  'Что положить в шкафчик в садике на первую неделю?',
  'Как подготовить ребёнка к первому дню в саду?',
  'Ребёнок плачет при расставании в садике. Какие фразы говорить?',
  'Как сделать утренние сборы в сад спокойнее?',
  'Что делать, если ребёнок не хочет одеваться в сад?',
  'Как обсудить с воспитателем привычки ребёнка?',
  'Как помочь ребёнку познакомиться с другими детьми в группе?',
  'После сада ребёнок капризничает дома. Как организовать вечер?',
  'Как понять, что ребёнку нужен более постепенный режим адаптации к саду?',
  'Ребёнок кричит, когда слышит «нет». Как отвечать спокойно?',
  'Что говорить, когда ребёнок бьёт другого ребёнка?',
  'Как помочь назвать чувства, если ребёнок пока говорит мало?',
  'Ребёнок не хочет делиться игрушками. Как реагировать без стыда?',
  'Как установить границу и не читать длинную лекцию?',
  'Что делать во время истерики в магазине?',
  'Как подготовить ребёнка к приходу гостей?',
  'Как объяснить ребёнку, что скоро появится младший брат?',
  'Как пережить переезд с маленьким ребёнком?',
  'Как помочь ребёнку привыкнуть к няне?',
  'Я устала и раздражаюсь по мелочам. Как попросить близких о помощи?',
  'Как разделить домашние дела после рождения ребёнка?',
  'Папа чувствует себя лишним рядом с малышом. С чего ему начать?',
  'Как договориться с бабушкой о наших правилах без ссоры?',
  'Как найти десять минут на отдых, когда весь день с ребёнком?',
  'Что записать перед визитом к педиатру, чтобы ничего не забыть?',
  'Как подготовить ребёнка к плановому осмотру?',
  'Ребёнок кашляет, какие наблюдения подготовить для врача?',
  'Как безопасно организовать игровое место дома?',
  'Как составить простой план дня с ребёнком и не перегрузить его?',
];
const requested=(process.env.MAMA_HELPER_QUESTION_NUMBERS||'').split(',').map(Number).filter(n=>Number.isInteger(n)&&n>=1&&n<=questions.length);
const selected=requested.length?requested.map(n=>({number:n,question:questions[n-1]})):questions.map((question,index)=>({number:index+1,question}));

let cookie='',revision=0,state;
async function call(action,data={}){
  const response=await fetch(API,{method:'POST',headers:{'content-type':'application/json','origin':ORIGIN,...(cookie?{cookie}:{})},body:JSON.stringify({action,...data})});
  const setCookie=response.headers.get('set-cookie');if(setCookie)cookie=setCookie.split(';')[0];
  const body=await response.json();if(!response.ok)throw Error(`${action}: ${body.error||response.status}`);
  return body;
}
function cleared(current){return {...current,profile:null,saved:[],completed:[],events:{},messages:[],medicalCard:[],pendingMemory:[],conversations:[],conversationTitle:'Общий разговор',care:{tasks:[],diary:[],achievements:[],appointments:[],checked:[],followups:true}};}
async function save(next){const body=await call('save',{state:next,revision});revision=body.revision;state=next;}

const session=await call('login',{email:LOGIN,password:PASSWORD});revision=session.revision;state=session.state;
const preservedChat={messages:structuredClone(state.messages||[]),conversations:structuredClone(state.conversations||[]),conversationTitle:state.conversationTitle||'Общий разговор'};
await save(cleared(state));
await save({...state,profile:{childName:'Тест',role:'mom',stage:'child',birthDate:'2023-09-17',feeding:'unknown',sleep:'',health:'',healthConfirmed:false,topics:[]}});
const results=[];
try{
  for(const item of selected){
    const i=item.number-1;
    await save({...state,messages:[],pendingMemory:[],conversations:[],conversationTitle:`Проверка ${String(item.number).padStart(2,'0')}`});
    const messageId=crypto.randomUUID();let body,error='';
    for(let attempt=1;attempt<=2;attempt++){
      try{body=await call('chat',{question:item.question,messageId,revision});break;}
      catch(e){error=e.message;if(attempt<2)process.stderr.write(`[${item.number}/50] повтор после ошибки: ${error}\n`);}
    }
    if(!body){results.push({number:item.number,question:item.question,answer:'',error,unwantedWarning:false,ageMention:false});process.stderr.write(`[${item.number}/50] не получен ответ\n`);continue;}
    revision=body.revision;state=body.state;
    const answer=body.answer||'';
    const ordinary=i!==47;
    const unwanted=ordinary&&/синюш|судорог|потер[яеию].*созн|\b112\b/i.test(answer);
    const ageMention=/\bв (?:этом|таком) возрасте\b|\b\d+\s*(?:год|года|лет|месяц|месяца|месяцев|недел)/i.test(answer);
    results.push({number:item.number,question:item.question,answer,unwantedWarning:unwanted,ageMention});
    process.stderr.write(`[${item.number}/50] готово\n`);
  }
}finally{
  await save({...cleared(state),...preservedChat});
}
const report={runAt:new Date().toISOString(),count:results.length,unwantedWarnings:results.filter(r=>r.unwantedWarning).length,ageMentions:results.filter(r=>r.ageMention).length,failed:results.filter(r=>r.error||!r.answer).length,results};
process.stdout.write(JSON.stringify(report,null,2)+'\n');
if(report.count!==selected.length||report.failed||report.unwantedWarnings||report.ageMentions)process.exitCode=1;
