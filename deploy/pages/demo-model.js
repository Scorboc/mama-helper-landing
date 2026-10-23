/* Explicit browser-memory demo. This is not an account service or a security boundary. */
(() => {
  'use strict';
  function createDemo(now = () => Date.now(), hints = {}) {
    const clone = value => JSON.parse(JSON.stringify(value));
    const iso = offset => new Date(now() - offset).toISOString();
    const birth = new Date(now()); birth.setUTCDate(15); birth.setUTCMonth(birth.getUTCMonth() - 6);
    let revision = 1;
    let state = { activeChildId:'primary', profile:{ childName:'Демо-малыш',childSex:'unknown',role:'mom',stage:'child',
      birthDate:birth.toISOString().slice(0,10),week:20,weekDate:iso(0).slice(0,10),feeding:'mixed',sleep:'',health:'',healthConfirmed:false,topics:[] },
      saved:[],completed:[],events:{},preferences:{repeat:'never',push:false,timezone:'Europe/Moscow'},messages:[],medicalCard:[],
      care:{tasks:[],diary:[],appointments:[],checked:[],followups:true,achievements:[]} };
    const records = new Map([['primary',[
      {id:'demo-feed',kind:'feeding',at:iso(7200000),side:'left',note:''},
      {id:'demo-sleep',kind:'sleep',at:iso(10800000),end:iso(3600000),sleepType:'day',note:''},
      {id:'demo-memory',kind:'achievement',at:iso(86400000*30),value:'Знакомая игрушка',note:'Пример воспоминания — можно заменить своим тестовым текстом.'},
    ]]]);
    const questions = new Map();
    const labels = {roll:'Переворачивается',crawl:'Ползает',stand:'Встаёт у опоры',walk:'Ходит',words:'Первые слова'};
    const session = () => ({ user:{id:'public-visual-preview',email:'demo@example.invalid',emailVerified:true},state:clone(state),revision,
      quota:{limit:0,used:0,remaining:0},billing:{mode:'off',paymentConfigured:false},publicDemo:true });
    const ok = body => ({status:200,body:clone(body)});
    const fail = (error,status=400) => ({status,body:{error}});
    function dispatch(data) {
      if (!data || typeof data !== 'object' || Array.isArray(data)) return fail('Проверьте запрос.');
      const cid = data.childId || state.activeChildId || 'primary';
      if (data.ownerId && data.ownerId !== 'public-visual-preview') return fail('В демо нет доступа к чужой семье.',403);
      const child = cid === (state.activeChildId || 'primary') ? state : (state.children || []).find(c => c.id === cid)?.data;
      if (['care-list','care-put','care-delete','doctor-question-put','doctor-question-delete','age-guidance'].includes(data.action) && !child?.profile) return fail('Профиль не найден.',404);
      const list = records.get(cid) || [], qs = questions.get(cid) || [];
      switch (data.action) {
        case 'session': return ok(session());
        case 'config': return ok({storage:'demo',chatConfigured:false,pushConfigured:false,publicDemo:true});
        case 'health': return ok({ok:true,storage:'demo'});
        case 'save':
          if (!data.state || typeof data.state !== 'object' || Array.isArray(data.state)) return fail('Проверьте тестовый профиль.');
          if (data.revision !== revision) return fail('Демо изменилось. Обновите страницу.',409);
          state = clone(data.state); revision++; return ok({state,revision});
        case 'care-list': return ok({profile:child.profile,contextVersion:'demo-'+revision,records:list,doctorQuestions:qs,
          daily:[],achievements:child.care?.achievements || [],appointments:child.care?.appointments || [],permission:'owner',authors:{},publicDemo:true});
        case 'care-put': {
          const r=data.record;
          if (!r || !/^[a-zA-Z0-9-]{1,100}$/.test(r.id || '') || !['sleep','wake','feeding','food','achievement','mood'].includes(r.kind)
              || !Number.isFinite(Date.parse(r.at)) || Date.parse(r.at)>now() || typeof (r.note || '') !== 'string' || (r.note || '').length>500) return fail('Проверьте тестовую запись.');
          if (qs.some(q=>q.id===r.id)) return fail('Идентификатор уже используется.',409);
          if (r.skill && (!Object.hasOwn(labels,r.skill) || r.kind!=='achievement')) return fail('Неизвестный навык.');
          if (r.skill) {
            const previous=list.find(x=>x.kind==='achievement' && x.skill===r.skill);
            if (previous) return ok({record:previous,alreadyMarked:true});
          }
          const saved=clone({...r,...(r.skill ? {value:labels[r.skill]} : {})});
          records.set(cid,[...list.filter(x=>x.id!==saved.id),saved]);revision++;return ok({record:saved});
        }
        case 'care-delete': records.set(cid,list.filter(x=>x.id!==data.id));revision++;return ok({ok:true});
        case 'doctor-question-put': {
          const text=typeof data.text==='string' ? data.text.trim() : '';
          if (!/^[a-zA-Z0-9-]{1,100}$/.test(data.id || '') || !text || text.length>500) return fail('Вопрос должен содержать от 1 до 500 символов.');
          if (list.some(r=>r.id===data.id)) return fail('Идентификатор уже используется.',409);
          const canonical=s=>s.toLocaleLowerCase('ru').replace(/\s+/g,' ').trim();
          const duplicate=qs.find(q=>q.id!==data.id && canonical(q.note)===canonical(text));
          if (duplicate) return ok({duplicate:true});
          if (qs.length>=30 && !qs.some(q=>q.id===data.id)) return fail('Можно сохранить до 30 вопросов.');
          questions.set(cid,[...qs.filter(q=>q.id!==data.id),{id:data.id,note:text,at:iso(0),kind:'doctor-question'}]);revision++;
          return ok({ok:true,duplicate:false,undoToken:'demo-memory-only'});
        }
        case 'doctor-question-delete': questions.set(cid,qs.filter(q=>q.id!==data.id));revision++;return ok({ok:true});
        case 'age-guidance': {
          const p=child.profile,day=new Intl.DateTimeFormat('sv-SE',{timeZone:'Europe/Moscow',year:'numeric',month:'2-digit',day:'2-digit'}).format(new Date(now())),born=p.birthDate || '';
          let months=null;
          if (/^\d{4}-\d{2}-\d{2}$/.test(born) && born<=day && p.stage==='child') {
            const y=+day.slice(0,4),m=+day.slice(5,7),last=new Date(Date.UTC(y,m,0)).getUTCDate();
            months=(y-+born.slice(0,4))*12 + m-+born.slice(5,7) - (+day.slice(8,10)<Math.min(+born.slice(8,10),last) ? 1 : 0);
          }
          const items=months===null || p.health ? [] : Object.values(hints).filter(h=>h.minMonths<=months && months<h.maxMonths);
          const chosen=data.milestoneSkill ? items.find(h=>h.milestoneSkill===data.milestoneSkill) : items.find(h=>h.id===data.topic);
          return ok({childId:cid,childName:p.childName,months,items,selected:chosen || null,note:'Демонстрация. Возраст не задаёт срок освоения навыка.'});
        }
        case 'daily-plan': return ok({plan:null});
        case 'family-list': return ok({items:[]});
        case 'service': return ok({items:[],blocks:[]});
        case 'suggestion-list': return ok({phase:'collecting',week:'demo',canSubmit:false,remainingSubmissions:0,submissionCount:0,items:[],myVote:null,winners:[]});
        case 'chat': return fail('Это демонстрация интерфейса. Серверный ИИ здесь не подключён. Не вводите личные или медицинские сведения.',409);
        default: return fail('Это демонстрация: действие требует настоящего сервера и здесь не выполняется.',409);
      }
    }
    return {dispatch};
  }
  globalThis.MamaDemoModel = {createDemo};
})();
