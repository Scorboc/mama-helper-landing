"""User content rules across age boundaries, fallbacks and stored context."""
import calendar
import importlib.util
import unittest
from datetime import date
from pathlib import Path
from unittest.mock import patch

def module(name):
    spec=importlib.util.spec_from_file_location(name,Path(__file__).with_name(name+'.py'))
    value=importlib.util.module_from_spec(spec);spec.loader.exec_module(value);return value

policy=module('content_policy')
reminders=module('reminders')

class ContentPolicyTest(unittest.TestCase):
    def test_month_boundaries_and_missing_age(self):
        for born,now,expected in [('2024-02-29','2025-02-28',12),('2025-01-31','2025-03-30',1),('2025-01-31','2025-03-31',2)]:
            self.assertEqual(policy.months({'stage':'child','birthDate':born},date.fromisoformat(now)),expected)
        for profile in (None,{'stage':'pregnancy'}, {'stage':'child','birthDate':'bad'}, {'stage':'child','birthDate':'2099-01-01'}):
            self.assertIsNone(policy.months(profile))
            self.assertNotIn('Игра «',policy.play(profile))
        self.assertIn('беременность',policy.context({'stage':'pregnancy'}))

    def test_fallback_game_is_eligible_at_every_supported_month(self):
        today=date.today()
        for age in range(85):
            y,m=divmod(today.year*12+today.month-1-age,12)
            profile={'stage':'child','birthDate':date(y,m+1,1).isoformat()}
            answer=policy.play(profile)
            allowed=[g for g in policy.catalog.candidates(age) if g['materials']=='Ничего' and g['area'] not in ('Движение','Координация')]
            self.assertTrue(any('«'+g['title']+'»' in answer and g['goal'] in answer for g in allowed),age)
            self.assertIn(f'{age} полных месяцев',policy.context(profile))

    def test_chat_invitations_removed_without_losing_followup_or_safety(self):
        body='Назовите знакомый предмет и подождите реакции.\n\nЕсли хочется ещё идей, напишите в чат.\n\nЧто ребёнок уже пробовал?'
        answer=policy.clean(body)
        self.assertIn('подождите реакции.',answer)
        self.assertIn('Что ребёнок уже пробовал?',answer)
        self.assertNotIn('напишите в чат',answer)
        for invitation in ('Проверьте в чате.','Обсудите это с ИИ.','Спросите у помощника!','Задайте вопрос в наш чат.','Уточните в нашем чате.'):
            self.assertEqual(policy.clean('Полезный совет. '+invitation),'Полезный совет.')
        emergency='Немедленно звоните 112. Не ждите ответа чата.'
        self.assertEqual(policy.clean(emergency),emergency)
        doctor='Обратитесь к врачу, а не проверяйте лечение в чате.'
        self.assertEqual(policy.clean(doctor),doctor)
        self.assertTrue(policy.clean('Напишите в чат.'))
        self.assertEqual(policy.clean('Полезная игра. Если и это надоест, скажите — предложу другой вариант.'),'Полезная игра.')

    def test_model_age_conversion_is_replaced_by_catalogue_bounds(self):
        today=date.today();year,m=divmod(today.year*12+today.month-1-72,12)
        profile={'stage':'child','birthDate':date(year,m+1,1).isoformat()}
        for wrong in ('6–8,5 лет','6–8.5 лет','72–85 месяцев'):
            answer=policy.clean('«Какой звук слышим первым?» ('+wrong+'). Играйте 3–5 минут.',profile)
            self.assertIn('72–73 полных месяцев',answer)
            self.assertIn('3–5 минут',answer)
            self.assertNotIn(wrong,answer)
        answer=policy.clean('«Какой звук слышим первым?» **72–84 полных месяцев** (максимум не включается).',profile)
        self.assertIn('72–73 полных месяцев включительно',answer)
        self.assertNotIn('не включается',answer)
        self.assertEqual(policy.clean(answer,profile),answer)

    def test_play_context_filters_candidates_and_does_not_intrude_on_support(self):
        today=date.today();year,m=divmod(today.year*12+today.month-1-14,12)
        profile={'stage':'child','birthDate':date(year,m+1,1).isoformat()}
        import json
        context=policy.context(profile,'Нужна новая игра без игрушек, ку-ку надоела.')
        games=json.loads(context.split('Каталог: ')[1])
        self.assertTrue(games)
        self.assertTrue(all(g['minMonths']<=14<g['maxMonths'] and g['materials']=='Ничего' for g in games))
        self.assertNotIn('Каталог:',policy.context(profile,'Я устала и хочу просто поговорить. Не хочу занятия.'))

    def test_expired_legacy_reminder_does_not_resurface(self):
        state={'profile':{'stage':'child','birthDate':'2025-01-01','topics':[]},'preferences':{'push':True,'repeat':'day'},'events':{}}
        self.assertEqual([x[0] for x in reminders.due(state,date(2025,1,1))],['child-0'])
        self.assertEqual(reminders.due(state,date(2025,4,1)),[])
        self.assertEqual(reminders.due(state,date(2025,6,30)),[])
        self.assertEqual([x[0] for x in reminders.due(state,date(2025,7,1))],['child-6'])
        self.assertEqual(reminders.due(state,date(2025,10,1)),[])
        self.assertEqual([x[0] for x in reminders.due(state,date(2026,3,1))],['child-12'])
        self.assertEqual(reminders.due(state,date(2026,7,1)),[])

if __name__=='__main__':unittest.main()
