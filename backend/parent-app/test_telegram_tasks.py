import json,sqlite3,tempfile,unittest
from pathlib import Path
from contextlib import closing
from unittest.mock import patch
import telegram_tasks as tasks
import telegram_admin as admin
import telegram_outbox as outbox

class TaskTest(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.root=Path(self.temp.name)
    def test_queue_dedup_and_status(self):
        with closing(outbox.database(self.root)) as db:
            tasks.submit(db,10,'Добавить кнопку');tasks.submit(db,10,'Добавить кнопку')
            self.assertEqual(db.execute('SELECT COUNT(*) FROM admin_tasks').fetchone()[0],1)
            self.assertIn('в очереди',tasks.status(db))
    def test_secret_and_backpressure(self):
        with closing(outbox.database(self.root)) as db:
            self.assertIn('секрет',tasks.submit(db,1,'123456789:'+('A'*35)))
            for i in range(5):tasks.submit(db,10+i,'Тест')
            self.assertIn('пять',tasks.submit(db,99,'Шестая задача'))
    def test_scope_and_concurrent_changes(self):
        app=self.root/'app';candidate=self.root/'candidate';artifact=self.root/'artifact'
        for folder in (app,candidate):
            (folder/'src').mkdir(parents=True);(folder/'src/a.ts').write_text('old')
        artifact.mkdir();base=tasks.sources(app);(candidate/'src/a.ts').write_text('new');after=tasks.sources(candidate)
        (app/'src/a.ts').write_text('concurrent')
        with self.assertRaisesRegex(ValueError,'working-source'):tasks.apply_checked(app,candidate,base,after,artifact)
        self.assertEqual((app/'src/a.ts').read_text(),'concurrent')
    def test_apply_and_rollback_copy(self):
        app=self.root/'app';candidate=self.root/'candidate';artifact=self.root/'artifact'
        for folder in (app,candidate):
            (folder/'src').mkdir(parents=True);(folder/'src/a.ts').write_text('old')
        artifact.mkdir();base=tasks.sources(app);(candidate/'src/a.ts').write_text('new')
        tasks.apply_checked(app,candidate,base,tasks.sources(candidate),artifact)
        self.assertEqual((app/'src/a.ts').read_text(),'new');self.assertEqual((artifact/'rollback/src/a.ts').read_text(),'old')
    def test_scope_restrictions(self):
        for name in ['../private/secret.py','backend/parent-app/telegram_tasks.py','backend/parent-app/local_server.py','package.json','deploy/go.py']:
            self.assertFalse(tasks.allowed_change(name),name)
    def test_owner_only_and_publish_disabled(self):
        cfg={'chatId':'123','enabledAt':1}
        def u(ident,who,text):return {'update_id':ident,'message':{'date':2000000000,'chat':{'id':who,'type':'private'},'from':{'id':who},'text':text}}
        admin.process(self.root,cfg,[u(1,99,'/task Чужая задача'),u(2,123,'/task Добавить график'),u(3,123,'/publish 1')])
        with closing(outbox.database(self.root)) as db:
            self.assertEqual(db.execute('SELECT COUNT(*) FROM admin_tasks').fetchone()[0],1)
            self.assertIn('не сохраняется',db.execute("SELECT body FROM messages WHERE id='admin:3'").fetchone()[0])
    def test_clean_environment_does_not_inherit_app_secrets(self):
        with patch.dict(tasks.os.environ,{'APP_KEY':'secret','MAMA_AUTOMATION_TOKEN':'secret','OPENAI_API_KEY':'secret','CODEX_APP_TOOLS_PIPE_PATH':'pipe'}):
            env=tasks.clean_env()
        self.assertFalse(any(k.startswith(('APP_','MAMA_','CODEX_','OPENAI_')) for k in env))

if __name__=='__main__':unittest.main()
