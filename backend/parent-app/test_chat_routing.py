"""Regression checks for the optional local two-tier chat route."""
import json
import os
import unittest
from unittest.mock import MagicMock, patch

import chat_routing
from test_api import app


class RoutingTests(unittest.TestCase):
    def test_common_and_sensitive_questions(self):
        ordinary, strong = 'openai/gpt-6-luna', 'openai/gpt-6.1-sol'
        self.assertEqual(chat_routing.choose('Во что поиграть сегодня?', [], ordinary, strong), ordinary)
        self.assertEqual(chat_routing.choose('Можно ли дать лекарство при температуре?', [], ordinary, strong), strong)
        self.assertEqual(chat_routing.choose('Как организовать безопасный сон без подушки?', [], ordinary, strong), strong)
        self.assertEqual(chat_routing.choose('Восемь месяцев: ребёнок давится кусочками. Как безопасно подбирать текстуру еды?', [], ordinary, strong), strong)
        self.assertEqual(chat_routing.choose('Меня пугают навязчивые мысли о вреде ребёнку.', [], ordinary, strong), strong)
        self.assertEqual(chat_routing.choose('А если она всё ещё горячая?',
            [{'role':'user','text':'У ребёнка температура и он плохо ест.'}], ordinary, strong), strong)
        self.assertEqual(chat_routing.choose('А где график?',
            [{'role':'user','text':'Как добавить отметку сна?'}], ordinary, strong), ordinary)

    def test_proxy_payload_and_daily_model(self):
        response = MagicMock()
        response.__enter__.return_value.read.return_value = json.dumps({
            'choices':[{'message':{'content':'Проверенный тестовый ответ'},'finish_reason':'stop'}],
            'usage':{'prompt_tokens':100,'completion_tokens':30}}).encode()
        env = {'AI_PROVIDER':'proxyapi','PROXYAPI_API_KEY':'synthetic',
               'PROXYAPI_CHAT_MODEL':'openai/gpt-6-luna',
               'PROXYAPI_COMPLEX_MODEL':'openai/gpt-6.1-sol',
               'PROXYAPI_DAILY_MODEL':'z-ai/glm-5.3-flash',
               'APP_CHAT_TIERED_ENABLED':'1'}
        with patch.dict(os.environ,env,clear=True),patch.object(app,'CHAT_LIVE_ENABLED',True),\
             patch.object(app,'with_chat_deadline',side_effect=lambda fn:fn()),\
             patch.object(app.ai_budget,'reserve',return_value='test'),\
             patch.object(app.ai_budget,'finish'),patch.object(app.ops,'ai_call'),\
             patch.object(app.urllib.request,'urlopen',return_value=response) as opened:
            app.chat_answer('Можно ли дать лекарство при температуре?', 'Синтетический контекст')
            body=json.loads(opened.call_args.args[0].data)
            self.assertEqual(body['model'],'openai/gpt-6.1-sol')
            self.assertEqual(body['reasoning_effort'],'medium')
            self.assertIn('max_completion_tokens',body)
            self.assertNotIn('temperature',body)
            app.chat_answer('Во что поиграть?', 'Синтетический контекст')
            self.assertEqual(json.loads(opened.call_args.args[0].data)['model'],'openai/gpt-6-luna')
            app.chat_answer('Подбери игру', '{}',system_prompt='Только ID каталога')
            self.assertEqual(json.loads(opened.call_args.args[0].data)['model'],'z-ai/glm-5.3-flash')


if __name__=='__main__':
    unittest.main()
