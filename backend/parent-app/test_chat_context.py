"""Concrete regression: a valid long account must not exceed the provider cap."""
import copy,json,unittest
from datetime import date,datetime,timezone
from types import SimpleNamespace
from unittest.mock import patch
from test_api import app

class ChatContextTest(unittest.TestCase):
    def fixture(self,long=False):
        state=app.blank_state()
        state['profile']={'role':'mom','stage':'child','birthDate':'2025-08-13','childName':'Тест',
                          'feeding':'unknown','sleep':'С'*300,'health':'З'*500,'healthConfirmed':True,'topics':[]}
        if long:
            state['messages']=[{'role':'user' if n%2==0 else 'assistant','text':'Обсуждали наблюдения. '*40} for n in range(30)]
            state['medicalCard']=[{'id':str(n),'date':date.today().isoformat(),'text':'Наблюдение. '*40+str(n),'source':'manual','confirmation':'parent'} for n in range(12)]
            state['medicalCard'][0].update(date='2020-01-01',text='Аллергия на молоко, нельзя повторно пробовать без плана врача.')
        rows=[{'id':str(n),'kind':'feeding','at':datetime.now(timezone.utc).isoformat(),'data':{'method':'breast','note':'Наблюдение. '*30}} for n in range(100 if long else 2)]
        return state,rows

    def compose(self,state,rows,question='Что показывает дневник?'):
        stats=app.care_summary.summary(rows)
        with patch.object(app.ai_budget,'config',return_value=(100000000,100000000,65536,4)):
            return app.chat_context.compose(SimpleNamespace(**vars(app)),state,question,None,'',rows,stats)

    def test_small_context_preserves_raw_records_and_totals(self):
        state,rows=self.fixture();context,meta=self.compose(state,rows)
        self.assertEqual(meta['rawRecordsIncluded'],2)
        self.assertFalse(meta['rawRecordsTruncated'])
        self.assertFalse(meta['medicalNotesContextReduced'])
        self.assertIn('recordedSleepMinutesTotal',context)

    def test_large_context_keeps_current_totals_and_does_not_mutate_storage(self):
        state,rows=self.fixture(True);before=copy.deepcopy(state)
        question='Предложи игру без игрушек, учитывая развитие и уход. '+('Контекст ситуации. '*100)
        context,meta=self.compose(state,rows,question)
        self.assertLessEqual(app.chat_context.size(app,question,context),65536)
        self.assertTrue(meta['rawRecordsTruncated'])
        self.assertIn('Контекст сокращён',context)
        self.assertIn('Аллергия на молоко',context)
        self.assertEqual(state,before)
        summary=json.loads(context.split('Рассчитанная сводка сна и кормлений: ',1)[1])
        self.assertEqual(summary['records'],100)
        self.assertEqual(summary['feeding']['records'],100)
        self.assertEqual(summary['rawRecordsIncluded'],meta['rawRecordsIncluded'])

    def test_compact_daily_keeps_rejection_and_omits_unnecessary_steps(self):
        source={'today':{'items':[{'id':'copy-action@m14','title':'Повтор','steps':['x'*1000]}]},
                'feedback':[{'itemId':'copy-action@m14','reason':'dislike','detail':'Надоела механика.'}]}
        text=app.chat_context.compact_daily('\nПодборка:\n'+json.dumps(source,ensure_ascii=False))
        self.assertIn('Надоела механика',text)
        self.assertIn('copy-action@m14',text)
        self.assertNotIn('x'*1000,text)

    def test_missing_room_keeps_hard_cap_and_refuses_without_mutating(self):
        state,rows=self.fixture();before=copy.deepcopy(state)
        with patch.object(app.ai_budget,'config',return_value=(100000000,100000000,1024,4)):
            with self.assertRaises(app.AppError):
                app.chat_context.compose(SimpleNamespace(**vars(app)),state,'Что делать?',None,'',rows,app.care_summary.summary(rows))
        self.assertEqual(state,before)

if __name__=='__main__':unittest.main()
