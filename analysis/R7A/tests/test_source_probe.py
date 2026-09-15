import ast
import copy
import pathlib
import unittest

from source_probe import (WorldDouble, load_sender, source_identity, run_diagnostics,
                          indistinguishability_bound, COMMIT)

ROOT = pathlib.Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'upstream_excerpt' / 'messaging.py'

class SourceContractTest(unittest.TestCase):
    def setUp(self):
        self.w = WorldDouble()
        self.send = load_sender(SOURCE, self.w)

    def test_exact_git_blob_identity(self):
        self.assertEqual(source_identity(SOURCE)['git_blob_sha1'],
                         '9900cd2fbd4b88f25cf937776c4e185c0ab6339e')

    def test_same_contact_message_points_to_target(self):
        self.assertEqual(self.send(self.w.old_phone, 'fixture message'), 'test-message-0001')
        self.assertEqual(self.w.messages[0]['recipient_person_id'], 'target')

    def test_retired_phone_succeeds_but_recipient_is_none(self):
        self.w.contacts[1]['phone_number'] = self.w.new_phone
        self.assertEqual(self.send(self.w.old_phone, 'fixture message'), 'test-message-0001')
        self.assertIsNone(self.w.messages[0]['recipient_person_id'])

    def test_reassigned_phone_succeeds_but_points_to_other_person(self):
        self.w.contacts[1]['phone_number'] = self.w.new_phone
        self.w.contacts[2]['phone_number'] = self.w.old_phone
        self.assertEqual(self.send(self.w.old_phone, 'fixture message'), 'test-message-0001')
        self.assertEqual(self.w.messages[0]['recipient_person_id'], 'other')

    def test_read_current_contact_then_send_uses_new_phone(self):
        self.w.contacts[1]['phone_number'] = self.w.new_phone
        phone = self.w.search_contacts(person_id='target')[0]['phone_number']
        self.send(phone, 'fixture message')
        self.assertEqual(self.w.messages[0]['recipient_person_id'], 'target')
        self.assertEqual(self.w.messages[0]['recipient_phone_number'], self.w.new_phone)

    def test_cellular_off_fails_before_write(self):
        self.w.cellular = False
        with self.assertRaisesRegex(ConnectionError, 'Cellular service is not enabled'):
            self.send(self.w.old_phone, 'fixture message')
        self.assertEqual(self.w.messages, [])

    def test_reactive_cellular_enable_then_retry_no_duplicate_write(self):
        self.w.cellular = False
        with self.assertRaises(ConnectionError): self.send(self.w.old_phone, 'fixture message')
        self.w.cellular = True
        self.send(self.w.old_phone, 'fixture message')
        self.assertEqual(len(self.w.messages), 1)

    def test_unrelated_phone_change_not_target_change(self):
        self.w.contacts[2]['phone_number'] = '+12025550114'
        self.send(self.w.old_phone, 'fixture message')
        self.assertEqual(self.w.messages[0]['recipient_person_id'], 'target')

    def test_immediate_observation_equivalent_despite_recipient_difference(self):
        stable = self.send(self.w.old_phone, 'fixture message')
        changed = WorldDouble()
        changed.contacts[1]['phone_number'] = changed.new_phone
        changed.contacts[2]['phone_number'] = changed.old_phone
        observed = load_sender(SOURCE, changed)(changed.old_phone, 'fixture message')
        self.assertEqual(stable, observed)
        self.assertNotEqual(self.w.messages[0]['recipient_person_id'],
                            changed.messages[0]['recipient_person_id'])

    def test_later_lookup_does_not_undo_prior_write(self):
        self.w.contacts[1]['phone_number'] = self.w.new_phone
        self.send(self.w.old_phone, 'fixture message')
        self.w.search_contacts(person_id='target')
        self.assertEqual(len(self.w.messages), 1)
        self.assertIsNone(self.w.messages[0]['recipient_person_id'])

    def test_absent_self_is_rejected(self):
        self.w.contacts = [c for c in self.w.contacts if not c['is_self']]
        with self.assertRaisesRegex(Exception, '1 and only 1 self entry'):
            self.send(self.w.old_phone, 'fixture message')
        self.assertEqual(self.w.messages, [])

    def test_duplicate_self_is_rejected(self):
        self.w.contacts.append(copy.deepcopy(self.w.contacts[0]))
        with self.assertRaisesRegex(Exception, '1 and only 1 self entry'):
            self.send(self.w.old_phone, 'fixture message')
        self.assertEqual(self.w.messages, [])

    def test_fixture_validator_rejects_non_string(self):
        with self.assertRaises(TypeError): self.send(None, 'fixture message')
        self.assertEqual(self.w.messages, [])

    def test_modified_source_rejected(self):
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            p = pathlib.Path(d) / 'messaging.py'
            p.write_bytes(SOURCE.read_bytes() + b'\n')
            with self.assertRaises(ValueError): load_sender(p, self.w)

    def test_execution_retains_original_function_body_ast(self):
        original = next(x for x in ast.parse(SOURCE.read_text()).body
                        if isinstance(x, ast.FunctionDef) and x.name == 'send_message_with_phone_number')
        self.assertEqual(self.send.__source_body_ast__,
                         '\n'.join(ast.dump(x, include_attributes=False) for x in original.body))

    def test_diagnostics_label_not_native_benchmark(self):
        result = run_diagnostics(SOURCE)
        self.assertEqual(result['evidence_type'], 'SOURCE_LEVEL_UNIT_TEST_WITH_TEST_DOUBLES')
        self.assertFalse(result['native_toolsandbox_executed'])
        self.assertEqual(result['new_llm_calls'], 0)
        self.assertEqual(len(result['cases']), 8)

    def test_elementary_information_bound(self):
        bound = indistinguishability_bound()
        self.assertEqual(bound['uniform_two_world_error_lower_bound'], '1/2')
        self.assertEqual(bound['tight_at_rational_randomization'], '1/2')
        self.assertFalse(bound['novel_theorem_claim'])

if __name__ == '__main__': unittest.main()
