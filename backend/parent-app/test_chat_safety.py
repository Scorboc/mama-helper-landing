import importlib.util
from pathlib import Path
import unittest

spec=importlib.util.spec_from_file_location('safety',Path(__file__).with_name('chat_safety.py'))
safety=importlib.util.module_from_spec(spec);spec.loader.exec_module(safety)

class SafetyTest(unittest.TestCase):
    def test_poisoning_survives_profile_filter(self):
        from datetime import date
        profile={'stage':'child','birthDate':date.today().isoformat()}
        raw=safety.reply('Проглотил чистящее средство. Нужно ли вызывать рвоту?',profile)
        shown=safety._policy.clean(raw,profile)
        self.assertTrue(shown.startswith('Звоните 112 сейчас'))
        self.assertIn('Не вызывайте рвоту',shown)
        self.assertIn('возраст ребёнка',shown)

    def test_honey_and_food_position(self):
        profile={'stage':'child','birthDate':'2026-03-12'}
        for q in ('Можно мед в промышленной выпечке?','Кашу с медом можно?'):
            self.assertIn('Не делайте исключение',safety.reply(q,profile))
        raw=safety.reply('Сидит неустойчиво, можно кормить полусидя пюре?',profile)
        self.assertIn('нельзя давать полулёжа или полусидя',raw)
        self.assertIn('вертикальное положение',raw)
        for question in ('Ещё не уверенно удерживает позу сидя. Как выбирать способ кормления?',
                         'Можно пюре в шезлонге?', 'Неустойчивое положение сидя, как давать прикорм?'):
            answer=safety.reply(question,profile)
            self.assertIn('устойчивое вертикальное положение',answer)
            self.assertNotIn('в шезлонге',answer)

    def test_new_wetting_not_attributed_to_motives(self):
        answer=safety.reply('После рождения младшего снова мочится в трусики. Это назло?')
        self.assertIn('нельзя определить причину',answer)
        self.assertIn('запишитесь к педиатру',answer)
        self.assertIn('в тот же день',answer)
    def test_generated_hazards_reviewed(self):
        self.assertNotIn('Надуйте',safety.review('Надуйте шарик и дайте малышу',{}))
        self.assertIn('112',safety.review('К врачу, если трудно глотать или дышать.',{}))
        self.assertEqual(safety.review('Спокойно поговорите рядом.',{}),'Спокойно поговорите рядом.')
        partner=safety.review('Если партнёр согласился, дайте ему сделать это по-своему, без поправок по ходу — иначе просьба превращается в контроль.',{})
        self.assertIn('Если действие создаёт риск ребёнку, остановите',partner)
        self.assertNotIn('превращается в контроль',partner)
    def test_night_fright_and_kitchen_game(self):
        night=safety.reply('Просыпаюсь ночью и ищу младенца под одеялом')
        self.assertIn('продолжайте отвечать',night)
        self.assertNotIn('до утра',night)
        game=safety.reply('Игра для речи на кухне вместо мультиков')
        self.assertIn('готовка уже закончена',game)
        self.assertIn('возраст неизвестен',game)
    def test_unsafe_sleep_and_play(self):
        self.assertIn('Не грейте матрас',safety.reply('Месячный малыш спит на мне на диване'))
        self.assertIn('пока не используйте',safety.reply('Кроватка крошится и есть щепки'))
        self.assertIn('Присмотр не делает мелкие',safety.reply('Игра на моторику, все тянет в рот'))
        self.assertIn('Не заклеивайте глаза',safety.reply('Боится помыть голову'))
        self.assertIn('без предметов',safety.reply('Игра без мелких предметов',{'stage':'child','birthDate':__import__('datetime').date.today().isoformat()}))
        self.assertIn('возраст неизвестен',safety.reply('Игра без игрушек и мелких предметов'))
    def test_suspected_battery_without_symptoms(self):
        for q in ('Пропала батарейка, ребёнок играет.', 'Дочка проглотила батарейку?', 'Не могу найти батарейку от пульта'):
            self.assertIn('Не ждите симптомов',safety.reply(q))
    def test_head_banging_not_left_alone(self):
        for q in ('Сын бьётся головой о кровать','Дочка стучится лбом об пол'):
            answer=safety.reply(q)
            self.assertIn('не оставляйте его одного',answer)
            self.assertIn('не привязывайте мягкие бортики',answer)
    def test_unwanted_thought_is_not_intent(self):
        answer=safety.reply('Пугает мысль навредить ребёнку, не хочу этого, не собираюсь.')
        self.assertIn('сама по себе не означает',answer)
        self.assertIn('звоните 112',safety.reply('Навязчивая мысль, не хочу, но теряю контроль, сейчас ударю'))
        self.assertIsNone(safety.reply('После удара головой ребенок без сознания'))
    def test_normal_questions_not_intercepted(self):
        for q in ('Как мыть голову?', 'Какие игрушки без батареек?', 'Я не хочу готовить сегодня'):
            self.assertIsNone(safety.reply(q))

    def test_repeated_breathing_checks_do_not_get_exposure_exercise(self):
        answer=safety.reply('Постоянно проверяю дыхание малыша и не могу отдохнуть.')
        self.assertIn('Не нужно назначать себе запрет',answer)
        self.assertNotIn('задержать проверку',answer)
        listening=safety.reply('Постоянно проверяю дыхание, тревожно. Только выслушайте, без советов.')
        self.assertNotIn('112',listening)
        self.assertNotIn('упражнение:',listening)
        acute=safety.reply('Постоянно проверяю дыхание, но сейчас ребёнок синеет.')
        self.assertIn('немедленно звоните 112',acute)

    def test_current_harm_followup_never_waits_in_provider_queue(self):
        history=[{'role':'user','text':'Сейчас теряю контроль и боюсь, что ударю ребёнка.'},
                 {'role':'assistant','text':'Звоните 112 сейчас.'}]
        for q in ('Ребёнок в кроватке. Нужна помощь сейчас.','Могу я просто ждать следующего ответа чата?'):
            self.assertIn('Не ждите следующего ответа чата',safety.followup_reply(q,history))
        self.assertIsNone(safety.followup_reply('Врач приехал. Можно ждать ответа чата?',history))
        self.assertIsNone(safety.followup_reply('Я устала. Что обсудить?',history))
        self.assertIsNone(safety.followup_reply('Можно ждать ответа чата?',[]))
