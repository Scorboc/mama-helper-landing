import copy
import unittest
from datetime import date
import test_api as base


class ProfileLockTest(unittest.TestCase):
    setUp = base.AccountsTest.setUp
    tearDown = base.AccountsTest.tearDown
    call = base.AccountsTest.call
    register = base.AccountsTest.register

    def test_lock_all_fields_and_allow_name_and_new_child(self):
        cookie, session = self.register('lock@example.test')
        state = session['state']
        state['profile'] = dict(childName='Первый', childSex='unknown', role='mom', stage='child', birthDate='2025-01-01', week=20, weekDate=date.today().isoformat(), feeding='unknown', sleep='', health='', healthConfirmed=False, topics=[])
        self.assertEqual(self.call('save',cookie,state=state,revision=0)[0]['statusCode'],200)
        for field, value in [('birthDate','2024-01-01'),('role','dad'),('feeding','mixed'),('sleep','Другая информация'),('childSex','male')]:
            changed=copy.deepcopy(state); changed['profile'][field]=value
            self.assertEqual(self.call('save',cookie,state=changed,revision=1)[0]['statusCode'],403,field)
        changed=copy.deepcopy(state); changed['profile']=None
        self.assertEqual(self.call('save',cookie,state=changed,revision=1)[0]['statusCode'],403)
        changed=copy.deepcopy(state); changed['activeChildId']='replacement-id'
        self.assertEqual(self.call('save',cookie,state=changed,revision=1)[0]['statusCode'],403)
        state['profile']['childName']='Новое имя'
        state['children']=[dict(id='second',data=dict(profile={**state['profile'],'birthDate':'2024-01-01'}))]
        self.assertEqual(self.call('save',cookie,state=state,revision=1)[0]['statusCode'],200)
        changed=copy.deepcopy(state); changed['children'][0]['data']['profile']['birthDate']='2023-01-01'
        self.assertEqual(self.call('save',cookie,state=changed,revision=2)[0]['statusCode'],403)
        switched=copy.deepcopy(state)
        switched['profile']=state['children'][0]['data']['profile']
        switched['activeChildId']='second'
        switched['children']=[dict(id='primary',data=dict(profile=state['profile']))]
        self.assertEqual(self.call('save',cookie,state=switched,revision=2)[0]['statusCode'],200)
        self.assertEqual(self.call('save',cookie,state=state,revision=2)[0]['statusCode'],409)


if __name__ == '__main__': unittest.main()
