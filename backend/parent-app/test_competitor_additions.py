from datetime import datetime, timezone, timedelta
from unittest.mock import patch
from test_care_tools import CareToolsTest
from test_api import app

class CompetitorAdditionsTest(CareToolsTest):
    def record(self, kind='feeding', offset=2):
        now=datetime.now(timezone.utc)
        return {'kind':kind,'at':(now-timedelta(hours=offset)).isoformat(),'note':'synthetic'}

    def test_import_deduplicates_without_overwrite_and_is_atomic(self):
        cookie,_=self.setup_parent('import@example.test')
        listing=self.call('care-list',cookie)[1]
        item=self.record()
        result=self.call('care-import',cookie,contextVersion=listing['contextVersion'],records=[item,item])[1]
        self.assertEqual((result['added'],result['skipped']),(1,1))
        listing=self.call('care-list',cookie)[1];original=listing['records']
        self.assertEqual(self.call('care-import',cookie,contextVersion='stale',records=[self.record(offset=3)])[0]['statusCode'],409)
        self.assertEqual(self.call('care-import',cookie,contextVersion=listing['contextVersion'],records=[self.record(offset=3),{**self.record(),'kind':'mood'}])[0]['statusCode'],400)
        self.assertEqual(self.call('care-list',cookie)[1]['records'],original)
        duplicate=self.call('care-import',cookie,contextVersion=listing['contextVersion'],records=[item])[1]
        self.assertEqual((duplicate['added'],duplicate['skipped']),(0,1))
        offset={**item,'at':datetime.fromisoformat(item['at']).astimezone(timezone(timedelta(hours=3))).isoformat()}
        self.assertEqual(self.call('care-import',cookie,contextVersion=listing['contextVersion'],records=[offset])[1]['added'],0)

    def test_authorship_export_and_account_deletion(self):
        cookie,uid=self.setup_parent('author-export@example.test')
        self.call('care-put',cookie,record={**self.record(),'id':'feed'})
        export=self.call('data-export',cookie,password='long-test-password')[1]
        self.assertEqual(export['careAuthorship'][0]['recordId'],'feed')
        self.assertEqual(self.call('delete',cookie,password='long-test-password')[0]['statusCode'],200)
        db=app.DB()
        self.assertEqual(db.query('SELECT COUNT(*) FROM mh_care_authorship WHERE owner_id=?',(uid,)).fetchone()[0],0)
        db.close()

    def test_import_and_authorship_obey_family_privacy(self):
        owner,uid=self.setup_parent('author-owner@example.test');guest,_=self.setup_parent('author-guest@example.test')
        self.call('care-put',owner,record={**self.record(),'id':'feed'})
        invite=self.call('family-invite',owner,permission='write')[1];self.call('family-accept',guest,code=invite['code'])
        listing=self.call('care-list',guest,ownerId=uid)[1]
        self.assertEqual(self.call('care-import',guest,ownerId=uid,contextVersion=listing['contextVersion'],records=[self.record(offset=3)])[0]['statusCode'],403)
        self.call('care-put',guest,ownerId=uid,record={**listing['records'][0],'note':'corrected'})
        author=self.call('care-list',owner)[1]['authors']['feed']
        self.assertEqual(author['createdByRole'],'Владелец профиля')
        self.assertEqual(author['updatedByRole'],'Приглашённый взрослый')
        self.call('care-delete',owner,id='feed')
        self.assertEqual(self.call('care-list',owner)[1]['authors'],{})

    def test_answer_passport_is_snapshot_and_updates_after_delete(self):
        cookie,_=self.setup_parent('passport@example.test')
        self.call('care-put',cookie,record={**self.record(),'id':'feed'})
        def ask(ident):
            revision=self.call('session',cookie)[1]['revision']
            return self.call('chat',cookie,question='Что видно по записям кормлений?',messageId=ident,revision=revision)[1]['state']['messages'][-1]
        with patch.object(app,'chat_answer',return_value='По отметкам нельзя оценить достаточность питания.'):
            first=ask('first');self.assertIn('1 отметок',first['evidence']['basis'])
            self.call('care-delete',cookie,id='feed')
            second=ask('second');self.assertIn('0 отметок',second['evidence']['basis'])
            self.assertNotEqual(first['careVersion'],second['careVersion'])
            self.assertIn('1 отметок',self.call('session',cookie)[1]['state']['messages'][-3]['evidence']['basis'])
