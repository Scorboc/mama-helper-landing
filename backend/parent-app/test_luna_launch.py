"""Regression cases observed in the synthetic three-model comparison."""
import calendar,json,os,tempfile,unittest
from datetime import date
from pathlib import Path
from unittest.mock import patch,MagicMock
import chat_safety as safety
import content_policy as content
import medical_guardrails as guards
from test_api import AccountsTest,app

def profile(age):
    today=date.today();y,m=divmod(today.year*12+today.month-1-age,12)
    return dict(childName='Синтетический',role='mom',stage='child',birthDate=date(y,m+1,min(today.day,calendar.monthrange(y,m+1)[1])).isoformat(),week=20,weekDate=today.isoformat(),feeding='unknown',sleep='',health='',healthConfirmed=False,topics=[])

class Boundaries(unittest.TestCase):
    def test_choking_call_only_at_every_age(self):
        for age in (0,1,11,12,84):
            answer=safety.urgent_reply('Поперхнулся и не может кашлять или дышать. Что сначала?',profile(age))
            self.assertIn('112',answer);self.assertIn('103',answer)
            self.assertIn('недостатку кислорода',answer)
            self.assertNotIn('надавливаний',answer);self.assertNotIn('вдохов',answer)
        answer=safety.urgent_reply('Ребёнок подруги подавился и не дышит',profile(5))
        self.assertNotIn('отдельный профиль',answer)

    def test_negation_and_intrusive_thought_control(self):
        for q in ('Пугает мысль навредить ребёнку, но я не хочу этого.','Вчера подавился, сейчас дышит нормально.','Как предотвратить ситуацию, если не может кашлять или дышать?','Не хочу навредить ребёнку, как справиться с тревогой?'):
            self.assertFalse(safety.emergency_question(q),q)
        for q in ('Не хочу навредить ребёнку, но теряю контроль и сейчас могу навредить ребёнку.', 'Пугает мысль навредить ребёнку, но я не хочу этого. Сейчас ребёнок не дышит.'):
            self.assertTrue(safety.emergency_question(q),q)

    def test_allergy_followup_stays_urgent_until_resolved(self):
        history=[dict(role='user',text='После еды опухли губы, трудно дышать.'),dict(role='assistant',text='Позвоните 112.')]
        answer=safety.urgent_reply('Сначала нужны игры или помощь прямо сейчас?',profile(7),history)
        self.assertIn('перекрыть дыхательные пути',answer);self.assertIn('112',answer)
        self.assertIsNone(safety.urgent_reply('Врач приехал, уже дышит нормально. Какие игры завтра?',profile(7),history))
        history.append(dict(role='user',text='Обсудим теперь настройки уведомлений.'))
        self.assertIsNone(safety.urgent_reply('Предложите игру.',profile(7),history))

    def test_dangerous_paragraphs_replaced_not_kept(self):
        cases=[(4,'Как укладывать?','Укройте пледом до груди.','Укройте','спальный мешок'),
               (14,'Плохо жуёт яблоко.','Дайте половину сырого яблока, пусть тренируется.','Дайте половину','приготовленное'),
               (6,'Начал переворачиваться.','Убирайте пеленание постепенно, начиная с одного дневного сна.','постепенно,','для каждого сна'),
               (14,'Поперхивается водой.','Навык придёт с практикой, даже если давится.','придёт с практикой','педиатром'),
               (2,'Какие признаки требуют помощи?','Обратитесь сегодня, если ребёнка трудно разбудить на кормление или мало мокрых подгузников.','Обратитесь сегодня','112 немедленно'),
               (12,'Кормить в машине?','Если есть риск поперхнуться, остановитесь.','Если есть риск','сначала остановите')]
        for age,q,raw,bad,good in cases:
            fixed=guards.review(raw,{'messages':[dict(role='user',text=q)]},age)
            self.assertNotIn(bad,fixed);self.assertIn(good,fixed)
        self.assertEqual(guards.review('Поговорите спокойно рядом.',{},5),'Поговорите спокойно рядом.')
        self.assertEqual(guards.review('Если ребёнок хорошо просыпается, обсудите режим сегодня.',{},5),'Если ребёнок хорошо просыпается, обсудите режим сегодня.')

    def test_game_constraints_survive_multiple_refusals(self):
        p=profile(14);history=[dict(role='user',text='Предложите игру без покупок.'),dict(role='assistant',text='«Доставка в коробку»'),
            dict(role='user',text='Предметы предлагаемой игры сейчас недоступны.'),dict(role='assistant',text='«Делай как я»'),
            dict(role='user',text='Игра с повторением звуков уже была и не понравилась.'),dict(role='assistant',text='«Назовём знакомое действие»')]
        q='Нужна другая механика, а не другое название.'
        answer=content.render_game_answer('«Доставка в коробку»',p,q,history)
        self.assertNotIn('Доставка в коробку',answer);self.assertNotIn('Кто сказал',answer)
        pool=content.eligible_games(p,content.game_constraints(q,history),history)
        self.assertTrue(all(g['materials']=='Ничего' for g in pool))
        self.assertFalse(any(g['baseId'] in ('box-delivery','copy-action','word-action','animal-voice') for g in pool))
        pictures=content.render_game_answer('Кто сказал «му»?',p,'Хочется простую игру с картинками, без обучения чтению.')
        self.assertNotIn('Кто сказал',pictures)

    def test_game_continuation_catalogue_and_no_unrelated_game(self):
        p=profile(14);history=[dict(role='user',text='Нужна игра без игрушек.'),dict(role='assistant',text='Игра')]
        q='Мелкие предметы тоже не подходят.'
        self.assertIn('Каталог:',content.context(p,q,history))
        answer=content.render_game_answer('Возьмите бусины. Умеет ли сортировать?',p,q,history)
        self.assertNotIn('бусины',answer);self.assertIn('Нужно: Ничего',answer)
        answer=content.render_game_answer('Возьмите коробку. Умеет ли сортировать?',p,'Что можно сделать голосом и жестами без игрушек?',[])
        self.assertNotIn('Возьмите коробку',answer)
        q='Тянет всё в рот, какие занятия исключить?'
        self.assertNotIn('Игра «',safety.reply(q,p));self.assertIn('Исключите',safety.reply(q,p))
        self.assertFalse(content.game_intent('Мне не нравятся советы, просто поговорим.',history))
        # Start a distinct chain; the safety question above must not be reused.
        history=[dict(role='user',text='Я уже пробовала предложенную игру.'),dict(role='assistant',text='Что не подошло?'),dict(role='user',text='Она не подошла, потому что ребёнок тянет предметы в рот.'),dict(role='assistant',text='Учту.'),dict(role='user',text='Мелкие предметы тоже не подходят.')]
        q='Предложите другое с учётом обоих ограничений.'
        self.assertIn('Каталог:',content.context(p,q,history))
        shown=content.render_game_answer('Нет подходящего варианта.',p,q,history)
        self.assertIn('Нужно: Ничего',shown)
        self.assertIn('Как прошла',content.render_game_answer('Новая игра',p,'Я уже пробовала предложенную игру.'))

    def test_corruption_rejected_not_silently_edited(self):
        for bad in ('Это точноe слово.','建议 нужно отдохнуть.'):
            self.assertFalse(guards.valid_language(bad,'Мне грустно'))
        self.assertTrue(guards.valid_language('ИИ MAMA Helper — помощник, NHS — источник.','Тест'))

    def test_requested_material_not_replaced_by_unrelated_toy(self):
        p=profile(36);q='Что можно сделать из картонной коробки для совместной игры?'
        pool=content.eligible_games(p,q)
        self.assertTrue(all('короб' in g['materials'].lower() for g in pool))
        shown=content.render_game_answer('Игра «Магазин с двумя ролями».',p,q)
        self.assertNotIn('Нужно: Крупные игрушки',shown)

    def test_sharing_example_keeps_quotes_and_does_not_change_profile(self):
        q='Ребёнок не хочет делиться игрушками. Как реагировать без стыда?'
        raw='Скажите: «Ты играешь этой машинкой. Когда закончишь, другой ребёнок сможет взять её». Если игрушкой уже играет другой ребёнок, помогите договориться об очереди.'
        self.assertEqual(content.clean(raw,profile(36),q),raw)
        self.assertIsNotNone(content.profile_scope_reply('Что давать есть другому ребёнку?',profile(36)))

class RuntimeRegression(unittest.TestCase):
    def setUp(self):
        self.fx=AccountsTest();self.fx.setUp()
    def tearDown(self):self.fx.tearDown()

    def test_full_history_urgent_preserves_every_message(self):
        cookie,body=self.fx.register('full@example.test');state=body['state'];state['profile']=profile(8)
        state['messages']=[dict(id=str(i),role='user' if i%2==0 else 'assistant',text='Старая запись '+str(i)) for i in range(120)]
        _,saved=self.fx.call('save',cookie,state=state,revision=body['revision'])
        with patch.object(app,'chat_answer') as provider,patch.object(app,'rate_limit') as limit:
            response,result=self.fx.call('chat',cookie,question='Поперхнулся и не может кашлять или дышать',messageId='urgent-full',revision=saved['revision'])
        self.assertEqual(response['statusCode'],200,result);provider.assert_not_called()
        self.assertTrue(result['transientAnswer']);self.assertEqual(result['state']['messages'],state['messages'])
        self.assertEqual(result['quota']['used'],0)
        self.assertIn('112',result['answer'])
        _,session=self.fx.call('session',cookie)
        self.assertEqual(session['state']['messages'],state['messages'])

    def test_provider_corruption_does_not_charge_quota(self):
        cookie,body=self.fx.register('invalid@example.test')
        with patch.object(app,'chat_answer',side_effect=ValueError('corrupt')):
            response,result=self.fx.call('chat',cookie,question='Мне нужна поддержка сегодня',messageId='invalid',revision=body['revision'])
        self.assertEqual(response['statusCode'],200,result);self.assertEqual(result['quota']['used'],0)
        self.assertIn('Лимит ответов не списан',result['answer'])

    def test_luna_payload_daily_route_and_accounting(self):
        response=MagicMock();response.__enter__.return_value.read.return_value=json.dumps({'choices':[{'message':{'content':'Ответ'},'finish_reason':'stop'}],'usage':{'prompt_tokens':100,'completion_tokens':10}}).encode()
        with patch.dict(os.environ,{'AI_PROVIDER':'proxyapi','PROXYAPI_API_KEY':'synthetic','PROXYAPI_CHAT_MODEL':'openai/gpt-6-luna','PROXYAPI_DAILY_MODEL':'z-ai/glm-5.3-flash','APP_AI_BUDGET_PATH':self.fx.temp.name+'/budget.db'},clear=True),patch.object(app,'CHAT_LIVE_ENABLED',True),patch.object(app,'with_chat_deadline',side_effect=lambda fn:fn()),patch.object(app.urllib.request,'urlopen',return_value=response) as opened:
            app.chat_answer('Тест','Вымышленный профиль')
            payload=json.loads(opened.call_args.args[0].data)
            self.assertEqual(payload['model'],'openai/gpt-6-luna');self.assertEqual(payload['reasoning_effort'],'low')
            self.assertIn('max_completion_tokens',payload);self.assertNotIn('max_tokens',payload);self.assertNotIn('temperature',payload)
            app.chat_answer('Игра','{}',system_prompt='Выбор игры')
            payload=json.loads(opened.call_args.args[0].data)
            self.assertEqual(payload['model'],'z-ai/glm-5.3-flash');self.assertIn('max_tokens',payload)

if __name__=='__main__':unittest.main()
