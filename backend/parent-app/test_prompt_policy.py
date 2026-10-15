import json
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock
import prompt_policy
from test_api import AccountsTest, app


class ApprovedInstructionTest(unittest.TestCase):
    def setUp(self):
        self.fixture = AccountsTest()
        self.fixture.setUp()

    def tearDown(self):
        self.fixture.tearDown()

    def test_active_chat_matches_owner_approved_section_exactly(self):
        draft = (Path(__file__).resolve().parents[2] / 'docs/ai/MAMA_SYSTEM_PROMPT_DRAFT.md').read_text(encoding='utf-8')
        section = draft.split('## Системный промпт\n', 1)[1].split('## Отдельные режимы:', 1)[0].strip() if '## Системный промпт\n' in draft else draft.strip()
        self.assertEqual(app.CHAT_SYSTEM_PROMPT, section)
        self.assertEqual(prompt_policy.VERSION, prompt_policy.MANIFEST['version'])
        self.assertEqual(app.CHAT_SYSTEM_PROMPT, prompt_policy.approved_part('chat'))

    def test_modified_instruction_fails_instead_of_loading_unreviewed_text(self):
        with patch.object(Path, 'read_bytes', return_value=b'unapproved changes'):
            with self.assertRaises(RuntimeError):
                prompt_policy.approved_part('chat')

    def test_reply_check_does_not_duplicate_large_policy_sections(self):
        reminder=prompt_policy.reply_check('Нужна тихая игра')
        self.assertLess(len(reminder.encode('utf-8')),4000)
        self.assertLess(len(reminder),len(app.CHAT_SYSTEM_PROMPT)/3)
        self.assertRegex(prompt_policy.reply_check('Сколько сна?'),r'итог сна бери из (?:рассчитанной сводки|поля сводки recordedSleepMinutesTotal)')

    def test_fallback_never_guesses_topic_age_or_testing_state(self):
        for q in ('Партнёра нет, я воспитываю одна.','Мне нужна поддержка без советов.','Нужна игра.'):
            answer=app.fallback_chat_answer(q,app.blank_state(),'parse_error')
            self.assertIn('ИИ вернул неполный ответ',answer)
            self.assertIn('Лимит ответов не списан',answer)
            for wrong in ('Для сна','назовите возраст','для теста','В тестовом режиме','просьбу к близкому'):
                self.assertNotIn(wrong,answer)

    def test_emergency_is_not_blocked_by_other_child_scope_or_quota(self):
        cookie, body = self.fixture.register('urgent-scope@example.test')
        state = body['state']
        state['profile'] = {'childName':'Тест','role':'mom','stage':'child','birthDate':'2023-09-17','week':20,'weekDate':'2026-10-12','feeding':'unknown','sleep':'','health':'','healthConfirmed':False,'topics':[]}
        response, saved = self.fixture.call('save', cookie, state=state, revision=body['revision'])
        self.assertEqual(response['statusCode'], 200)
        with patch.object(app, 'chat_answer') as external:
            response, answer = self.fixture.call('chat', cookie, question='Ребёнок подруги не дышит, что сейчас делать?', messageId='urgent-other-child', revision=saved['revision'])
        self.assertEqual(response['statusCode'], 200)
        self.assertIn('112', answer['answer'])
        self.assertNotIn('добавьте отдельный профиль', answer['answer'])
        external.assert_not_called()
        self.assertEqual(answer['quota']['used'], 0)

    def test_request_contains_new_prompt_and_chat_keeps_its_provider_mode(self):
        response = MagicMock()
        response.__enter__.return_value.read.return_value = json.dumps({'choices':[{'message':{'content':'Проверенный ответ'},'finish_reason':'stop'}], 'usage':{'prompt_tokens':10,'completion_tokens':5}}).encode()
        import os
        with patch.dict(os.environ, {'AI_PROVIDER':'proxyapi','PROXYAPI_API_KEY':'synthetic-key'}), patch.object(app, 'CHAT_LIVE_ENABLED', True), patch.object(app.urllib.request, 'urlopen', return_value=response) as opened:
            app.chat_answer('Как сделать вечер спокойнее?', 'Искусственный контекст')
        request = json.loads(opened.call_args.args[0].data)
        self.assertEqual(request['messages'][0]['content'], prompt_policy.CHAT_SYSTEM_PROMPT)
        self.assertNotIn('response_format', request)

    def test_social_question_keeps_active_child_and_real_other_profile_is_blocked(self):
        profile = {'stage':'child','birthDate':'2023-09-17','childName':'Тест'}
        self.assertIsNone(app._content.profile_scope_reply('Что говорить, когда ребёнок бьёт другого ребёнка?', profile))
        self.assertIsNotNone(app._content.profile_scope_reply('Другой ребёнок бьёт другого ребёнка. Что ему сказать?', profile))
        self.assertIsNotNone(app._content.profile_scope_reply('Ребёнок подруги бьёт другого ребёнка. Как ей помочь?', profile))

    def test_profile_notice_is_not_duplicated_and_useful_social_sentence_survives(self):
        profile = {'stage':'child','birthDate':'2023-09-17','childName':'Тест'}
        notice = app._content.profile_scope_reply('Что делать для другого ребёнка?', profile)
        self.assertEqual(app._content.clean(notice, profile), notice)
        useful = 'Если ребёнок ударил другого ребёнка, остановите удар и оставайтесь рядом.'
        self.assertEqual(app._content.clean(useful, profile), useful)

    def test_implicit_activity_requests_receive_an_age_bounded_catalog(self):
        profile = {'stage':'child','birthDate':'2023-09-17','childName':'Тест'}
        for question in ('Как занять ребёнка, пока я готовлю?', 'Как поддержать интерес к рисованию?'):
            self.assertIn('Каталог:', app._content.context(profile, question))

    def test_unknown_age_cannot_be_supplied_in_free_text(self):
        answer = app._safety.reply('Ребёнку 6 месяцев, какой размер кусочков дать?', None)
        self.assertIn('активном профиле', answer)
        self.assertNotIn('Сколько ему', answer)

    def test_nutrition_certainty_and_unproven_save_failure_are_removed(self):
        bad = 'Ребёнок получает достаточно, если ест хотя бы несколько привычных продуктов из разных групп.'
        self.assertNotIn('получает достаточно', app._safety.review(bad, {}))
        diary = 'В дневнике 30 минут. Изменения могли не сохраниться — проверьте запись.'
        reviewed = app._safety.review(diary, {})
        self.assertIn('30 минут', reviewed)
        self.assertNotIn('не сохраниться', reviewed)
        deleted=app._safety.review('Записей нет. Если записи были, возможно, они не сохранились или попали в другой профиль.',{})
        self.assertNotIn('не сохранились',deleted)
        self.assertIn('текущий дневник',deleted)

    def test_review_does_not_infer_parent_guilt_or_require_waiting_for_help(self):
        text = ('Ребёнок получает её в достатке. Лекция нужна вам, чтобы снять чувство вины. '
                'Если через месяц-полтора легче не становится, стоит обсудить это с педиатром или психологом.')
        reviewed = app._safety.review(text, {})
        self.assertNotIn('в достатке', reviewed)
        self.assertNotIn('чувство вины', reviewed)
        self.assertNotIn('через месяц', reviewed)
        self.assertIn('уже сейчас', reviewed)

    def test_unwanted_thought_is_not_used_to_certify_safety(self):
        text = ('Она пугает именно потому, что противоречит вашим настоящим чувствам. '
                'То, что мысль вызывает ужас, — характерный признак именно навязчивой мысли, а не опасного намерения. '
                'Если чувствуете риск действовать — звоните 112.')
        reviewed = app._safety.review(text, {})
        self.assertNotIn('характерный признак', reviewed)
        self.assertIn('оценить безопасность полностью нельзя', reviewed)
        self.assertIn('112', reviewed)

    def test_young_child_snack_includes_food_preparation_not_just_familiarity(self):
        answer=app._safety.review('Возьмите кусочки овощей: огурец, морковь. Сыр и варёное яйцо.', {'profile':{'stage':'child','birthDate':'2023-09-17'}})
        self.assertIn('до мягкости', answer)
        self.assertIn('не круглыми', answer)

    def test_unsolicited_offer_removed_but_specific_question_and_emergency_remain(self):
        text = 'Начните с одного шага. Если хотите, могу предложить ещё игру. Что у вас есть дома?'
        cleaned = app._content.clean(text)
        self.assertNotIn('могу предложить', cleaned)
        self.assertIn('Что у вас есть дома?', cleaned)
        self.assertIn('112', app._content.clean('Не ждите ответа чата — звоните 112.'))
        for offer in ('Если расскажете, как выглядит ваш день, предложу ещё идею.',
                      'Если напишете, какой навык вы имеете в виду, помогу точнее сформулировать наблюдение для врача.',
                      'Хотите, помогу сформулировать начало разговора под вашу ситуацию?',
                      'Если захотите, можно подумать об одном маленьком шаге для вас — но только если сами захотите.',
                      'Если ребёнку станет скучно, скажите — подберу другой вариант.',
                      'Если хотите, напишите ваш распорядок — помогу скорректировать его.'):
            self.assertEqual(app._content.clean('Один шаг уже описан. '+offer), 'Один шаг уже описан.')


if __name__ == '__main__':
    unittest.main()
