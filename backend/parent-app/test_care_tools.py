from test_api import AccountsTest,app
from datetime import datetime,timezone,date,timedelta

class CareToolsTest(AccountsTest):
    def test_milestone_allowlist_deduplication_and_undo(self):
        from care_tools import MILESTONE_LABELS
        cookie,_=self.setup_parent('marks@example.test')
        for skill,label in MILESTONE_LABELS.items():
            with self.subTest(skill=skill):
                record={'id':'mark-'+skill,'kind':'achievement','skill':skill,'at':datetime.now(timezone.utc).isoformat(),'value':'ignored'}
                response,body=self.call('care-put',cookie,record=record)
                self.assertEqual(response['statusCode'],200)
                self.assertEqual(body['record']['value'],label)
                response,repeat=self.call('care-put',cookie,record={**record,'id':'retry-'+skill})
                self.assertEqual(response['statusCode'],200)
                self.assertTrue(repeat['alreadyMarked'])
                self.assertEqual(repeat['record']['id'],record['id'])
                self.assertEqual(self.call('care-delete',cookie,id=record['id'])[0]['statusCode'],200)
        self.assertEqual(self.call('care-list',cookie)[1]['records'],[])

    def test_milestone_rejects_unknown_skill_foreign_child_and_future(self):
        cookie,_=self.setup_parent('invalid-mark@example.test')
        other,other_uid=self.setup_parent('other-mark@example.test')
        record={'id':'mark','kind':'achievement','skill':'roll','at':datetime.now(timezone.utc).isoformat()}
        for skill in ('sit','unknown','__proto__',None,[],{}):
            self.assertEqual(self.call('care-put',cookie,record={**record,'skill':skill})[0]['statusCode'],400)
        self.assertEqual(self.call('care-put',cookie,childId='not-my-child',record=record)[0]['statusCode'],404)
        self.assertEqual(self.call('care-put',cookie,ownerId=other_uid,record=record)[0]['statusCode'],403)
        self.assertEqual(self.call('care-put',cookie,record={**record,'at':(datetime.now(timezone.utc)+timedelta(days=1)).isoformat()})[0]['statusCode'],400)
        self.assertEqual(self.call('care-list',cookie)[1]['records'],[])
        self.assertEqual(self.call('care-list',other)[1]['records'],[])

    def test_milestone_existing_manual_value_is_not_duplicated(self):
        cookie,_=self.setup_parent('manual-mark@example.test')
        record={'id':'manual','kind':'achievement','value':'Ползает','at':datetime.now(timezone.utc).isoformat()}
        self.call('care-put',cookie,record=record)
        response,body=self.call('care-put',cookie,record={**record,'id':'new','skill':'crawl'})
        self.assertEqual(response['statusCode'],200)
        self.assertTrue(body['alreadyMarked'])
        self.assertEqual(body['record']['id'],'manual')
        self.assertEqual(len(self.call('care-list',cookie)[1]['records']),1)

    def test_milestone_legacy_card_is_not_duplicated(self):
        cookie,_=self.setup_parent('legacy-mark@example.test')
        session=self.call('session',cookie)[1]
        state=session['state']
        state.setdefault('care',{})['achievements']=[{'id':'legacy','kind':'roll','date':date.today().isoformat(),'note':'Переворачивается'}]
        self.assertEqual(self.call('save',cookie,state=state,revision=session['revision'])[0]['statusCode'],200)
        record={'id':'new','kind':'achievement','skill':'roll','at':datetime.now(timezone.utc).isoformat()}
        response,body=self.call('care-put',cookie,record=record)
        self.assertEqual(response['statusCode'],200)
        self.assertTrue(body['alreadyMarked'])
        self.assertTrue(body['record']['legacy'])
        self.assertEqual(self.call('care-list',cookie)[1]['records'],[])

    def test_edit_feeding_time_preserves_record_identity_notes_and_dialogue(self):
        cookie,_=self.setup_parent('edit-feed@example.test')
        now=datetime.now(timezone.utc)
        record={'id':'feed-edit','kind':'feeding','at':(now-timedelta(hours=2)).isoformat(),'end':(now-timedelta(hours=1)).isoformat(),'side':'left','value':'ГВ','note':'Preserve note'}
        self.assertEqual(self.call('care-put',cookie,record=record)[0]['statusCode'],200)
        edited={**record,'at':(now-timedelta(hours=3)).isoformat(),'end':(now-timedelta(hours=2)).isoformat()}
        self.assertEqual(self.call('care-put',cookie,record=edited)[0]['statusCode'],200)
        self.assertEqual(self.call('care-list',cookie)[1]['records'],[edited])
        self.assertEqual(self.call('care-put',cookie,record={**edited,'kind':'food'})[0]['statusCode'],409)
        self.assertEqual(self.call('care-put',cookie,record={**edited,'end':(now-timedelta(hours=4)).isoformat()})[0]['statusCode'],400)
        self.assertEqual(self.call('care-list',cookie)[1]['records'],[edited])
        self.assertEqual(self.call('care-delete',cookie,id=record['id'])[0]['statusCode'],200)
        self.assertEqual(self.call('care-delete',cookie,id=record['id'])[0]['statusCode'],200)
        self.assertEqual(self.call('care-list',cookie)[1]['records'],[])
        self.assertEqual(self.call('session',cookie)[1]['state']['messages'][0]['text'],'private dialogue')

    def test_feeding_edit_and_delete_keep_family_permissions(self):
        owner,uid=self.setup_parent('edit-owner@example.test')
        guest,_=self.setup_parent('edit-reader@example.test')
        now=datetime.now(timezone.utc)
        record={'id':'private-feed','kind':'feeding','at':(now-timedelta(hours=2)).isoformat(),'note':'Private'}
        self.assertEqual(self.call('care-put',owner,record=record)[0]['statusCode'],200)
        edited={**record,'at':(now-timedelta(hours=3)).isoformat()}
        self.assertEqual(self.call('care-put',guest,ownerId=uid,record=edited)[0]['statusCode'],403)
        invite=self.call('family-invite',owner,permission='read')[1]
        self.call('family-accept',guest,code=invite['code'])
        self.assertEqual(self.call('care-put',guest,ownerId=uid,record=edited)[0]['statusCode'],403)
        self.assertEqual(self.call('care-delete',guest,ownerId=uid,id=record['id'])[0]['statusCode'],403)
        self.call('family-revoke',owner,id=invite['id'])
        invite=self.call('family-invite',owner,permission='write')[1]
        self.call('family-accept',guest,code=invite['code'])
        self.assertEqual(self.call('care-put',guest,ownerId=uid,record=edited)[0]['statusCode'],200)
        self.assertEqual(self.call('care-delete',guest,ownerId=uid,id=record['id'])[0]['statusCode'],403)
        self.assertEqual(self.call('care-list',owner)[1]['records'],[edited])

    def test_full_summary_survives_raw_chat_context_limit_and_preserves_diary(self):
        cookie, uid = self.setup_parent('summary-context@example.test')
        now = datetime.now(timezone.utc)
        db = app.DB()
        for number in range(100):
            record = {'id':'feed-'+str(number),'kind':'feeding','at':(now-timedelta(minutes=number)).isoformat(),'value':'ГВ','note':''}
            db.query('INSERT INTO mh_care_records VALUES(?,?,?,?)',(uid,'primary',record['id'],app.seal(record)))
        sleep = {'id':'sleep-old','kind':'sleep','at':(now-timedelta(hours=4)).isoformat(),'end':(now-timedelta(hours=3)).isoformat(),'note':''}
        db.query('INSERT INTO mh_care_records VALUES(?,?,?,?)',(uid,'primary',sleep['id'],app.seal(sleep)))
        db.conn.commit();db.close()
        listing = self.call('care-list',cookie)[1]
        self.assertEqual(listing['summary']['feeding']['records'],100)
        captured=[];previous=app.chat_answer
        def fake(question,context,*args,**kwargs):
            captured.append(context);return 'По неполным записям режим оценить нельзя.'
        app.chat_answer=fake
        try:
            revision=self.call('session',cookie)[1]['revision']
            result, body=self.call('chat',cookie,question='Помоги разобраться с дневником',messageId='summary-question',revision=revision)
            self.assertEqual(result['statusCode'],200,body)
            self.assertIn('"rawRecordsTruncated": true',captured[0])
            self.assertIn('"records": 100',captured[0])
            self.assertEqual(body['sleepContext']['records'],1)
            self.assertEqual(len(self.call('care-list',cookie)[1]['records']),101)
            self.assertEqual(body['state']['messages'][0]['text'],'private dialogue')
        finally:app.chat_answer=previous

    def test_feeding_timer_persists_and_rejects_duplicate(self):
        cookie,_=self.setup_parent('feeding-timer@example.test')
        record={'id':'timer','kind':'feeding','at':datetime.now(timezone.utc).isoformat(),'value':'Таймер кормления','side':'left','note':''}
        self.assertEqual(self.call('care-put',cookie,record=record)[0]['statusCode'],200)
        self.assertEqual(self.call('care-put',cookie,record={**record,'id':'duplicate'})[0]['statusCode'],409)
        records=self.call('care-list',cookie)[1]['records']
        self.assertEqual(records[0],record)
        self.assertEqual(self.call('care-put',cookie,record={**record,'end':datetime.now(timezone.utc).isoformat()})[0]['statusCode'],200)
        self.assertEqual(self.call('care-put',cookie,record={**record,'id':'next'})[0]['statusCode'],200)
    def test_chat_receives_recent_active_child_records_only(self):
        cookie,uid=self.setup_parent('context@example.test')
        now=datetime.now(timezone.utc)
        for ident,kind,at,value in [('fresh','feeding',now,'FRESH_ACTIVE'),('old','feeding',now-timedelta(days=8),'OLD_RECORD'),('mood','mood',now,'PRIVATE_MOOD')]:
            self.assertEqual(self.call('care-put',cookie,record={'id':ident,'kind':kind,'at':at.isoformat(),'value':value,'note':''})[0]['statusCode'],200)
        db=app.DB()
        db.query('INSERT INTO mh_care_records VALUES(?,?,?,?)',(uid,'second','other',app.seal({'id':'other','kind':'feeding','at':now.isoformat(),'value':'OTHER_CHILD'})))
        db.conn.commit();db.close()
        captured=[];previous=app.chat_answer
        def fake(question,context,*args,**kwargs):
            captured.append(context);return 'Данных мало, пока нельзя сделать вывод о режиме.'
        app.chat_answer=fake
        try:
            revision=self.call('session',cookie)[1]['revision']
            self.assertEqual(self.call('chat',cookie,question='Что видно по кормлениям?',messageId='context-question',revision=revision)[0]['statusCode'],200)
            self.assertIn('FRESH_ACTIVE',captured[0])
            for forbidden in ('OLD_RECORD','PRIVATE_MOOD','OTHER_CHILD'):self.assertNotIn(forbidden,captured[0])
        finally:app.chat_answer=previous
    def setup_parent(self,email):
        c,b=self.register(email)
        s=b['state'];s['profile']={'role':'mom','stage':'child','birthDate':date.today().isoformat(),'week':20,'weekDate':date.today().isoformat(),'feeding':'unknown','sleep':'','health':'','healthConfirmed':False,'topics':[]}
        s['messages']=[{'id':'private','role':'user','text':'private dialogue'}]
        self.assertEqual(self.call('save',c,state=s,revision=0)[0]['statusCode'],200)
        return c,b['user']['id']

    def test_family_privacy_revocation_and_permissions(self):
        mom,uid=self.setup_parent('owner@example.test');guest,_=self.setup_parent('guest@example.test');other,_=self.setup_parent('other@example.test')
        at=datetime.now(timezone.utc).isoformat()
        for kind in ('mood','achievement'):
            self.assertEqual(self.call('care-put',mom,record={'id':kind,'kind':kind,'at':at,'note':'test'})[0]['statusCode'],200)
        invite=self.call('family-invite',mom,permission='read')[1]
        self.assertEqual(self.call('family-accept',guest,code=invite['code'])[0]['statusCode'],200)
        self.assertEqual(self.call('family-accept',other,code=invite['code'])[0]['statusCode'],400)
        r,b=self.call('care-list',guest,ownerId=uid)
        self.assertEqual(r['statusCode'],200);self.assertEqual([x['kind'] for x in b['records']],['achievement'])
        self.assertNotIn('messages',b);self.assertNotIn('health',b['profile'])
        self.assertEqual(self.call('care-list',other,ownerId=uid)[0]['statusCode'],403)
        self.assertEqual(self.call('care-put',guest,ownerId=uid,record={'id':'x','kind':'food','at':at,'note':'test'})[0]['statusCode'],403)
        self.call('family-revoke',mom,id=invite['id'])
        self.assertEqual(self.call('care-list',guest,ownerId=uid)[0]['statusCode'],403)

    def test_sleep_preservation_and_write_access(self):
        mom,uid=self.setup_parent('sleep@example.test');guest,_=self.setup_parent('writer@example.test')
        at=datetime.now(timezone.utc).isoformat();r={'id':'sleep','kind':'sleep','at':at,'note':''}
        self.assertEqual(self.call('care-put',mom,record=r)[0]['statusCode'],200)
        self.assertEqual(self.call('care-put',mom,record={**r,'id':'second'})[0]['statusCode'],409)
        invite=self.call('family-invite',mom,permission='write')[1];self.call('family-accept',guest,code=invite['code'])
        self.assertEqual(self.call('care-put',guest,ownerId=uid,record={**r,'end':datetime.now(timezone.utc).isoformat()})[0]['statusCode'],200)
        self.assertEqual(self.call('care-put',guest,ownerId=uid,record={**r,'id':'m','kind':'mood'})[0]['statusCode'],403)
        self.assertEqual(self.call('session',mom)[1]['state']['messages'][0]['text'],'private dialogue')
        self.assertEqual(self.call('care-list',mom,childId='unknown')[0]['statusCode'],404)
