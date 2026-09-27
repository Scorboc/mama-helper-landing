import importlib.util
import json
import os
from pathlib import Path
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location('proxy_test_app', Path(__file__).with_name('index.py'))
app = importlib.util.module_from_spec(spec)
spec.loader.exec_module(app)


class ProxyTests(unittest.TestCase):
    def call(self, daily=False, content='Ответ', finish='stop'):
        response = unittest.mock.MagicMock()
        response.__enter__.return_value.read.return_value = json.dumps({
            'choices': [{'message': {'content': content}, 'finish_reason': finish}],
            'usage': {'prompt_tokens': 12, 'completion_tokens': 4},
        }).encode()
        with patch.dict(os.environ, {'AI_PROVIDER':'proxyapi','PROXYAPI_API_KEY':'test-only',
                                     'YANDEX_API_KEY':'old-test-only','YANDEX_FOLDER_ID':'old-folder'}, clear=True), \
             patch.object(app, 'CHAT_LIVE_ENABLED', True), \
             patch.object(app, 'with_chat_deadline', side_effect=lambda fn:fn()), \
             patch.object(app.urllib.request, 'urlopen', return_value=response) as opened:
            answer = app.chat_answer('Тест', 'Вымышленный профиль', system_prompt='Занятия' if daily else None)
            req = opened.call_args.args[0]
            self.assertEqual(req.full_url, 'https://api.proxyapi.ru/v1/chat/completions')
            self.assertNotIn('Openai-project', req.headers)
            self.assertEqual(req.headers['Authorization'], 'Bearer test-only')
            return json.loads(req.data)['model'], answer

    def test_chat_uses_glm_even_with_old_yandex_credentials(self):
        self.assertEqual(self.call()[0], 'z-ai/glm-5.3-flash')

    def test_daily_uses_verified_glm(self):
        self.assertEqual(self.call(daily=True)[0], 'z-ai/glm-5.3-flash')

    def test_no_fallback_when_proxy_key_missing(self):
        with patch.dict(os.environ, {'AI_PROVIDER':'proxyapi','YANDEX_API_KEY':'old'}, clear=True), \
             patch.object(app,'CHAT_LIVE_ENABLED',True), patch.object(app.urllib.request,'urlopen') as opened:
            with self.assertRaises(app.AppError): app.chat_answer('Тест','Контекст')
            opened.assert_not_called()

    def test_empty_or_truncated_answer_is_rejected(self):
        for content, finish in [('', 'stop'), ('Незакончено', 'length')]:
            with self.assertRaises(ValueError): self.call(content=content,finish=finish)


if __name__ == '__main__': unittest.main()
