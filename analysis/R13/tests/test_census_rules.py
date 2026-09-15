import unittest
from census_rules import classify,constraint_kind
class CensusTests(unittest.TestCase):
 def r(self,name,dbs=(),factory='named_multiple_tool_call_scenarios'):
  return {'name':name,'factory':factory,'explicit_state_constraints':[{'db':x} for x in dbs]}
 def test_guardrail_not_target(self):self.assertEqual(constraint_kind('CONTACT','guardrail_similarity'),'preservation_guardrail')
 def test_dialog_not_state(self):self.assertEqual(constraint_kind('SANDBOX','snapshot_similarity'),'interaction_constraint')
 def test_setting_target(self):self.assertEqual(classify(self.r('wifi_off',['SETTING'])),'terminal_setting_candidate')
 def test_setting_prerequisite(self):self.assertEqual(classify(self.r('find_temperature_low_battery_mode',['SETTING'])),'information_with_transient_prerequisites')
 def test_message_with_prerequisite(self):self.assertEqual(classify(self.r('send_message',['SETTING','MESSAGING'])),'terminal_effect_candidate')
 def test_revision_not_terminalize_all(self):self.assertEqual(classify(self.r('update_contact_relationship_with_relationship_twice_multiple_user_turn',['CONTACT'])),'ordered_revised_effects')
 def test_information(self):self.assertEqual(classify(self.r('search_message')),'information_only')
 def test_missing_info_first(self):self.assertEqual(classify(self.r('send_message',['MESSAGING'],'named_insufficient_information_scenarios')),'insufficient_information_policy')
