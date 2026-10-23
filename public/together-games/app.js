(function(){'use strict';
const G=window.TogetherGames,C=window.TogetherCatalog,L=window.TogetherLibrary,T=window.TogetherToddler,$=id=>document.getElementById(id);
const views=['home','play','card','end','adult'];
const profileMode=true;let profileAge=null,contextReady=false,cursor=0,showAll=false;
if(profileMode){document.body.classList.add('profile-library');$('main').hidden=true;$('context-loading').hidden=false;}

let currentView='home',previousView='home',mode='offline',state=null,gameType=null,level=0,patternLeader=0,storyLeader=0,activeCard=null,toddlerTheme='world';
const defs={
 toddler:{icon:'🧸',title:'Картинка и мир вокруг',domain:'Слова · знакомые предметы · общение',description:'Три картинки: называем вместе, затем вспоминаем знакомую вещь в жизни. Телефон держит и переключает взрослый.',tip:'Можно показать, сказать слово, ответить жестом или только слушать. Не просите повторять до правильного ответа. Ничего не нужно искать или приносить; завершить можно в любой момент.'},
 detective:{icon:'🔎',title:'Комнатный сыщик',domain:'Признаки · описание · общение',description:'Один загадывает признак, другой показывает подходящую вещь рядом — или придумывает её. Потом меняетесь.',tip:'Не нужно ходить по комнате, брать вещи или куда-то забираться. Достаточно показать или представить предмет. Взрослый проверяет безопасность; без еды, мелких предметов, шнуров и розеток.'},
 pairs:{icon:'🌼',title:'Найдём пары вместе',domain:'Внимание · память · очередность',description:'У вас одна общая задача: найти пары. Открывайте по две карточки и передавайте ход друг другу.',tip:'Дайте ребёнку выбрать самому. Можно подсказать словами, рассмотреть картинки вместе. Это общая игра, а не соревнование.'},
 pattern:{icon:'◉',title:'Наши два узора',domain:'Последовательности · формы · общение',description:'Один придумывает узор, другой создаёт рядом свой. Образец остаётся видимым. Потом можно поменяться.',tip:'Скажите, что вы замечаете: «Здесь круг, а рядом треугольник». У ребёнка может получиться другая идея — сравните её с интересом, без оценки. Цвет дублируется формой.'},
 story:{icon:'🧺',title:'История для двоих',domain:'Воображение · речь · слушание',description:'Выбирайте картинки по очереди и придумывайте, что произошло. Мама начинает, ребёнок продолжает — можно словом или жестом.',tip:'Задавайте один открытый вопрос: «А что было потом?» Не исправляйте сюжет. Если ребёнку трудно говорить, он может показать картинку, а вы озвучите его идею.'}
};
function el(tag,text,cls){const e=document.createElement(tag);if(text!==undefined)e.textContent=String(text);if(cls)e.className=cls;return e;}
function button(text,fn,cls='secondary',id){const e=el('button',text,cls);e.type='button';if(id)e.id=id;e.addEventListener('click',fn);return e;}
function age(){return contextReady?profileAge:null;}
function ageText(n){const y=Math.floor(n/12),m=n%12;return y===0?(m===0?'Первый месяц':`${m} мес`):`${y} ${y===1?'год':y<5?'года':'лет'}${m?` ${m} мес.`:''}`;}
function windowText(card){const n=card.minMonths;return card.maxMonths-n===1?(n===0?'Первый месяц':`${n} ${n%10===1&&n!==11?'полный месяц':n%10>=2&&n%10<=4&&(n<12||n>14)?'полных месяца':'полных месяцев'}`):`${card.minMonths}–${card.maxMonths-1} мес.`;}
function view(name,heading){currentView=name;for(const id of views)$(id+'-view').hidden=id!==name;$('adult-link').hidden=['play','card'].includes(name);if(heading){$(heading).focus({preventScroll:true});window.scrollTo({top:0,behavior:'instant'});}}
function home(moveFocus=true){state=null;gameType=null;renderList();view('home');if(moveFocus)$('library-heading').focus({preventScroll:true});if(moveFocus)window.scrollTo({top:0,behavior:'instant'});}
function modeSelect(next){mode=next;cursor=0;showAll=false;renderList();}
function renderList(){
 updateAreas();const n=age(),list=$('game-list');list.replaceChildren();$('library-filters').hidden=mode==='screen'||n===null;$('library-count').textContent='';$('screen-tab').setAttribute('aria-pressed',String(mode==='screen'));$('offline-tab').setAttribute('aria-pressed',String(mode==='offline'));$('learning-tab').setAttribute('aria-pressed',String(mode==='learn'));
 $('age-summary').textContent=n!==null?`Активный профиль: ${ageText(n)}. Возраст меняется только в профиле.`:'Для подбора нужен профиль ребёнка.';
 if(n===null){$('mode-note').textContent=profileMode?'Для подбора нужен заполненный профиль родившегося ребёнка от 0 до 6 лет включительно.':'Уточните возраст, чтобы открыть подходящие варианты. Имя и дата рождения не нужны.';list.append(el('p','Каждому возрасту — свой способ поиграть вместе.','empty'));return;}
 if(mode==='screen'){
  if(!G.eligible(n)&&!T.eligible(n)){$('mode-note').replaceChildren(el('span','До 2 лет ВОЗ не рекомендует сидячее экранное время. Здесь доступны карточки для взрослого: прочитайте и отложите устройство. '),whoLink());list.append(button('Посмотреть занятия без экрана',()=>modeSelect('offline'),'primary'));return;}
  if(T.eligible(n))$('mode-note').replaceChildren(el('span',T.warning+' '),whoLink());else $('mode-note').textContent='Экранные варианты для 3–6 лет — короткая совместная часть игры. Начните с простого, смотрите на интерес ребёнка и делайте паузу по желанию.';
  for(const id of (T.eligible(n)?Object.keys(T.themes):['pairs','pattern','story','detective'])){const d=T.eligible(n)?{...defs.toddler,...T.themes[id]}:defs[id];const card=el('article',undefined,'game-card');card.append(el('div',d.icon,'game-icon'),el('p','НА ЭКРАНЕ · ВДВОЁМ','eyebrow'),el('h3',d.title),el('p',d.description),el('span',d.domain,'chip'),Object.assign(button('Играть вместе →',()=>requestStart(T.eligible(n)?'toddler':id,T.eligible(n)?id:undefined),'primary'),{ariaLabel:'Играть: '+d.title}));list.append(card);}
 }else{
  $('mode-note').textContent=mode==='learn'?'Знакомимся со звуками, формами, пространством и словами в совместной игре. Это не уроки и не проверка навыков. Взрослый читает карточку и откладывает экран.':'Прочитайте карточку сами, подготовьте всё необходимое и отложите экран. Порядок и длительность можно менять по интересу ребёнка.';
  const area=$('area-filter').value;const cards=L.select(C.cards,n,{area,noMaterials:$('no-materials').checked,stationary:$('stationary').checked,education:mode==='learn'});const page=L.page(cards,cursor,showAll);const start=page.start;const visible=page.items;$('library-count').textContent=`Подходит вариантов: ${cards.length}. ${showAll?'Показана вся подборка.':`Показаны ${cards.length?start+1:0}–${Math.min(start+3,cards.length)}.`} Знакомые занятия можно повторять; возрастные варианты не считаются разными механиками.`;
  for(const c of visible){const card=el('article',undefined,'game-card');card.append(el('div',c.icon,'game-icon'),el('p',windowText(c),'eyebrow'),el('h3',c.title),el('p',c.domain),button('Открыть карточку →',()=>openCard(c),'primary'));list.append(card);}
  if(!cards.length)list.append(el('p','С такими фильтрами вариантов нет. Отключите один фильтр — общая подборка по возрасту сохранена.','empty'));
  if(cards.length){const controls=el('div',undefined,'game-list-controls');controls.append(button(showAll?'Показывать по три':`Вся подборка (${cards.length})`,()=>{showAll=!showAll;cursor=0;renderList();},'secondary'));if(!showAll)controls.append(button(start+3>=cards.length?'Начать подборку сначала':'Ещё три идеи',()=>{cursor=start+3>=cards.length?0:start+3;renderList();},'primary'));list.append(controls);}
 }
}
function openCard(c){activeCard=c;$('card-age').textContent=windowText(c)+' · без экрана';$('card-title').textContent=c.title;$('card-goal').textContent='Что практикуем: '+c.domain.toLowerCase()+'.';const target=$('card-content');target.replaceChildren();
 target.append(el('h2','Приготовьте'),el('p',c.materials));
 for(const [title,text] of [['Ваша часть',c.adult],['Часть ребёнка',c.child]]){const box=el('section',undefined,'role-card');box.append(el('h2',title),el('p',text));target.append(box);}
 if(!c.roleBased){target.append(el('h2','Как поиграть'));const ol=el('ol');for(const step of c.steps)ol.append(el('li',step));target.append(ol);}target.append(el('h2','Если пока непросто'),el('p',c.readiness),el('p',c.safety,'note'));view('card','card-title');
}
function start(type,resetLevel=true){const n=age();if(n===null||!(type==='toddler'?T.eligible(n):G.eligible(n))){home();return;}if(resetLevel){level=type==='toddler'?0:G.settings(n).level;patternLeader=0;storyLeader=0;}
 gameType=type;state=type==='toddler'?T.create(n,toddlerTheme):type==='pairs'?G.memory(n,level):type==='pattern'?G.pattern(n,level,patternLeader):type==='detective'?G.detective(n,level):G.story(n,level,storyLeader);const d=type==='toddler'?{...defs.toddler,...T.themes[toddlerTheme]}:defs[type];$('play-title').textContent=d.title;$('play-domain').textContent=d.domain;$('play-description').textContent=d.description;$('play-age').textContent=ageText(n);$('parent-tip').textContent=d.tip;$('screen-guidance').hidden=type!=='toddler';view('play','play-title');renderGame();
}
function whoLink(){const a=el('a','Рекомендации ВОЗ');a.href=T.whoUrl;a.target='_blank';a.rel='noopener noreferrer';return a;}
let pendingScreenAge=null,pendingScreenTheme='world',screenOpener=null;
const screenGate=el('dialog');screenGate.className='adult-gate';screenGate.setAttribute('aria-labelledby','screen-gate-title');const screenTitle=el('h2','Перед экранным занятием');screenTitle.id='screen-gate-title';screenGate.append(screenTitle,el('p',T.warning),whoLink(),el('p','Три короткие части, без автоматического продолжения. В любой момент можно закончить.','note'));
const screenActions=el('div',undefined,'actions');screenActions.append(button('Выбрать занятие без экрана',()=>{screenGate.close();modeSelect('offline');},'secondary'),button('Играем вместе со взрослым',()=>{const valid=age()===pendingScreenAge&&T.eligible(age());screenGate.close();pendingScreenAge=null;if(valid){toddlerTheme=pendingScreenTheme;start('toddler');}else home();},'primary','screen-gate-start'));screenGate.append(screenActions);document.body.append(screenGate);
screenGate.addEventListener('close',()=>{if(currentView==='home'&&screenOpener?.isConnected)screenOpener.focus({preventScroll:true});});
function requestStart(type,theme='world'){if(type!=='toddler'){start(type);return;}if(!T.eligible(age())||!Object.hasOwn(T.themes,theme)){home();return;}screenTitle.textContent='Перед занятием «'+T.themes[theme].title+'»';pendingScreenAge=age();pendingScreenTheme=theme;screenOpener=document.activeElement;screenGate.showModal();screenGate.querySelector('button').focus();}
function slots(values,length){const row=el('div',undefined,'pattern-line');for(let i=0;i<length;i++){const slot=el('div',values[i]===undefined?'·':G.symbols[values[i]],'pattern-slot'+(values[i]===undefined?'':' filled symbol-'+values[i]));slot.setAttribute('aria-label',values[i]===undefined?'Пустое место':symbolName(values[i]));row.append(slot);}return row;}
function symbolName(id){return ['Круг','Треугольник','Звезда','Сердце'][id];}
function person(turn){return turn===0?'мамы':'ребёнка';}
function renderGame(){const focus=document.activeElement?.id;const board=$('board'),actions=$('game-actions'),instructions=$('game-instructions');board.replaceChildren();actions.replaceChildren();instructions.replaceChildren();$('game-feedback').textContent='';$('simplify').disabled=level===0;state.type==='toddler'?renderToddler(board,actions,instructions):state.type==='pairs'?renderPairs(board,actions,instructions):state.type==='pattern'?renderPattern(board,actions,instructions):state.type==='detective'?renderDetective(board,actions,instructions):renderStory(board,actions,instructions);
 if(focus==='animal-reveal'&&$('toddler-next')){$('toddler-next').focus({preventScroll:true});}else if(focus==='toddler-next'&&!$(focus)){$('turn').setAttribute('tabindex','-1');$('turn').focus({preventScroll:true});}else if(focus&&$(focus)&&!$(focus).disabled)$(focus).focus({preventScroll:true});else if(focus?.startsWith('tile-')||focus?.startsWith('token-')||focus?.startsWith('story-')){$('game-feedback').setAttribute('tabindex','-1');$('game-feedback').focus({preventScroll:true});}
}
const colorNames={red:'Красный',blue:'Синий',yellow:'Жёлтый'};
const shapeNames={circle:'Круг',square:'Квадрат',triangle:'Треугольник'};
function shapeArt(kind,size='normal'){
 const svg=document.createElementNS('http://www.w3.org/2000/svg','svg');svg.setAttribute('viewBox','0 0 100 100');svg.setAttribute('class','learning-shape '+size);svg.setAttribute('aria-hidden','true');
 const node=document.createElementNS('http://www.w3.org/2000/svg',kind==='circle'?'circle':kind==='square'?'rect':'polygon');
 const attrs=kind==='circle'?{cx:50,cy:50,r:43}:kind==='square'?{x:7,y:7,width:86,height:86}:{points:'50,5 96,91 4,91'};
 for(const [k,v]of Object.entries(attrs))node.setAttribute(k,String(v));svg.append(node);return svg;
}
function renderToddler(board,actions,instructions){
 $('turn').textContent=state.done?'Занятие завершено':`Часть ${state.index+1} из 3 · переключает взрослый`;
 if(state.done){instructions.append(el('p','Отложите экран. Можно просто побыть рядом.','instruction'));actions.append(button('Завершить занятие',()=>end(true),'primary'));return;}
 const theme=state.theme;
 if(state.phase==='real'){
  instructions.append(el('p','Теперь посмотрите друг на друга, а не на экран.','instruction'));
  const real=theme==='world'?state.real:theme==='animals'?T.rounds.animals[state.index].real:theme==='colors'?'Мама может показать цвет на своей одежде или назвать выбранный цвет ещё раз. Ребёнок может показать, ответить или только послушать.':theme==='shapes'?'Мама рисует форму пальцем в воздухе: плавный круг, стороны квадрата или три стороны треугольника. Повторять не обязательно.':'Мама показывает руками «большой» и «маленький». Ребёнок может показать любой размер своим жестом или посмотреть.';
  board.append(el('p',real,'intro'),el('p','Ничего искать или приносить не нужно. Если трудно — мама показывает сама. Можно пропустить; правильный ответ не требуется.','note'));
  actions.append(button(state.index===2?'Закончить занятие':'Продолжить к следующей части',()=>{T.advance(state);renderGame();},'primary','toddler-next'));return;
 }
 instructions.append(el('p',state.prompt,'instruction'));
 if(theme==='world'){
  const[icon,label]=T.pictures[state.index];const picture=el('div',icon,'toddler-picture');picture.setAttribute('role','img');picture.setAttribute('aria-label',label);board.append(picture,el('h2',label));
 }else if(theme==='animals'){
  const animal=T.rounds.animals[state.index];const picture=el('div',animal.icon,'toddler-picture');picture.setAttribute('role','img');picture.setAttribute('aria-label',animal.label);board.append(picture,el('h2',animal.label));
  if(state.revealed)board.append(el('p',animal.sound+' — мама произносит негромко.','learning-reply'));
  else actions.append(button('Как говорит '+animal.label.toLocaleLowerCase('ru')+'?',()=>{T.reveal(state);renderGame();},'secondary','animal-reveal'));
 }else{
  board.append(el('p',theme==='colors'?'Можно выбрать любой цвет — мама назовёт его.':theme==='shapes'?'Покажите любую форму — мама назовёт её.':'Рядом две одинаковые фигуры: большая и маленькая. Можно выбрать любую.','note'));
  const row=el('div',undefined,'learning-choices');const items=theme==='sizes'?(state.index%2?['small','big']:['big','small']):T.rounds[theme][state.index];
  items.forEach((id,i)=>{
   const label=theme==='colors'?colorNames[id]:theme==='shapes'?shapeNames[id]:id==='big'?'Большая фигура':'Маленькая фигура';
   const choice=button('',()=>{T.choose(state,i);renderGame();},'learning-choice'+(state.selection===i?' selected':''),'learning-choice-'+i);choice.setAttribute('aria-label',label);choice.setAttribute('aria-pressed',String(state.selection===i));
   if(theme==='colors')choice.append(el('span',undefined,'color-swatch color-'+id));else choice.append(shapeArt(theme==='sizes'?T.rounds.sizes[state.index]:id,theme==='sizes'?id:'normal'));
   choice.append(el('span',label));row.append(choice);
  });board.append(row);
  if(state.selection!==null){const id=items[state.selection];const label=theme==='colors'?colorNames[id]:theme==='shapes'?shapeNames[id]:id==='big'?'большая фигура':'маленькая фигура';$('game-feedback').textContent='Вы выбрали: '+label+'. Можно обсудить или выбрать другую.';}
 }
 actions.append(button('Обсудили или пропустили — дальше',()=>{T.advance(state);renderGame();},'primary','toddler-next'));
}
function renderPairs(board,actions,instructions){
 $('turn').textContent=state.done?'Все пары собраны вместе':`Сейчас ход ${person(state.turn)}`;instructions.append(el('p','Откройте две карточки. Потом посмотрите на них вместе и передайте ход.','instruction'));
 const grid=el('div',undefined,'pair-grid'+(state.config.pairs===3?' small':''));
 state.cards.forEach((id,index)=>{const open=state.open.includes(index),matched=state.matched.includes(index);const tile=button(open||matched?G.pictures[id][0]:'✦',()=>{if(G.tap(state,index))renderGame();},'tile '+(matched?'matched':open?'faceup':'back'),'tile-'+index);tile.setAttribute('aria-label',open||matched?`${G.pictures[id][1]}${matched?', пара найдена':''}`:`Закрытая карточка ${index+1}`);tile.disabled=matched||state.pending||state.done;grid.append(tile);});board.append(grid);
 if(state.done){$('game-feedback').textContent='У каждой картинки теперь есть пара. Вы сделали это вместе.';actions.append(button('Завершить раунд',()=>end(true),'primary'));}
 else if(state.pending){const same=state.cards[state.open[0]]===state.cards[state.open[1]];$('game-feedback').textContent=same?'Эти картинки нашли друг друга. Передадим ход?':'Картинки разные. Рассмотрите их и запомните, где они живут.';actions.append(button('Передать ход →',()=>{G.next(state);renderGame();},'primary','next-turn'));}
 else $('game-feedback').textContent=`Открыто пар: ${state.matched.length/2} из ${state.config.pairs}. Это ваш общий результат.`;
}
function renderPattern(board,actions,instructions){
 const compose=state.phase==='compose';const current=compose?state.leader:1-state.leader;$('turn').textContent=state.done?'Два узора — одна совместная игра':`Сейчас ход ${person(current)}`;
 instructions.append(el('p',compose?`Выберите ${state.config.length} ${state.config.length===5?'знаков':'знака'} и придумайте свой узор.`:'Образец перед вами. Создайте свой узор рядом — такой же или с новой идеей.','instruction'));
 board.append(el('p',`Узор ${person(state.leader)}`,'small-label'),slots(state.target,state.config.length));
 if(!compose)board.append(el('p',`Узор ${person(1-state.leader)}`,'small-label'),slots(state.answer,state.config.length));
 if(!state.done){const palette=el('div',undefined,'tokens');G.symbols.forEach((symbol,id)=>{const b=button(symbol,()=>{if(G.put(state,id))renderGame();},'token symbol-'+id,'token-'+id);b.setAttribute('aria-label',symbolName(id));b.disabled=(compose?state.target:state.answer).length>=state.config.length;palette.append(b);});board.append(palette);
 const currentLine=compose?state.target:state.answer;const undo=button('Убрать последний знак',()=>{G.undo(state);renderGame();},'quiet','undo-pattern');undo.disabled=!currentLine.length;actions.append(undo);
 const done=button(compose?'Передать ход →':'Посмотреть на два узора',()=>{if(compose)G.handover(state);else G.compare(state);renderGame();},'primary','pattern-next');done.disabled=currentLine.length!==state.config.length;actions.append(done);
 }else{$('game-feedback').textContent='Посмотрите: что у ваших узоров общее, а что каждый придумал по-своему?';actions.append(button('Завершить раунд',()=>end(true),'primary'),button('Поменяться ведущими',()=>{patternLeader=1-state.leader;start('pattern',false);},'secondary'));}
}
function renderStory(board,actions,instructions){
 $('turn').textContent=state.done?'Ваша история готова к рассказу':`Сейчас выбирает ${state.turn===0?'мама':'ребёнок'}`;
 const prompts=['Кто появится в вашей истории?','Где или когда это случилось?','Что было дальше?','Кого встретил герой?','Что изменилось?','Чем всё закончилось?'];
 instructions.append(el('p',state.done?'Расскажите по очереди, как связаны ваши картинки. Можно придумать совсем необычную историю.':prompts[state.chosen.length]+' Выберите картинку и добавьте фразу или жест.','instruction'));
 const strip=el('div',undefined,'story-strip');state.chosen.forEach((id,index)=>{const part=el('div',G.pictures[id][0],'story-part');part.append(el('small',(index+state.leader)%2===0?'мама':'ребёнок'));part.setAttribute('aria-label',G.pictures[id][1]);strip.append(part);});board.append(strip);
 if(!state.done){if(!state.chosen.length)actions.append(button(state.leader===0?'Начать с ребёнка':'Начать с мамы',()=>{storyLeader=1-state.leader;start('story',false);},'secondary'));const grid=el('div',undefined,'story-grid');G.pictures.forEach(([icon,label],id)=>{const b=button('',()=>{if(G.choose(state,id))renderGame();},'story-choice','story-'+id);b.append(el('span',icon),el('small',label));b.setAttribute('aria-label',label);grid.append(b);});board.append(grid);$('game-feedback').textContent=`Выбрано картинок: ${state.chosen.length} из ${state.config.story}.`;}
 else{$('game-feedback').textContent='Одна история, в которой есть идеи вас обоих.';actions.append(button('Рассказали — завершить',()=>end(true),'primary'),button(state.leader===0?'Начать историю с ребёнка':'Начать историю с мамы',()=>{storyLeader=1-state.leader;start('story',false);},'secondary')); }
}
function renderDetective(board,actions,instructions){
 const clues=[['🧸','Что-то мягкое','Большую мягкую игрушку'],['🏡','Большую вещь рядом','Большую вещь с рисунком'],['👕','Рисунок на одежде','Рисунок с двумя цветами'],['▥','Полоски','Полоски на ткани'],['☁️','Что-то похожее на облако','Что-то мягкое, похожее на облако'],['🌿','Зелёный цвет','Зелёный цвет на рисунке']];
 const leader=state.round;const text=id=>clues[id][state.config.level===0?1:2];
 if(state.phase==='prepare'){$('turn').textContent='Сначала — взрослый';instructions.append(el('p','Телефон держит взрослый. Ребёнок остаётся рядом. Только показываем пальцем или придумываем: ничего не берём, не несём, никуда не лезем.','instruction'));board.append(el('p','Перед началом взрослый проверяет: рядом нет мелких предметов, еды, шнуров и доступных розеток. Не нужно перемещаться ради поиска. Если подходящей вещи нет, её можно представить.','note'));actions.append(button('Взрослый проверил — играем на месте',()=>{G.readyDetective(state);renderGame();},'primary','detective-ready'));return;}
 $('turn').textContent=state.done?'Две загадки придуманы вместе':state.phase==='clue'?`Загадку выбирает ${leader===0?'мама':'ребёнок'}`:`Ищет ${leader===0?'ребёнок':'мама'}`;
 instructions.append(el('p','Выберите безопасную вещь рядом и только покажите на неё. Можно ничего не искать, а представить подходящий предмет.','instruction'));
 if(state.phase==='clue'){const palette=el('div',undefined,'story-grid');clues.forEach(([icon],id)=>{const b=button('',()=>{G.setClue(state,id);renderGame();},'story-choice','clue-'+id);b.append(el('span',icon),el('small',text(id)));palette.append(b);});board.append(palette);}
 else if(state.phase==='find'){board.append(el('div',clues[state.clue][0],'end-art'),el('h2','Покажите или представьте: '+text(state.clue).toLocaleLowerCase('ru')));$('game-feedback').textContent='Нет подходящей вещи? Придумайте её вместе — это тоже ход.';actions.append(button('Показали или придумали',()=>{G.found(state);renderGame();},'primary','found-object'));}
 else if(state.phase==='handover'){$('turn').textContent='Пора поменяться ролями';$('game-feedback').textContent='Теперь ребёнок выбирает признак, а мама предлагает свою идею.';actions.append(button('Поменяться ролями →',()=>{G.detectiveNext(state);renderGame();},'primary','detective-next'));}
 else{$('game-feedback').textContent='Вы нашли общий язык и придумали два подходящих варианта.';actions.append(button('Завершить раунд',()=>end(true),'primary'));}
}
function end(completed=false){$('end-copy').textContent=completed?(gameType==='toddler'?T.themes[toddlerTheme].end:gameType==='story'?'У вас появилась своя маленькая история.':gameType==='pattern'?'У вас получились два узора и повод поговорить о них.':gameType==='pairs'?'Вы вместе нашли все пары.':gameType==='detective'?'Вы по очереди загадывали и предлагали свои идеи.':'Вы попробовали совместную игру.'):'Пауза — тоже часть игры. Возвращайтесь, если захотите.';$('end-view').querySelector('.adult-details').hidden=!completed;view('end','end-title');}
const gate=el('dialog');gate.className='adult-gate';gate.setAttribute('aria-labelledby','gate-title');gate.innerHTML='<h2 id="gate-title">Передайте устройство взрослому</h2><p>Здесь информация о помощнике. Оплата отсутствует.</p><label for="gate-check">Чтобы перейти, напечатайте слово ВМЕСТЕ</label><input id="gate-check" type="text" autocomplete="off" autocorrect="off" spellcheck="false" autocapitalize="characters" aria-describedby="gate-help"><p class="note" id="gate-help">Это защита от случайных нажатий, а не проверка возраста. Ответ никуда не отправляется.</p><div class="actions"><button id="gate-cancel" class="secondary">Назад к игре</button><button id="gate-open" class="primary" disabled>Показать описание</button></div>';document.body.append(gate);
let gateOpener=null;
function offer(){gateOpener=document.activeElement;gate.querySelector('input').value='';$('gate-open').disabled=true;gate.showModal();$('gate-cancel').focus();}
$('gate-check').oninput=()=>{$('gate-open').disabled=$('gate-check').value.trim().toUpperCase()!=='ВМЕСТЕ';};$('gate-cancel').onclick=()=>gate.close();gate.addEventListener('close',()=>{if(currentView!=='adult'&&gateOpener?.isConnected)gateOpener.focus({preventScroll:true});});$('gate-open').onclick=()=>{if($('gate-check').value.trim().toUpperCase()!=='ВМЕСТЕ')return;gate.close();previousView=currentView;view('adult','adult-title');};
$('screen-tab').onclick=()=>modeSelect('screen');$('offline-tab').onclick=()=>modeSelect('offline');$('learning-tab').onclick=()=>modeSelect('learn');
$('home-link').onclick=e=>{e.preventDefault();home();};$('leave-game').onclick=home;$('leave-card').onclick=home;$('back-to-games').onclick=home;$('end-offline').onclick=()=>{mode='offline';home();};$('card-finish').onclick=()=>{gameType='card';end(true);};$('finish-game').onclick=()=>end(false);$('adult-link').onclick=offer;$('end-offer').onclick=offer;$('leave-adult').onclick=()=>view(previousView);$('adult-back').onclick=home;$('simplify').onclick=()=>{if(level>0)simplifyGate.showModal();};
const simplifyGate=el('dialog');simplifyGate.className='adult-gate';simplifyGate.setAttribute('aria-labelledby','simplify-title');simplifyGate.append(el('h2','Начать новый раунд попроще?'));simplifyGate.firstChild.id='simplify-title';simplifyGate.append(el('p','Текущий раунд закончится. Уже выбранные картинки и узоры в новый раунд не переносятся.'));
 const simpleActions=el('div',undefined,'actions');simpleActions.append(button('Продолжить этот раунд',()=>simplifyGate.close(),'secondary'),button('Начать попроще',()=>{simplifyGate.close();if(level>0){level--;start(gameType,false);}},'primary'));simplifyGate.append(simpleActions);document.body.append(simplifyGate);
function updateAreas(){const selected=$('area-filter').value;const categories=[...new Set(L.select(C.cards,age(),{education:mode==='learn'}).map(c=>c.category))].sort((a,b)=>a.localeCompare(b,'ru'));$('area-filter').replaceChildren(el('option','Все области'));$('area-filter').firstChild.value='';for(const text of categories){const option=el('option',text);option.value=text;$('area-filter').append(option);}if(categories.includes(selected))$('area-filter').value=selected;}
for(const id of ['area-filter','no-materials','stationary'])$(id).onchange=()=>{cursor=0;showAll=false;renderList();};
window.addEventListener('message',event=>{const config=L.context(event.data,event.origin,window.location.origin,event.source===window.parent);if(!config)return;contextReady=true;profileAge=Number.isInteger(config.ageMonths)&&config.ageMonths>=0&&config.ageMonths<84?config.ageMonths:null;if(screenGate.open)screenGate.close();pendingScreenAge=null;state=null;cursor=0;showAll=false;$('profile-context').hidden=!profileMode;$('main').hidden=false;$('context-loading').hidden=true;document.body.classList.toggle('profile-library',profileMode);document.body.classList.add('embedded-library');home(false);window.parent.postMessage({type:'mama-games-ready'},window.location.origin);});
if(window.parent!==window)window.parent.postMessage({type:'mama-games-request-context'},window.location.origin);else if(profileMode){$('context-loading').textContent='Подборка активного ребёнка открывается из кабинета.';const back=el('a','Открыть кабинет');back.href='../chat';$('context-loading').append(el('br'),back);}
 renderList();
})();
