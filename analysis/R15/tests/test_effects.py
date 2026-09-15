import unittest, sys
from pathlib import Path
from datetime import datetime, timezone
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from effects import normalized, latest_outgoing_target, clock_context, effect_at, combine, literal, new_rows

def batch(name,args,result):
 import json
 return {'calls':[{'id':'x','function':{'name':name,'arguments':json.dumps(args)}}], 'receipts':[{'tool_call_id':'x','content':result}]}

def raw_rec(batches):return {'batches':batches,'issues':[]}

class EffectTests(unittest.TestCase):
 def test_apostrophe_punctuation(self):self.assertEqual(normalized(' How’s the new album coming along? '),normalized("How's the new album coming along."))
 def test_not_remove_words(self):self.assertNotEqual(normalized('Do not buy chocolate milk'),normalized('Buy chocolate milk'))
 def test_false_dominates_unknown(self):self.assertIs(combine(False,None),False)
 def test_unknown_does_not_become_false(self):self.assertIsNone(combine(True,None))
 def test_true_and_true(self):self.assertIs(combine(True,True),True)
 def test_literal_no_exec(self):self.assertIsNone(literal("__import__('os').system('echo unsafe')"))
 def test_literal_dict(self):self.assertEqual(literal("{'year': 2025}"),{'year':2025})
 def test_new_rows_not_initial_ids(self):self.assertEqual(new_rows([{'id':'a'}],[{'id':'a'},{'id':'b'}],'id'),[{'id':'b'}])
 def test_new_rows_missing_initial_unknown(self):self.assertIsNone(new_rows(None,[{'id':'b'}],'id'))
 def test_latest_outgoing_not_incoming(self):
  init={'CONTACT':[{'person_id':'me','is_self':True},{'person_id':'A','is_self':False},{'person_id':'B','is_self':False}], 'MESSAGING':[{'sender_person_id':'me','recipient_person_id':'A','creation_timestamp':10},{'sender_person_id':'B','recipient_person_id':'me','creation_timestamp':20}]}
  self.assertEqual(latest_outgoing_target(init),'A')
 def test_latest_tie_unknown(self):
  init={'CONTACT':[{'person_id':'me','is_self':True},{'person_id':'A'},{'person_id':'B'}], 'MESSAGING':[{'sender_person_id':'me','recipient_person_id':'A','creation_timestamp':10},{'sender_person_id':'me','recipient_person_id':'B','creation_timestamp':10}]}
  self.assertIsNone(latest_outgoing_target(init))
 def test_clock_paired_offsets(self):
  ts=datetime(2025,9,16,3,0,tzinfo=timezone.utc).timestamp()
  rec=raw_rec([batch('get_current_timestamp',{},str(ts)),batch('timestamp_to_datetime_info',{'timestamp':ts},"{'year':2025,'month':9,'day':16,'hour':11,'minute':0,'second':0}")])
  c=clock_context(rec,'add_reminder_content_and_week_delta_and_time')
  self.assertEqual(c['offset_seconds'],28800)
  self.assertEqual(c['target_epochs'],[datetime(2025,9,17,9,0,tzinfo=timezone.utc).timestamp()])
 def test_missing_clock_unknown(self):self.assertIsNone(clock_context(raw_rec([]),'add_reminder_content_and_week_delta_and_time')['target_epochs'])
 def test_absolute_without_conversion_unknown(self):self.assertIsNone(clock_context(raw_rec([]),'add_reminder_content_and_date_and_time')['target_epochs'])
 def test_exact_date_conversion(self):
  c=clock_context(raw_rec([batch('datetime_info_to_timestamp',{'year':2024,'month':3,'day':22,'hour':17},'1711098000.0')]),'add_reminder_content_and_date_and_time')
  self.assertEqual(c['target_epochs'],[1711098000.0])
 def test_inconsistent_offsets_unknown(self):
  b=[batch('datetime_info_to_timestamp',{'year':2024,'month':3,'day':22,'hour':17},'1711098000.0'),batch('datetime_info_to_timestamp',{'year':2024,'month':3,'day':22,'hour':17},'1711126800.0')]
  self.assertIsNone(clock_context(raw_rec(b),'add_reminder_content_and_date_and_time')['target_epochs'])
 def test_friday_ambiguity(self):
  b=[batch('get_current_timestamp',{},'1757991662.414098'),batch('timestamp_to_datetime_info',{'timestamp':1757991662.414098},"{'year':2025,'month':9,'day':16,'hour':11,'minute':1,'second':2}")]
  c=clock_context(raw_rec(b),'add_reminder_content_and_weekday_delta_and_time')
  self.assertEqual(len(c['target_epochs']),2)
  self.assertEqual(c['target_epochs'][1]-c['target_epochs'][0],7*86400)
 def test_wrong_reminder_time(self):
  v=effect_at('add_reminder_content_and_date_and_time',{'REMINDER':[{'reminder_id':'b','content':'Buy chocolate milk','reminder_timestamp':22}]},{'REMINDER':[]},{'target_epochs':[42]},None)
  self.assertIs(v['effect'],False);self.assertIs(v['content'],True);self.assertIs(v['time'],False)
 def test_new_correct_reminder(self):
  v=effect_at('add_reminder_content_and_date_and_time',{'REMINDER':[{'reminder_id':'b','content':'Buy chocolate milk.','reminder_timestamp':42}]},{'REMINDER':[]},{'target_epochs':[42]},None)
  self.assertIs(v['effect'],True)
 def test_existing_not_new_reminder(self):
  r=[{'reminder_id':'b','content':'Buy chocolate milk','reminder_timestamp':42}]
  self.assertIs(effect_at('add_reminder_content_and_date_and_time',{'REMINDER':r},{'REMINDER':r},{'target_epochs':[42]},None)['effect'],False)
 def test_content_exists_time_unknown(self):
  r=[{'reminder_id':'b','content':'Buy chocolate milk','reminder_timestamp':42}]
  self.assertIsNone(effect_at('add_reminder_content_and_date_and_time',{'REMINDER':r},{'REMINDER':[]},{'target_epochs':None},None)['effect'])
 def test_message_recipient_and_self(self):
  init={'CONTACT':[{'person_id':'me','is_self':True}],'MESSAGING':[]}
  s={'MESSAGING':[{'message_id':'b','sender_person_id':'me','recipient_phone_number':'+12453344098','content':"How's the new album coming along."}]}
  self.assertIs(effect_at('send_message_with_phone_number_and_content',s,init,{},None)['effect'],True)
 def test_message_wrong_recipient(self):
  init={'CONTACT':[{'person_id':'me','is_self':True}],'MESSAGING':[]}
  s={'MESSAGING':[{'message_id':'b','sender_person_id':'me','recipient_phone_number':'+1999','content':"How's the new album coming along."}]}
  self.assertIs(effect_at('send_message_with_phone_number_and_content',s,init,{},None)['effect'],False)
 def test_contact_wrong_self(self):
  s={'CONTACT':[{'person_id':'me','phone_number':'+10293847563'},{'person_id':'A','phone_number':'+1000'}]}
  self.assertIs(effect_at('modify_contact_with_message_recency',s,{}, {},'A')['effect'],False)
 def test_contact_unknown_target(self):self.assertIsNone(effect_at('modify_contact_with_message_recency',{'CONTACT':[]},{},{},None)['effect'])

class AdditionalTests(unittest.TestCase):
 def test_reminder_paraphrase_not_false(self):
  r=[{'reminder_id':'b','content':'Get some chocolate milk','reminder_timestamp':42}]
  self.assertIs(effect_at('add_reminder_content_and_date_and_time',{'REMINDER':r},{'REMINDER':[]},{'target_epochs':[42]},None)['effect'],True)
 def test_unknown_reminder_paraphrase(self):
  r=[{'reminder_id':'b','content':'Maybe procure a cocoa beverage','reminder_timestamp':42}]
  self.assertIsNone(effect_at('add_reminder_content_and_date_and_time',{'REMINDER':r},{'REMINDER':[]},{'target_epochs':[42]},None)['effect'])
 def test_message_greeting_not_false(self):
  init={'CONTACT':[{'person_id':'me','is_self':True}],'MESSAGING':[]}
  r={'MESSAGING':[{'message_id':'b','sender_person_id':'me','recipient_phone_number':'+12453344098','content':"Hey Fredrik! How's the new album coming along?"}]}
  self.assertIs(effect_at('send_message_with_phone_number_and_content',r,init,{},None)['effect'],True)
 def test_unknown_message_content_is_unknown(self):
  init={'CONTACT':[{'person_id':'me','is_self':True}],'MESSAGING':[]}
  r={'MESSAGING':[{'message_id':'b','sender_person_id':'me','recipient_phone_number':'+12453344098','content':"Please stop making music"}]}
  self.assertIsNone(effect_at('send_message_with_phone_number_and_content',r,init,{},None)['effect'])

if __name__=='__main__':unittest.main()

