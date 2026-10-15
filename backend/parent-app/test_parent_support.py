"""Synthetic boundary and API tests; external AI must not be called."""
import json
import unittest
from unittest.mock import MagicMock, patch

import parent_support as support
import prompt_policy
from test_api import AccountsTest, app


class AdultSelfHelpTest(unittest.TestCase):
    def test_how_should_i_breathe_is_not_misread_as_not_breathing(self):
        question = 'Я тревожусь, как мне дышать, чтобы сделать паузу?'
        self.assertFalse(app.EMERGENCY_PATTERN.search(question))
        self.assertIn('мягкое дыхание', app._safety.reply(question))
        for acute in ('Ребёнок не дышит.', 'Я сейчас не дышу нормально, задыхаюсь.'):
            self.assertTrue(app.EMERGENCY_PATTERN.search(acute.lower()), acute)

    def test_optional_breathing_has_no_forcing_or_required_timer(self):
        for question in ('Я тревожусь, покажи дыхательную практику.',
                         'Дай мне упражнение на дыхание при стрессе.',
                         'Для мамы можно дыхательную практику?'):
            with self.subTest(question=question):
                answer = support.reply(question)
                self.assertIn('без усилия', answer)
                self.assertIn('не задерживайте', answer)
                self.assertIn('прекратите', answer)
                self.assertIn('Счёт необязателен', answer)
                self.assertNotIn('https://', answer)

    def test_sources_are_verified_and_shown_only_on_request(self):
        answer = support.reply('Покажи мне официальную дыхательную практику, дай источник.')
        self.assertIn(support.SOURCES['breathing'][1], answer)
        self.assertIn('не оценивала наш чат', answer)

    def test_listening_has_no_forced_exercise(self):
        for question in ('Мне тяжело, без советов и дыхательных практик.',
                         'Я устала, только выслушайте.',
                         'Не предлагай упражнения, мне нужно поговорить.'):
            self.assertIsNone(support.reply(question), question)

    def test_grounding_allows_accessibility_and_no_breath_focus(self):
        for question in ('Мне нужна практика заземления без дыхания.',
                         'Я не могу стоять, покажи заземление.',
                         'Мне дыхательная практика не подходит, хочу другое.'):
            answer = support.reply(question)
            self.assertIn('без управления дыханием', answer)
            self.assertIn('только доступные', answer)
            self.assertNotIn('встаньте', answer.lower())

    def test_grounding_uses_available_sense_and_does_not_force_unavailable_one(self):
        for question in ('Я не вижу, как выполнить заземление?', 'Я не слышу, хочу заземление.'):
            answer = support.reply(question)
            self.assertIn('только доступное', answer)
            self.assertNotIn('один звук', answer)
            self.assertNotIn('его цвет', answer)

    def test_driving_and_child_supervision_outrank_practice(self):
        self.assertIn('сначала остановитесь', support.reply('Я за рулём, дай дыхательную практику.'))
        self.assertIn('Не оставляйте', support.reply('Мне нужна дыхательная практика, можно оставить ребёнка одного?'))

    def test_child_exercises_do_not_receive_adult_protocol(self):
        for question in ('Мне нужно дыхательное упражнение для ребёнка.',
                         'Ребёнку нужна дыхательная практика, я мама.',
                         'Как ребёнку успокоиться, покажите дыхательную практику?'):
            self.assertIsNone(support.reply(question), question)

    def test_discomfort_stops_exercise_without_diagnosis(self):
        question = 'Мне от дыхательной практики кружится голова. Можно продолжать?'
        answer = support.reply(question)
        self.assertTrue(answer.startswith('Прекратите упражнение'))
        self.assertNotIn('это нормально', answer)
        self.assertIn('обратитесь за медицинской помощью', answer)

    def test_current_physical_red_flags_outrank_practice_and_no_advice(self):
        for question in ('Мне сейчас давит в груди. Покажи дыхательную практику.',
                         'У меня сейчас тяжело дышать, без советов.',
                         'Мне вчера было плохо, но сейчас сдавило грудь, хочу дыхательную практику.',
                         'У меня сейчас нет боли в груди, но тяжело дышать. Дай дыхательную практику.',
                         'Мне сейчас давит в груди, но нет одышки. Хочу дыхательную практику.'):
            self.assertTrue(support.reply(question).startswith('Сейчас звоните 112'), question)

    def test_past_denied_and_hypothetical_red_flags_are_distinct(self):
        for question in ('У меня раньше была боль в груди, сейчас нет боли. Хочу заземление.',
                         'Мне вчера было тяжело дышать. Покажи заземление.',
                         'У меня сейчас не болит грудь. Дай дыхательную практику.'):
            self.assertIsNone(support.urgent_reply(question), question)
        hypothetical = support.urgent_reply('Если мне внезапно станет тяжело дышать и будет боль в груди, что делать?')
        self.assertTrue(hypothetical.startswith('Если это происходит сейчас'))

    def test_new_perceptual_symptoms_are_not_treated_by_breathing(self):
        question = 'Я после родов слышу голоса, которых нет. Покажи дыхательную практику.'
        answer = support.reply(question)
        self.assertIn('срочная медицинская оценка сегодня', answer)
        self.assertNotIn('Это психоз', answer)

    def test_known_dangerous_model_instructions_are_replaced(self):
        question = 'Мне тревожно, как помочь себе?'
        for raw in ('Задержите дыхание на семь секунд.',
                    'Дышите в бумажный пакет.',
                    'Дышите максимально глубоко.',
                    'Продолжайте упражнение несмотря на головокружение.',
                    'Попробуйте схему 4–7–8.'):
            self.assertEqual(support.review(raw, question), support.BREATHING, raw)

    def test_correct_warnings_and_other_topics_are_preserved(self):
        for raw in ('Не задерживайте дыхание.', 'Нельзя дышать в бумажный пакет.',
                    'Не используйте схему 4–7–8.', 'Можно просто рассказать, что произошло.'):
            self.assertEqual(support.review(raw, 'Мне тяжело.'), raw)
        self.assertEqual(support.review('Задержите дыхание.', 'Что такое эта фраза в книге?'), 'Задержите дыхание.')

    def test_final_check_keeps_emergency_even_if_model_claims_stress(self):
        state = {'messages':[{'role':'user','text':'У меня сейчас сдавило грудь.'}]}
        answer = app._safety.review('Это точно стресс. Попробуйте схему 4–7–8.', state)
        self.assertTrue(answer.startswith('Сейчас звоните 112'))

    def test_crisis_followup_with_practice_request_keeps_handoff(self):
        history = [{'role':'user','text':'Сейчас теряю контроль и боюсь, что ударю ребёнка.'},
                   {'role':'assistant','text':'Звоните 112 сейчас.'}]
        self.assertIn('Не ждите', app._safety.followup_reply('Покажи мне дыхательную практику.', history))
        history += [{'role':'user','text':'Бригада приехала, врач рядом.'}]
        self.assertIsNone(app._safety.followup_reply('Покажи мне дыхательную практику.', history))


class AdultSelfHelpApiTest(unittest.TestCase):
    def setUp(self):
        self.fixture = AccountsTest()
        self.fixture.setUp()

    def tearDown(self):
        self.fixture.tearDown()

    def test_local_practice_saves_reply_without_external_call_or_quota(self):
        cookie, initial = self.fixture.register('adult-practice@example.test')
        with patch.object(app, 'chat_answer') as external:
            response, body = self.fixture.call('chat', cookie,
                question='Мне тревожно, покажи дыхательную практику.',
                messageId='adult-practice', revision=initial['revision'])
        self.assertEqual(response['statusCode'], 200, body)
        self.assertIn('без усилия', body['answer'])
        self.assertEqual(body['quota']['used'], 0)
        external.assert_not_called()
        _, session = self.fixture.call('session', cookie)
        self.assertEqual(session['state']['messages'][-1]['text'], body['answer'])

    def test_natural_breath_question_does_not_get_crisis_boilerplate(self):
        cookie, initial = self.fixture.register('adult-breath-question@example.test')
        with patch.object(app, 'chat_answer') as external:
            response, body = self.fixture.call('chat', cookie,
                question='Я тревожусь, как мне дышать, чтобы сделать паузу?',
                messageId='adult-how-breathe', revision=initial['revision'])
        self.assertEqual(response['statusCode'], 200, body)
        self.assertIn('мягкое дыхание', body['answer'])
        self.assertNotIn('112', body['answer'])
        external.assert_not_called()

    def test_crisis_in_history_outranks_new_local_practice(self):
        cookie, initial = self.fixture.register('adult-crisis@example.test')
        state = initial['state']
        state['messages'] = [{'id':'risk','role':'user','text':'Сейчас теряю контроль и боюсь, что ударю ребёнка.'},
                             {'id':'handoff','role':'assistant','text':'Звоните 112 сейчас.'}]
        response, saved = self.fixture.call('save', cookie, state=state, revision=initial['revision'])
        self.assertEqual(response['statusCode'], 200, saved)
        with patch.object(app, 'chat_answer') as external:
            response, body = self.fixture.call('chat', cookie,
                question='Покажи мне дыхательную практику.', messageId='risk-followup', revision=saved['revision'])
        self.assertEqual(response['statusCode'], 200, body)
        self.assertTrue(body['answer'].startswith('Не ждите'))
        external.assert_not_called()

    def test_generated_support_receives_rules_and_preserves_user_choice(self):
        response = MagicMock()
        response.__enter__.return_value.read.return_value = json.dumps({'choices':[{'message':{'content':'Synthetic answer'},'finish_reason':'stop'}], 'usage':{'prompt_tokens':10,'completion_tokens':5}}).encode()
        import os
        with patch.dict(os.environ, {'AI_PROVIDER':'proxyapi','PROXYAPI_API_KEY':'synthetic-key'}), patch.object(app, 'CHAT_LIVE_ENABLED', True), patch.object(app.urllib.request, 'urlopen', return_value=response) as opened:
            app.chat_answer('Я устала, только выслушайте.', 'Synthetic context')
        payload = json.loads(opened.call_args.args[0].data)
        instruction = payload['messages'][0]['content']
        self.assertIn('### 19.', instruction)
        self.assertIn('Выслушивание важнее упражнения', instruction)
        self.assertIn('не заменяет', support.BREATHING)
        self.assertEqual(payload['messages'][-1]['content'], 'Я устала, только выслушайте.')
        self.assertLess(len(prompt_policy.reply_check('Хочу игру').encode()), 2000)


if __name__ == '__main__':
    unittest.main()
