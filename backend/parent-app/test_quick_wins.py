from test_care_tools import CareToolsTest

class QuickWinsTest(CareToolsTest):
    def test_questions_limits_deduplication_edit_delete_and_isolation(self):
        cookie,uid=self.setup_parent('questions@example.test')
        other,_=self.setup_parent('other-questions@example.test')
        put=lambda ident,text:self.call('doctor-question-put',cookie,id=ident,text=text)
        self.assertEqual(put('q1','  О сне?  ')[0]['statusCode'],200)
        self.assertTrue(put('q2','о   сне?')[1]['duplicate'])
        listing=self.call('care-list',cookie)[1]
        self.assertEqual(listing['records'],[])
        from test_api import app
        from care_tools import observations, current_version, version
        db=app.DB()
        try:
            self.assertEqual(observations(app,db,uid,'primary'),[])
            self.assertEqual(current_version(app,db,uid,'primary'),version([]))
        finally:
            db.close()
        self.assertEqual(len(listing['doctorQuestions']),1)
        self.assertEqual(listing['doctorQuestions'][0]['note'],'О сне?')
        for value in ('','a'*501,[],None):self.assertEqual(put('bad',value)[0]['statusCode'],400)
        self.assertEqual(put('q1','a'*500)[0]['statusCode'],200)
        for i in range(2,31):self.assertEqual(put('q'+str(i),'Question '+str(i))[0]['statusCode'],200)
        self.assertEqual(put('q31','Over limit')[0]['statusCode'],400)
        self.assertEqual(put('q1','Edited')[0]['statusCode'],200)
        self.assertEqual(self.call('care-list',other)[1]['doctorQuestions'],[])
        self.assertEqual(self.call('care-list',cookie,childId='missing')[0]['statusCode'],404)
        self.assertEqual(self.call('doctor-question-delete',cookie,id='q1')[0]['statusCode'],200)
        self.assertEqual(put('q31','Now fits')[0]['statusCode'],200)

    def test_question_family_read_write_owner_and_collision(self):
        owner,uid=self.setup_parent('question-owner@example.test')
        guest,_=self.setup_parent('question-guest@example.test')
        self.call('doctor-question-put',owner,id='q',text='Question')
        self.assertEqual(self.call('doctor-question-put',guest,ownerId=uid,id='x',text='x')[0]['statusCode'],403)
        invite=self.call('family-invite',owner,permission='read')[1]
        self.call('family-accept',guest,code=invite['code'])
        self.assertEqual(len(self.call('care-list',guest,ownerId=uid)[1]['doctorQuestions']),1)
        self.assertEqual(self.call('doctor-question-put',guest,ownerId=uid,id='q',text='Edit')[0]['statusCode'],403)
        self.call('family-revoke',owner,id=invite['id'])
        invite=self.call('family-invite',owner,permission='write')[1]
        self.call('family-accept',guest,code=invite['code'])
        self.assertEqual(self.call('doctor-question-put',guest,ownerId=uid,id='q',text='Edit')[0]['statusCode'],200)
        self.assertEqual(self.call('doctor-question-delete',guest,ownerId=uid,id='q')[0]['statusCode'],403)
        from datetime import datetime,timezone
        record={'id':'care','kind':'feeding','at':datetime.now(timezone.utc).isoformat()}
        self.call('care-put',owner,record=record)
        self.assertEqual(self.call('doctor-question-put',owner,id='care',text='Collision')[0]['statusCode'],409)
        self.call('doctor-question-delete',owner,id='care')
        self.assertEqual(len(self.call('care-list',owner)[1]['records']),1)

    def test_writer_undo_is_limited_to_own_unedited_question_and_token(self):
        owner,uid=self.setup_parent('undo-owner@example.test')
        guest,_=self.setup_parent('undo-guest@example.test')
        invite=self.call('family-invite',owner,permission='write')[1]
        self.call('family-accept',guest,code=invite['code'])
        put=self.call('doctor-question-put',guest,ownerId=uid,id='own',text='Question')[1]
        self.assertTrue(put['undoToken'])
        self.assertNotIn('undoToken',self.call('care-list',guest,ownerId=uid)[1]['doctorQuestions'][0])
        self.assertEqual(self.call('doctor-question-delete',guest,ownerId=uid,id='own',undoToken='wrong')[0]['statusCode'],403)
        self.assertEqual(self.call('doctor-question-delete',guest,ownerId=uid,id='own',undoToken=put['undoToken'])[0]['statusCode'],200)
        put=self.call('doctor-question-put',guest,ownerId=uid,id='edited',text='Question')[1]
        self.call('doctor-question-put',owner,id='edited',text='Changed')
        self.assertEqual(self.call('doctor-question-delete',guest,ownerId=uid,id='edited',undoToken=put['undoToken'])[0]['statusCode'],403)

    def test_owner_delete_ignores_expired_or_invalid_undo_token(self):
        from test_api import app
        owner,uid=self.setup_parent('owner-delete@example.test')
        for ident, token in [('expired', 'original'), ('invalid', 'wrong')]:
            saved=self.call('doctor-question-put',owner,id=ident,text=ident)[1]
            db=app.DB()
            try:
                row=db.query('SELECT encrypted_data FROM mh_care_records WHERE owner_id=? AND id=?',(uid,ident)).fetchone()
                question=app.unseal(row[0]);question['at']='2020-01-01T00:00:00+00:00'
                db.query('UPDATE mh_care_records SET encrypted_data=? WHERE owner_id=? AND id=?',(app.seal(question),uid,ident));db.conn.commit()
            finally:
                db.close()
            result=self.call('doctor-question-delete',owner,id=ident,undoToken=saved['undoToken'] if token=='original' else token)
            self.assertEqual(result[0]['statusCode'],200,result[1])
        self.assertEqual(self.call('care-list',owner)[1]['doctorQuestions'],[])

    def test_export_preserves_question_without_internal_token_or_author_id(self):
        owner,_=self.setup_parent('export-question@example.test')
        self.call('doctor-question-put',owner,id='export',text='Вопрос о сне?')
        response,body=self.call('data-export',owner,password='long-test-password')
        self.assertEqual(response['statusCode'],200,body)
        question=next(r for r in body['careRecords'] if r['id']=='export')
        self.assertEqual(question['note'],'Вопрос о сне?')
        self.assertNotIn('undoToken',question)
        self.assertNotIn('addedBy',question)
