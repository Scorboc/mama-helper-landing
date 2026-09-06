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
export function demoAnswer(question:string, profile:Profile|null=null):string {
  const q=question.toLowerCase().replace(/ё/g,'е').trim();
  const context=profile ? `Я вижу в демо-профиле: ${contextLabel(profile).toLowerCase()}. ` : '';
  if(/не дыш|задыха|судорог|без созн|не хочу жить|убить|навредить|суицид|покончить|кровотеч/.test(q))return 'Если прямо сейчас есть угроза жизни или риск навредить себе либо ребёнку, позвоните 112 и, если возможно, позовите взрослого, которому доверяете. Не ждите ответа чата. Демо не умеет надёжно оценивать срочность состояния.';
  if(/поддержк|устал|стресс|тревог|тяжело|не справля/.test(q))return `${context}Давайте без попытки решить всё сразу. На ближайшие 10 минут выберите одно маленькое действие: выпить воды, сесть с опорой для спины, попросить близкого побыть с ребёнком или отменить необязательную задачу. Если тревога или подавленность держатся, мешают спать и жить — важно обратиться к специалисту. Это демонстрационный ответ, не терапия.`;
  if(/пап|муж.*помо|как.*помо/.test(q))return `${context}Папе полезнее взять не «помощь по запросу», а одну зону целиком: прогулку, купание, ужин или утренние сборы. Затем договоритесь о конкретном времени отдыха для каждого. Лучше спросить не «чем помочь?», а «я беру прогулку с 18:00 до 19:00 — тебе подходит?»`;
  if(/смес|искусственн.*кормлен/.test(q))return `${context}Смесь не выбирают по рекламе или рейтингу. В безопасном варианте ориентируются на возрастную категорию, показания, переносимость и рекомендации педиатра, если есть особенности здоровья. Не стоит самостоятельно менять смесь из-за одного отзыва или назначать лечебную смесь. В полноценной версии чат сможет объяснить критерии и помочь подготовить вопросы врачу, но не будет ставить диагноз.`;
  if(/игр|играт|занят|развива/.test(q)){
    if(profile?.stage==='child'&&ageValue(profile)<12)return `${context}Для первого года обычно важнее простая игра вместе: спокойный разговор, безопасный предмет для исследования, «ку-ку», песенка с паузами. Не нужно проверять ребёнка на результат — достаточно наблюдать, что его заинтересовало.`;
    if(profile?.stage==='child')return `${context}Попробуйте игру, где ребёнок участвует в обычном деле: сортировать безопасные предметы, искать игрушку по простой подсказке, строить и разрушать башню, называть действия на прогулке. Начните на 5–10 минут и остановитесь, пока всем ещё интересно.`;
    return `${context}Для беременности в демо можно выбрать спокойное занятие для себя: короткая прогулка, музыка, разговор с близким или список вещей, которые уже помогают вам восстанавливаться. После рождения советник предложит идеи игр по возрасту.`;
  }
  if(/сон|спит|засып/.test(q))return `${context}Сон у детей и родителей редко бывает «по расписанию идеально». Для начала попробуйте один повторяющийся спокойный ритуал перед сном: приглушить свет, закончить активную игру, коротко побыть рядом. Если вопрос о безопасности сна, трудном дыхании, отказе от еды или самочувствии — демо не оценивает состояние, нужен специалист.`;
  if(/напомин|что умеет|может чат/.test(q))return `${context}В профиле укажите срок беременности или дату рождения. Советник показывает карточки при наступлении возрастного этапа; их можно прочитать, скрыть или отложить. В этом демо нет внешнего AI и нет поиска в интернете: ответы подготовлены заранее, чтобы безопасно показать интерфейс.`;
  if(/кормлен|прикорм|еда|пита/.test(q))return `${context}Вопросы питания зависят от возраста, здоровья и готовности ребёнка. Демо может подсказать общий принцип: не торопиться и обсуждать индивидуальные особенности с педиатром. Оно не составляет меню, не назначает добавки и не оценивает симптомы.`;
  return `${context}Это автономный демо-чат: он знает типовые безопасные темы — поддержка, папа, сон, игры, смесь, питание и напоминания. Попробуйте спросить, например: «Как выбрать смесь?» или «Во что поиграть?» Для симптомов, лекарств и срочных состояний он не даёт советов; при угрозе жизни — 112.`;
}
