import unittest,time,json,sqlite3
from contextlib import closing
from test_telegram_outbox import TelegramTest
import telegram_admin as admin
import telegram_outbox as outbox

class AdminTest(TelegramTest):
    def update(self,ident,text,owner=True):
        who=int(self.cfg['chatId']) if owner else 99
        return {'update_id':ident,'message':{'date':int(time.time()),'chat':{'id':who,'type':'private'},'from':{'id':who,'is_bot':False},'text':text}}
    def bodies(self):
        with closing(outbox.database(self.root)) as db:return [r[0] for r in db.execute("SELECT body FROM messages WHERE kind='admin'")]
    def test_owner_prompt_and_duplicate(self):
        u=self.update(1,'/prompt Добавить кнопку графика')
        self.assertEqual(admin.process(self.root,self.cfg,[u]),1)
        self.assertEqual(admin.process(self.root,self.cfg,[u]),0)
        self.assertIn('Добавить кнопку графика',self.bodies()[0]);self.assertIn('Сохрани',self.bodies()[0])
    def test_unknown_sender_ignored(self):
        admin.process(self.root,self.cfg,[self.update(1,'/prompt Вредная команда',False)])
        self.assertEqual(self.bodies(),[])
    def test_two_message_prompt_and_cancel(self):
        admin.process(self.root,self.cfg,[self.update(1,'/prompt'),self.update(2,'Упростить трекер')])
        self.assertIn('Упростить трекер',self.bodies()[-1])
        admin.process(self.root,self.cfg,[self.update(3,'/prompt'),self.update(4,'/cancel'),self.update(5,'Не задание')])
        self.assertEqual(len(self.bodies()),4)
    def test_runs_no_private_text_and_dedup(self):
        with closing(sqlite3.connect(self.root/'automation-journal.sqlite')) as db:
            db.execute('CREATE TABLE runs(k TEXT,job TEXT,state TEXT,result TEXT,at INTEGER)')
            db.executemany('INSERT INTO runs VALUES(?,?,?,?,?)',[('1','backup','success','{"ok":true,"secret":"PRIVATE"}',100),('2','ai-tests','failed','{"ok":false,"text":"PRIVATE"}',101)]);db.commit()
        outbox.collect_runs(self.root,1);outbox.collect_runs(self.root,1)
        with closing(outbox.database(self.root)) as db:rows=db.execute('SELECT body FROM messages').fetchall()
        self.assertEqual(len(rows),2);self.assertNotIn('PRIVATE',str([r[0] for r in rows]))
    def test_failed_handler_and_sender_are_caught_from_metadata(self):
        folder=self.root/'state/.n8n';folder.mkdir(parents=True)
        with closing(sqlite3.connect(folder/'database.sqlite')) as db:
            db.execute('CREATE TABLE workflow_entity(id TEXT,active INTEGER)')
            db.execute('CREATE TABLE execution_entity(id INTEGER,workflowId TEXT,startedAt TEXT,status TEXT)')
            for i in (7,18):
                ident='mamaLocal'+str(i).zfill(2)
                db.execute('INSERT INTO workflow_entity VALUES(?,1)',(ident,))
                db.execute("INSERT INTO execution_entity VALUES(?,?,'2026-10-17 12:00:00','error')",(i,ident))
            db.commit()
        outbox.collect(self.root);outbox.collect(self.root)
        with closing(outbox.database(self.root)) as db:rows=db.execute("SELECT body FROM messages WHERE kind='error'").fetchall()
        self.assertEqual(len(rows),2)

if __name__=='__main__':unittest.main()
