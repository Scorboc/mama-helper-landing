import unittest
import answer_scenarios as a
import importlib.util
from pathlib import Path

spec=importlib.util.spec_from_file_location('scenario_app',Path(__file__).with_name('index.py'))
app=importlib.util.module_from_spec(spec);spec.loader.exec_module(app)

class ScenarioTests(unittest.TestCase):
    def test_unrelated_has_no_template(self):
        for q in ('Спасибо!', 'Как поменять имя?', 'Я беременна и спрашиваю про своё питание.'):
            self.assertEqual(a.context(q), '')

    def test_urgency_beats_formula(self):
        self.assertEqual(a.select('Рвота зелёная после смеси'), ['vomiting', 'formula-change'])

    def test_bank_is_complete_and_bounded(self):
        self.assertEqual(len(a.BANK), 20)
        self.assertEqual(set(a.BANK), set(a.PATTERNS))
        self.assertLessEqual(len(a.select('Температура, сыпь, рвота после смеси')), 2)
        for id, row in a.BANK.items():
            self.assertTrue(row['guardrails'])
            self.assertTrue(row['applicability'])
            if id != 'doctor': self.assertTrue(row['sources'])

    def test_age_conditions_kept(self):
        self.assertIn('12', a.context('козье молоко'))
        self.assertIn('готовност', a.context('Когда начинать прикорм'))
        self.assertIn('3', a.context('температура'))

    def test_no_export_data(self):
        self.assertNotIn('from_id', str(a.BANK))
        self.assertIn('Не спрашивай повторно', a.TONE)

    def test_active_child_only_and_no_mutation(self):
        import copy
        state=app.blank_state()
        state['profile']={'stage':'child','role':'mom','birthDate':'2025-10-03','feeding':'breast','childName':'Аня'}
        state['children']=[{'id':'other','data':{'profile':{'childName':'Другой ребёнок'},'messages':[]}}]
        before=copy.deepcopy(state)
        text=app.build_chat_context(state,'Как завершить ГВ?')
        self.assertIn('Аня',text)
        self.assertNotIn('Другой ребёнок',text)
        self.assertIn('weaning',text)
        self.assertEqual(state,before)

    def test_pregnancy_does_not_invent_child_age(self):
        from datetime import date
        state=app.blank_state();state['profile']={'stage':'pregnancy','role':'mom','week':24,'weekDate':date.today().isoformat()}
        text=app.build_chat_context(state,'Моё питание')
        self.assertIn('24 полных недель',text)
        self.assertNotIn('solids-start',text)

    def test_critical_regressions(self):
        for q in ('Сегодня трудно разбудить','Синеет и тяжело дышит'):
            self.assertIn('112',app._safety.reply(q))
        self.assertIn('не ожидая',app._safety.reply('Ребёнок перестал делать то, что уже умел'))
        self.assertIn('сегодня',app._safety.reply('Кровь в стуле и нет прибавки'))
        self.assertIn('не считайте пюре',app._safety.reply('Голову держит неустойчиво. Пора кусочки?').lower())
        self.assertIn('до года',app._safety.reply('Как завершить ГВ?').lower())
        self.assertIn('не буду',app._safety.reply('Боюсь давать кусочки'))

    def test_immediate_risk_precedes_topic(self):
        self.assertIsNone(app._safety.reply('Как завершить ГВ? Ребёнок не дышит'))
        self.assertIsNone(app._safety.reply('При каждом кусочке ребёнок задыхается. Просто продолжать тренироваться?'))
        self.assertIn('112',app._safety.reply('Как завершить ГВ? Сейчас ударю ребёнка'))

if __name__ == '__main__': unittest.main()
