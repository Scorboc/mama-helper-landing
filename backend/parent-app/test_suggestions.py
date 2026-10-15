import importlib.util
import json
import sqlite3
import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace
from zoneinfo import ZoneInfo

ROOT=Path(__file__).parent
spec=importlib.util.spec_from_file_location('suggestions',ROOT/'suggestions.py')
suggestions=importlib.util.module_from_spec(spec);spec.loader.exec_module(suggestions)

class AppError(Exception):
    def __init__(self,status,message):self.status=status;self.message=message

class DB:
    def __init__(self,path):self.conn=sqlite3.connect(path)
    def query(self,sql,params=()):return self.conn.execute(sql,params)

class Ops:
    def __init__(self):self.tasks=[]
    def document(self,kind,body):self.tasks.append((kind,body));return body

class SuggestionTest(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.NamedTemporaryFile(delete=False);self.tmp.close();self.db=DB(self.tmp.name)
        for statement in (ROOT/'schema.sql').read_text(encoding='utf-8').split(';'):
            if statement.strip():self.db.query(statement)
        for uid in ('u1','u2'):
            self.db.query('INSERT INTO mh_users VALUES(?,?,?,?,?,?)',(uid,uid+'@x.test','p','r',1,'v'))
        self.ops=Ops();self.clock=[datetime(2026,10,5,12,tzinfo=ZoneInfo('Europe/Moscow'))]
        self.runtime=SimpleNamespace(AppError=AppError,seal=lambda x:json.dumps(x,ensure_ascii=False),unseal=json.loads,ops=self.ops,now=lambda:self.clock[0])

    def tearDown(self):self.db.conn.close();Path(self.tmp.name).unlink(missing_ok=True)

    def call(self,uid,action,**data):return suggestions.action(self.runtime,self.db,uid,{'action':action,**data})

    def test_collect_vote_finalize_and_privacy(self):
        with self.assertRaises(AppError):self.call('u1','suggestion-create',title='Позвоните +79991234567',detail='')
        first=self.call('u1','suggestion-create',title='Сравнение сна за две недели',detail='Показать изменения на графике')
        self.assertEqual('collecting',first['phase']);self.assertEqual([],first['items'])
        self.call('u2','suggestion-create',title='Удобный экспорт дневника сна',detail='Сохранение отчёта')
        self.clock[0]=datetime(2026,10,9,12,tzinfo=ZoneInfo('Europe/Moscow'))
        for item in suggestions.moderation_queue(self.runtime,self.db):
            suggestions.review(self.runtime,self.db,dict(id=item['id'],title=item['title'],detail=item['detail'],reviewed=True))
        ballot=self.call('u1','suggestion-list')
        self.assertEqual(2,len(ballot['items']))
        chosen=ballot['items'][0]['id']
        self.call('u1','suggestion-vote',suggestionId=chosen)
        changed=self.call('u2','suggestion-vote',suggestionId=chosen)
        self.assertEqual(2,next(x for x in changed['items'] if x['id']==chosen)['votes'])
        self.clock[0]=datetime(2026,10,12,12,tzinfo=ZoneInfo('Europe/Moscow'))
        result=self.call('u1','suggestion-list')
        self.assertEqual(1,result['newWinnerCount']);self.assertEqual(chosen,result['winners'][0]['id'])
        self.assertEqual('task',self.ops.tasks[0][0])

    def test_unreviewed_health_story_never_reaches_ballot_or_winners(self):
        story='Моя дочь Анна родилась 14 мая, у неё астма, принимаем лекарство.'
        self.call('u1','suggestion-create',title='Добавить напоминание о приёмах',detail=story)
        record=suggestions.moderation_queue(self.runtime,self.db)[0]
        self.assertEqual(record['detail'],story)
        self.clock[0]=datetime(2026,10,9,12,tzinfo=ZoneInfo('Europe/Moscow'))
        self.assertEqual(self.call('u2','suggestion-list')['items'],[])
        with self.assertRaises(AppError):self.call('u2','suggestion-vote',suggestionId=record['id'])
        suggestions.review(self.runtime,self.db,dict(id=record['id'],title='Добавить напоминание о встречах',detail='Удобное напоминание',reviewed=True))
        public=self.call('u2','suggestion-list')['items'][0]
        self.assertNotIn('Анна',str(public)); self.assertNotIn('астма',str(public))
        self.assertEqual(suggestions.moderation_queue(self.runtime,self.db)[0]['detail'],story)

    def test_existing_planned_winner_can_get_a_safe_public_version(self):
        self.call('u1','suggestion-create',title='Удобный график для дневника',detail='Искусственный частный текст')
        record=suggestions.moderation_queue(self.runtime,self.db)[0]
        self.db.query("UPDATE mh_product_suggestions SET status='planned' WHERE id=?",(record['id'],))
        suggestions.review(self.runtime,self.db,dict(id=record['id'],title='Удобный график для дневника',detail='Без личных сведений',reviewed=True))
        row=self.db.query('SELECT encrypted_data,status FROM mh_product_suggestions WHERE id=?',(record['id'],)).fetchone()
        self.assertEqual(row[1],'planned')
        self.assertEqual(json.loads(row[0])['detail'],'Искусственный частный текст')
        self.assertEqual(suggestions._public(dict(json.loads(row[0]),id=record['id']))['detail'],'Без личных сведений')

if __name__=='__main__':unittest.main()
