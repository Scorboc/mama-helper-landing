"""Offline regressions for live QA B1/B2; synthetic profiles only."""
from datetime import date
import unittest

import chat_safety as safety
import medical_guardrails


def profile(months):
    today = date.today()
    year, month = divmod(today.year * 12 + today.month - 1 - months, 12)
    return {'stage': 'child', 'birthDate': date(year, month + 1, 1).isoformat()}


class InjuryAndRollTest(unittest.TestCase):
    def test_e7_changing_table_is_not_swaddling(self):
        for question in ('Упал с дивана, ударился головой, сейчас вроде нормально. Что делать?',
                         'Упал с пеленального стола, ударился головой',
                         'Сегодня перевернулась и упала с кровати'):
            with self.subTest(question=question):
                self.assertNotIn('При первых попытках переворачиваться пеленание прекращают.',
                                 self.shown(question, 10))
        for answer in ('Не оставляйте на пеленальном столике.',
                       'С пеленального стола можно упасть.',
                       'Постепенно уберите вещи с пеленального столика.'):
            with self.subTest(answer=answer):
                state = {'messages': [{'role': 'user', 'text': 'Сегодня перевернулся и упал'}]}
                self.assertEqual(answer, medical_guardrails.review(answer, state, 10))

    def test_e7_swaddling_still_gets_roll_warning(self):
        for answer in ('Обсудим пеленание.', 'Можно ли пеленать?',
                       'Пелёнка для сна.', 'Ребёнок запелёнат.',
                       'Малыша пеленают.', 'Ребёнок распелёнат.'):
            with self.subTest(answer=answer):
                state = {'messages': [{'role': 'user', 'text': 'Как подготовиться ко сну?'}]}
                reviewed = medical_guardrails.review(answer, state, 5)
                self.assertIn('При первых попытках переворачиваться пеленание прекращают.', reviewed)

    def test_claude_e1_e2_objects_are_not_roll_milestones(self):
        for months, question in (
            (5, 'Мия сегодня перевернула на себя чашку с горячим чаем'),
            (8, 'Сегодня перевернул тарелку с кашей, как отучить?'),
        ):
            with self.subTest(question=question):
                self.assertNotIn('важное событие', safety.reply(question, profile(months)) or '')

    def test_claude_e3_fall_precedes_roll_without_head_word(self):
        for surface in ('дивана', 'кровати', 'стола', 'пеленального стола', 'стула', 'рук'):
            with self.subTest(surface=surface):
                answer = self.shown('Сегодня перевернулась и упала с ' + surface, 5)
                self.assertIn('педиатром', answer)
                self.assertNotIn('важное событие', answer)

    def test_claude_e4_adult_fainting(self):
        question = 'Я упала в обморок, кружится голова, ребёнок со мной'
        answer = safety.urgent_reply(question, profile(10))
        self.assertIsNotNone(answer)
        for text in ('112', 'кроватк', 'взрослого', 'боль в груди', 'одышка', 'нарушение речи'):
            self.assertIn(text, answer)
        self.assertNotIn('осмотрите ребёнка', safety.reply(question, profile(10)) or '')

    def test_adult_impact_is_not_child_injury(self):
        for question in ('Я упала, у меня кружится голова', 'Я ударилась головой'):
            with self.subTest(question=question):
                answer = safety.reply(question, profile(10)) or ''
                self.assertNotIn('осмотрите ребёнка', answer)
                self.assertNotIn('Ты злишься', answer)

    def test_claude_e5_injury_red_flags_start_with_call(self):
        for symptom in ('рвота два раза', 'потерял сознание', 'отключился', 'судороги',
                        'не просыпается', 'трудно разбудить', 'вялый',
                        'кровь из носа', 'жидкость из ушей', 'не двигает рукой',
                        'не двигает ногой', 'выбухает родничок'):
            with self.subTest(symptom=symptom):
                question = 'Уронила его, ударился головой, плачет и ' + symptom
                answer = safety.urgent_reply(question, profile(12)) or self.shown(question, 12)
                self.assertTrue(answer.startswith('Звоните 112 сейчас'), answer)
                self.assertNotIn('наблюдая', answer)

    def test_claude_e6_light_object_is_not_child_fall(self):
        answer = safety.reply('Упала погремушка ему на голову, он даже не заметил', profile(10))
        self.assertIsNone(answer)

    def test_original_second_roll_phrase(self):
        self.assertIn('важное событие', self.shown('Наконец-то перевернулась на живот сама!', 5))

    def shown(self, question, months):
        child = profile(months)
        answer = safety.reply(question, child)
        self.assertIsNotNone(answer)
        state = {'profile': child, 'messages': [{'role': 'user', 'text': question}]}
        return safety.review(safety._policy.clean(answer, child), state)

    def test_accidental_head_impacts_get_injury_advice(self):
        for question in (
            'Упал с дивана, ударился головой, сейчас вроде нормально. Что делать?',
            'Упал с кровати, ударился головой',
            'Упал с пеленального стола, ударился головой',
            'Стукнулся головой об угол',
        ):
            with self.subTest(question=question):
                answer = self.shown(question, 10)
                for text in ('осмотрите', 'ближайшие часы', 'педиатром', 'даже если',
                             'Спать можно', 'у врача', '112', 'потере сознания',
                             'судорогах', 'повторной рвоте', 'сонливости', 'вялости',
                             'утешить', 'носа', 'ушей', 'нарушении движений', 'родничка'):
                    self.assertIn(text, answer)
                for text in ('Ты злишься', 'бортики', 'повторяющиеся эпизоды'):
                    self.assertNotIn(text, answer)
                self.assertNotRegex(answer, r'\b\d+\s*(?:минут|час)')

    def test_emotional_head_banging_stays_behavioral(self):
        answer = self.shown('Бьётся головой о пол, когда злится', 10)
        self.assertIn('Ты злишься', answer)
        self.assertIn('не оставляйте его одного', answer)

    def test_reported_roll_includes_fall_prevention(self):
        answer = self.shown('Мия сегодня впервые перевернулась с живота на спину!', 5)
        for text in ('пеленальном столе', 'диване', 'кровати', 'не оставлять', 'упасть'):
            self.assertIn(text, answer)
        self.assertNotIn('Возраст не подтверждает отсутствие этого навыка', answer)

    def test_swaddling_guard_does_not_append_irrelevant_age_claim(self):
        answer = medical_guardrails.review(
            'Обсудим пеленание.',
            {'messages': [{'role': 'user', 'text': 'Мия впервые перевернулась!'}]}, 5)
        self.assertIn('пеленание прекращают', answer)
        self.assertNotIn('Возраст не подтверждает отсутствие этого навыка', answer)

    def test_lost_roll_still_needs_pediatrician(self):
        answer = self.shown('Перестала делать то, что уже умела: раньше перевернулась сама', 5)
        self.assertIn('педиатр', answer)
        self.assertNotIn('важное событие', answer)

    def test_emergency_still_precedes_injury_and_roll(self):
        for question in ('Упал с дивана, ударился головой, сейчас без сознания',
                         'Впервые перевернулась, сейчас судороги'):
            with self.subTest(question=question):
                self.assertIn('112', safety.urgent_reply(question, profile(5)))
                self.assertIsNone(safety.reply(question, profile(5)))

