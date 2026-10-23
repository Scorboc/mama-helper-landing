import unittest
import age_guidance


class MilestoneGuidanceTest(unittest.TestCase):
    def test_existing_first_words_tip_maps_without_new_age_windows(self):
        card=age_guidance.get('words-fifteen')
        self.assertEqual(age_guidance.mark_skill(card),'words')
        self.assertEqual((card['minMonths'],card['maxMonths']),(15,18))

    def test_only_explicit_development_topics_map(self):
        for skill in ('roll','crawl','stand','walk'):
            card=age_guidance.get('milestone-'+skill)
            self.assertIsNotNone(card)
            self.assertEqual(age_guidance.mark_skill({**card,'title':'Новый заголовок'}),skill)
        self.assertIsNone(age_guidance.mark_skill({'title':'Учимся ползать в игре','section':'Развитие'}))
        self.assertIsNone(age_guidance.mark_skill({'milestoneSkill':'__proto__'}))
        self.assertIsNone(age_guidance.mark_skill({'title':'Первые слова','section':'Игры'}))
        self.assertIsNone(age_guidance.mark_skill({'title':'Наблюдение за ручками','section':'Развитие'}))
