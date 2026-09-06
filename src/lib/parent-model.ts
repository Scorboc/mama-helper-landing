export type Profile = {
  role: 'mom' | 'dad'; stage: 'pregnancy' | 'child'; birthDate: string;
  week: number; weekDate: string; feeding: 'unknown'|'breast'|'formula'|'mixed'|'solids';
  sleep: string; health: string; healthConfirmed: boolean; topics: string[];
};
export type Message = {id:string;role:'user'|'assistant';text:string};
export type ParentState = {
  profile: Profile|null; saved:string[]; completed:string[];
  events:Record<string,{status:'read'|'hidden'|'later';until:number}>;
  preferences:{repeat:'never'|'day'|'week';push:boolean}; messages:Message[];
};
export const today = () => new Date().toISOString().slice(0,10);
export const emptyState = (): ParentState => ({profile:null,saved:[],completed:[],events:{},preferences:{repeat:'never',push:false},messages:[]});
export const defaultProfile = (): Profile => ({role:'mom',stage:'pregnancy',birthDate:'',week:20,weekDate:today(),feeding:'unknown',sleep:'',health:'',healthConfirmed:false,topics:[]});
export function ageValue(p:Profile,now=new Date()) {
  if(p.stage==='pregnancy') return p.week + Math.floor((Date.UTC(now.getUTCFullYear(),now.getUTCMonth(),now.getUTCDate())-Date.parse(p.weekDate+'T00:00:00Z'))/604800000);
  const d=new Date(p.birthDate+'T00:00:00Z');
  const anniversaryDay=Math.min(d.getUTCDate(),new Date(Date.UTC(now.getUTCFullYear(),now.getUTCMonth()+1,0)).getUTCDate());
  return (now.getUTCFullYear()-d.getUTCFullYear())*12+now.getUTCMonth()-d.getUTCMonth()-(now.getUTCDate()<anniversaryDay?1:0);
}
export const contextLabel=(p:Profile|null)=>!p?'Заполните профиль':p.stage==='child'?`Ребёнку ${ageValue(p)} мес.`:`Беременность · ${ageValue(p)} нед.`;
export type Milestone={id:string;stage:'pregnancy'|'child';age:number;topic:string;title:string;text:string;guide:string};
export const milestones:Milestone[]=[
  {id:'pregnancy-12',stage:'pregnancy',age:12,topic:'pregnancy',title:'Собрать вопросы к приёму',text:'Уточните свой план наблюдения. Напоминание не назначает обследований.',guide:'visit'},
  {id:'pregnancy-28',stage:'pregnancy',age:28,topic:'dad',title:'Обсудить помощь после рождения',text:'Поговорите с близкими о бытовых делах и времени для отдыха.',guide:'dad-team'},
  {id:'pregnancy-36',stage:'pregnancy',age:36,topic:'care',title:'Подготовить дом и контакты',text:'Сохраните контакты специалистов и договоритесь о помощи.',guide:'home'},
  {id:'child-0',stage:'child',age:0,topic:'sleep',title:'Проверить место для сна',text:'Откройте краткую памятку по организации сна младенца.',guide:'sleep-space'},
  {id:'child-6',stage:'child',age:6,topic:'feeding',title:'Вопросы о начале прикорма',text:'Возрастной ориентир для разговора с педиатром. Персональный план зависит от здоровья и готовности ребёнка.',guide:'feeding-notes'},
  {id:'child-12',stage:'child',age:12,topic:'play',title:'Новые идеи времени вместе',text:'Вернитесь к простым играм и общению с учётом интересов ребёнка.',guide:'talk-play'},
  {id:'child-24',stage:'child',age:24,topic:'play',title:'Общение в повседневных делах',text:'Выберите спокойное занятие вместе, без проверки навыков.',guide:'talk-play'},
  {id:'child-36',stage:'child',age:36,topic:'care',title:'Три года: вопросы на следующий этап',text:'Соберите вопросы к специалисту о дальнейшем наблюдении и развитии.',guide:'appointments'},
];
export function dueMilestones(state:ParentState,now=new Date()):Milestone[]{
  const p=state.profile;if(!p)return [];
  const age=ageValue(p,now);
  return milestones.filter(m=>m.stage===p.stage && m.age<=age && (!p.topics.length||p.topics.includes(m.topic))).filter(m=>{
    const event=state.events[m.id];return !event || (event.status==='later' && event.until<=now.getTime());
  });
}
// At first setup (or a stage/date correction), do not send a backlog of old milestones.
export function stateWithProfile(state:ParentState,p:Profile):ParentState {
  const previous=state.profile;
  const changed=!previous||previous.stage!==p.stage||previous.birthDate!==p.birthDate||previous.week!==p.week||previous.weekDate!==p.weekDate;
  if(!changed)return {...state,profile:p};
  const events:ParentState['events']={};
  for(const m of milestones){if(m.stage===p.stage&&m.age<ageValue(p))events[m.id]={status:'hidden',until:0};}
  return {...state,profile:p,events};
}
export function demoAnswer(question:string):string {
  const q=question.toLowerCase();
  if(/не дыш|задыха|судорог|без созн|не хочу жить|убить|навредить|суицид|покончить|кровотеч/.test(q))return 'Если прямо сейчас есть угроза жизни или риск навредить себе либо ребёнку, позвоните 112 и, если возможно, позовите взрослого, которому доверяете. Не ждите ответа чата. Демо не умеет надёжно оценивать срочность состояния.';
  // Exact demo intents avoid giving a canned health answer to an unrelated symptom description.
  if(['мне нужна поддержка','я устала','как справиться со стрессом?'].includes(q))return 'Вы можете начать с небольшой паузы. Почувствуйте опору под ногами, заметьте предметы и звуки вокруг. Затем выберите одно посильное действие — например, попросить близкого о конкретной помощи. В разделе «Памятки» есть пошаговая поддержка. Если тяжёлое состояние сохраняется или мешает жить, обратитесь к специалисту. Это готовый пример ответа, не терапия.';
  if(['как папе помочь?','что может делать папа?'].includes(q))return 'Выберите одну задачу, которую возьмёте на себя целиком: продукты, ужин или согласованную часть ухода. Обсудите, когда каждому из родителей нужен отдых. В памятке «Папа — тоже родитель» есть ещё несколько шагов. Это готовый сценарий для знакомства с чатом.';
  if(['как работают напоминания?','что умеет чат?'].includes(q))return 'В профиле укажите срок беременности или дату рождения. Советник показывает карточки при наступлении выбранного возрастного этапа. Их можно прочитать, скрыть или отложить. По умолчанию повторов нет. В демо доступны только готовые ответы; свободный AI-диалог и индивидуальные медицинские рекомендации не подключены.';
  return 'Пока я показываю только несколько готовых сценариев. Выберите вопрос под полем ввода или откройте памятки. Я не могу безопасно оценить симптомы, назначить лекарства, питание или упражнения. При вопросах о здоровье обратитесь к специалисту, а при угрозе жизни — 112.';
}
