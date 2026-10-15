const byId=id=>document.getElementById(id);
const labels={home:'Сегодня',chat:'Чат',trackers:'Трекеры',favorites:'Избранное',more:'Профиль',profile:'Ребёнок',settings:'Настройки',advisor:'Советник',card:'Медкарта','first-aid':'Первая помощь',daily:'Занятия',ok:'Успешно',error:'Ошибка',invalid:'Некорректный ответ',draft:'Черновик',published:'Опубликовано',archived:'Архив',new:'Новая',planned:'В работе',done:'Готово'};
labels['feedback-analysis']='Анализ отзывов';
const reviewLink=document.createElement('a');reviewLink.href='#feedback-review';reviewLink.textContent='Предложения по отзывам';document.querySelector('nav').insertBefore(reviewLink,byId('refresh'));
const money=value=>new Intl.NumberFormat('ru-RU',{minimumFractionDigits:2,maximumFractionDigits:6}).format(value)+' ₽';
function renderBudget(budget){
  if(!budget)return;
  byId('budget-note').textContent=budget.note;
  const rows=[[budget.today,budget.dailyLimitRub,'Сегодня'],[budget.monthToDate,budget.monthlyLimitRub,'Этот месяц']];
  table('budget-totals',['Период','Остаток','Лимит','По токенам','Выполняются / стоимость неизвестна','Вызовы'],rows.map(([value,limit,label])=>[label,money(value.remainingRub),money(limit),money(value.estimatedRub),money(value.reservedRub),value.calls]));
  table('budget-kinds',['Назначение','Вызовы','По токенам','Резерв'],budget.byKind.map(value=>[labels[value.kind]||value.kind,value.calls,money(value.estimatedRub),money(value.reservedRub)]));
  byId('budget-warning').textContent=rows.some(([value])=>value.exhausted)?'Общий бюджет исчерпан. Новые платные запросы приостановлены.':rows.some(([value])=>value.warning)?'Учтено не менее 80% бюджета. Проверьте расходы и оставшийся резерв.':'Расходы в пределах заданного бюджета.';
  const form=byId('budget-form');
  if(!form.contains(document.activeElement))for(const name of ['dailyLimitRub','monthlyLimitRub','freeChatLimit'])form.elements.namedItem(name).value=budget[name];
  form.querySelector('button').disabled=!budget.policyEditable;
}
function table(id,headers,rows){const root=byId(id);root.replaceChildren();if(!rows.length){root.textContent='Данных пока нет.';return;}const t=document.createElement('table'),head=t.createTHead().insertRow();headers.forEach(v=>{const el=document.createElement('th');el.textContent=v;head.append(el);});const body=t.createTBody();rows.forEach(r=>{const tr=body.insertRow();r.forEach(v=>{tr.insertCell().textContent=String(v??'Неизвестно');});});root.append(t);}
async function request(path,body){const r=await fetch(path,body?{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)}:{});const d=await r.json();if(!r.ok)throw Error(d.error||'Ошибка');return d;}
function list(kind,items){const root=byId(kind+'-list');root.replaceChildren();items.forEach(item=>{const article=document.createElement('article'),title=document.createElement('h3'),p=document.createElement('p'),button=document.createElement('button');title.textContent=item.title;p.textContent=labels[item.status]||item.status;button.textContent='Открыть';button.onclick=()=>{const form=byId(kind+'-form');Object.entries(item).forEach(([k,v])=>{const field=form.elements.namedItem(k);if(field){if(field.type==='checkbox')field.checked=!!v;else field.value=v??'';}});form.scrollIntoView({behavior:'smooth',block:'center'});};article.append(title,p,button);root.append(article);});}
async function refresh(){try{const d=await request('/data');renderBudget(d.aiBudget);renderAccess(d.access);renderFeedbackReview(d.feedbackReview);const checks=byId('checks');checks.replaceChildren();d.checks.forEach(c=>{const p=document.createElement('p');p.textContent=`${c.target==='site'?'Сайт и HTTPS':'API и база'}: ${c.ok?'работает':'ошибка'} · ${c.ms} мс · ${new Date(c.at*1000).toLocaleString()}`;checks.append(p);});byId('backup').textContent=d.backup?`Резервная копия проверена: ${new Date(d.backup.at*1000).toLocaleString()}. Хранится на этом компьютере или сервере; копию вне него следует хранить отдельно.`:'Проверенной копии пока нет.';
table('pages',['Раздел','Просмотры','Пользователи'],d.pages.map(x=>[labels[x.page]||x.page,x.views,x.users]));table('retention',['Возврат через','Можно оценить','Вернулось'],d.retention.map(x=>[x.day+' дн.',x.eligible,x.returned]));table('ai',['Назначение','Модель','Результат','Вызовы','Входные токены','Выходные токены','Среднее, мс','Без usage'],d.ai.map(x=>[labels[x.kind],x.model,labels[x.status],x.calls,x.inputTokens,x.outputTokens,x.averageMs,x.unknownUsage]));byId('note').textContent=d.note;byId('feedback').textContent=`Помогло: ${d.feedback.helpful}; не помогло: ${d.feedback.unhelpful}; небезопасно: ${d.feedback.unsafe}; идеи: ${d.feedback.idea}.`;byId('reports').textContent='Сохранённые отчёты: '+(d.reports.join(', ')||'пока нет');list('content',d.content);list('task',d.tasks);byId('status').textContent='Обновлено '+new Date().toLocaleTimeString();}catch(e){byId('status').textContent=e.message;}}
for(const kind of ['content','task'])byId(kind+'-form').onsubmit=async e=>{e.preventDefault();const form=e.target,body=Object.fromEntries(new FormData(form));if(kind==='content'){body.reviewed=form.elements.reviewed.checked;body.minMonths=Number(body.minMonths);body.maxMonths=Number(body.maxMonths);}const button=form.querySelector('button');button.disabled=true;try{await request('/'+kind,body);form.reset();await refresh();byId('status').textContent='Сохранено';}catch(err){byId('status').textContent=err.message;}finally{button.disabled=false;}};
byId('refresh').onclick=refresh;byId('report').onclick=async()=>{try{await request('/report',{});await refresh();}catch(e){byId('status').textContent=e.message;}};refresh();

function renderFeedbackReview(review){
 if(!review)return;
 const state={running:'Выполняется / результат неизвестен',success:'Предложения готовы',failed:'Нужна проверка владельца',uncertain:'Прервано; автоматического повтора нет'};
 byId('feedback-review-status').textContent=`Новых сигналов в очереди: ${review.pending}. Проверенных циклов: ${review.runs.length}.`;
 byId('feedback-review-limits').textContent=`${review.schedule}. Не более ${review.limits.dailyRub} ₽ в день и ${review.limits.monthlyRub} ₽ в месяц; расходы входят в общий бюджет ИИ и не расходуют ответы пользователей.`;
 table('feedback-review-runs',['Когда','Результат','Расход / резерв'],review.runs.map(r=>[new Date(r.created*1000).toLocaleString(),state[r.status]||r.status,money(r.estimatedRub)+(r.usageKnown?'':' · резерв')]));
 table('feedback-review-signals',['Сигнал · не подтверждённая ошибка','Количество'],(review.signals||[]).map(s=>[s.label,s.count]));
 const examples=byId('feedback-local-examples');examples.replaceChildren();
 for(const s of review.signals||[]){const details=document.createElement('details'),summary=document.createElement('summary');summary.textContent=s.label+' · локальные примеры';details.append(summary);for(const id of s.localEvidence||[]){const button=document.createElement('button'),box=document.createElement('div');button.type='button';button.textContent='Открыть локальный пример';button.onclick=async()=>{button.disabled=true;try{const e=await request('/feedback-evidence/'+id);box.replaceChildren();const note=document.createElement('p');note.textContent=e.available?`Комментарий: ${e.comment||'не указан'}. Контекст: ${e.consentContext?'разрешён':'не разрешён'}.`:e.reason;box.append(note);for(const m of e.messages||[]){const text=document.createElement('p');text.textContent=(m.role==='assistant'?'Ответ: ':'Вопрос: ')+m.text;box.append(text);}}catch(e){box.textContent=e.message;}finally{button.disabled=false;}};details.append(button,box);}examples.append(details);}
 const root=byId('feedback-proposals');root.replaceChildren();
 if(!review.proposals.length){root.textContent='Предложений пока нет. Они появятся после новых отзывов и успешного анализа.';return;}
 for(const p of review.proposals){
  const article=document.createElement('article'),title=document.createElement('h3');title.textContent=`${p.priority} · ${p.title}`;article.append(title);
  const badge=document.createElement('p');badge.className='muted';badge.textContent=`Сигналов: ${p.evidenceCount}. ${p.status==='planned'?'В плане':p.status==='dismissed'?'Отложено':'Новое предложение'}. Причина пока не подтверждена.`;article.append(badge);
  for(const [label,key] of [['Гипотеза','hypothesis'],['Проект правила','proposedRule'],['Обязательная граница','boundary'],['Промпт для исправления','adminPrompt'],['Проверка результата','test']]){const heading=document.createElement('h4'),text=document.createElement('p');heading.textContent=label;text.textContent=p[key];article.append(heading,text);}
  const copy=document.createElement('button');copy.type='button';copy.textContent='Скопировать промпт';copy.onclick=async()=>{try{await navigator.clipboard.writeText(`${p.adminPrompt}\n\nПроект правила: ${p.proposedRule}\nГраницы: ${p.boundary}\nТест: ${p.test}`);byId('status').textContent='Промпт скопирован.';}catch{byId('status').textContent='Выделите и скопируйте текст промпта вручную.';}};article.append(copy);
  for(const [status,label] of [['planned','В план'],['dismissed','Отложить'],['new','Вернуть к рассмотрению']]){if(status===p.status)continue;const b=document.createElement('button');b.type='button';b.textContent=label;b.style.margin='6px';b.onclick=async()=>{b.disabled=true;try{await request('/feedback-decision',{id:p.id,status});await refresh();byId('status').textContent='Решение сохранено. Правила не изменены.';}catch(e){byId('status').textContent=e.message;}finally{b.disabled=false;}};article.append(b);}
  const details=document.createElement('details'),summary=document.createElement('summary');summary.textContent='Локальные примеры · могут содержать личные сведения';details.append(summary);
  const note=document.createElement('p');note.textContent='Контекст доступен только при согласии на его сохранение. Не пересылайте эти примеры внешним инструментам.';details.append(note);
  for(const id of p.localEvidence){const button=document.createElement('button');button.type='button';button.textContent='Открыть локальный пример';const box=document.createElement('div');button.onclick=async()=>{button.disabled=true;try{const e=await request('/feedback-evidence/'+id);box.replaceChildren();const comment=document.createElement('p');comment.textContent=e.available?`Комментарий: ${e.comment||'не указан'}. Контекст: ${e.consentContext?'разрешён':'не разрешён'}.`:e.reason;box.append(comment);for(const m of e.messages||[]){const text=document.createElement('p');text.textContent=(m.role==='assistant'?'Ответ: ':'Вопрос: ')+m.text;box.append(text);}}catch(e){box.textContent=e.message;}finally{button.disabled=false;}};details.append(button,box);}
  article.append(details);root.append(article);
 }
}
byId('budget-form').onsubmit=async event=>{
  event.preventDefault();const form=event.target,button=form.querySelector('button');
  const body=Object.fromEntries([...new FormData(form)].map(([key,value])=>[key,Number(value)]));
  button.disabled=true;
  try{renderBudget(await request('/ai-policy',body));byId('status').textContent='Лимиты сохранены. Уже использованные ответы и расходы сохранены.';}
  catch(error){byId('status').textContent=error.message;}
  finally{button.disabled=false;}
};

function renderAccess(access){
 if(!access)return;
 renderSuggestions(access.suggestions||[]);
 byId('budget-form').elements.namedItem('freeChatLimit').closest('label').style.display=access.plan.enabled?'none':'block';
 byId('payment-status').textContent=access.plan.paymentConfigured?'Приём оплаты подключён. Чеки НПД выдавайте отдельно.':'Оплата не подключена. Бесплатный доступ назначается только вручную.';
 table('testers',['Аккаунт','Окончание','Ответов','Состояние'],access.testers.map(t=>[t.login,new Date(t.endsAt*1000).toLocaleString(),t.answerLimit,t.active?'Активен':'Окончен']));
 const root=byId('data-requests');root.replaceChildren();
 for(const r of access.requests){const article=document.createElement('article');for(const text of [r.id+' · '+r.login+' · '+r.kind+' · '+r.status,new Date(r.createdAt*1000).toLocaleString(),r.text]){const p=document.createElement('p');p.textContent=text;article.append(p);}root.append(article);}
 if(!access.requests.length)root.textContent='Обращений пока нет.';
 table('payments',['Заказ','Статус','Создан','Доступ начислен'],access.payments.map(p=>[p.orderId,p.status,new Date(p.createdAt*1000).toLocaleString(),p.fulfilledAt?new Date(p.fulfilledAt*1000).toLocaleString():'Нет']));
}
function renderSuggestions(items){
 let root=byId('suggestion-moderation');
 if(!root){root=document.createElement('section');root.id='suggestion-moderation';byId('tasks').before(root);}
 if(root.contains(document.activeElement))return;
 root.replaceChildren();const heading=document.createElement('h2');heading.textContent='Проверка идей перед голосованием';root.append(heading);
 const note=document.createElement('p');note.textContent='Исходный текст остаётся приватным. Подготовьте публичную версию без имён, возраста, диагнозов, истории лечения и других сведений о семье. Проверка касается личных данных; медицинские изменения требуют отдельного рассмотрения.';root.append(note);
 for(const item of items.filter(x=>x.status==='open'||x.status==='planned')){
  const article=document.createElement('article'),original=document.createElement('p');original.textContent='Приватный оригинал: '+item.title+' — '+item.detail;article.append(original);
  const form=document.createElement('form');
  for(const [name,labelText,max] of [['title','Публичный заголовок',120],['detail','Публичное описание',800]]){const label=document.createElement('label');label.textContent=labelText;const field=document.createElement(name==='title'?'input':'textarea');field.name=name;field.maxLength=max;field.value=item.public?.[name]||'';if(name==='title'){field.required=true;field.minLength=10;}label.append(field);form.append(label);}
  const label=document.createElement('label'),check=document.createElement('input');check.type='checkbox';check.required=true;label.append(check,document.createTextNode('Проверил отсутствие личных и медицинских сведений. Именно этот текст будет виден всем.'));form.append(label);
  const button=document.createElement('button');button.textContent=item.public?.reviewed?'Обновить публичную версию':'Допустить к голосованию';form.append(button);
  form.onsubmit=async e=>{e.preventDefault();button.disabled=true;try{await request('/suggestion-review',{id:item.id,title:form.elements.title.value,detail:form.elements.detail.value,reviewed:check.checked});await refresh();byId('status').textContent='Публичная версия сохранена. Приватный оригинал сохранён.';}catch(err){byId('status').textContent=err.message;}finally{button.disabled=false;}};
  article.append(form);root.append(article);
 }
}
for(const [id,path] of [['test-access-form','/test-access'],['data-request-status-form','/data-request-status']])byId(id).onsubmit=async event=>{
 event.preventDefault();const form=event.target,button=form.querySelector('button'),body=Object.fromEntries(new FormData(form));
 if(path==='/test-access'){body.days=Number(body.days);body.answerLimit=Number(body.answerLimit);body.revoke=form.elements.revoke.checked;}
 button.disabled=true;try{await request(path,body);await refresh();byId('status').textContent='Сохранено. Данные пользователей сохранены.';}catch(e){byId('status').textContent=e.message;}finally{button.disabled=false;}
};
