"""Execute one hash-verified upstream function body with EXPLICIT TEST DOUBLES.

Not a ToolSandbox installation, native integration test, or benchmark result.
Only the function body is retained. Imports/decorators, DB/filtering, phone
validation, UUID and clock are injected doubles, enumerated in the output.
"""
from __future__ import annotations
import ast
import copy
import datetime
import hashlib
import json
from fractions import Fraction
from pathlib import Path
from types import SimpleNamespace

COMMIT = 'c8571d7854316d2e1c5f288e59fe1e34e53f6dd1'
EXPECTED_BLOB = '9900cd2fbd4b88f25cf937776c4e185c0ab6339e'

class WorldDouble:
    """Memory-only collaborator; does not claim equivalence to ExecutionContext."""
    old_phone = '+12025550111'
    new_phone = '+12025550112'
    def __init__(self):
        self.contacts = [
            {'person_id': 'self', 'phone_number': '+12025550110', 'is_self': True},
            {'person_id': 'target', 'phone_number': self.old_phone, 'is_self': False},
            {'person_id': 'other', 'phone_number': '+12025550113', 'is_self': False}]
        self.cellular = True
        self.messages = []
        self.events = []
    def search_contacts(self, **kwargs):
        self.events.append({'dependency': 'search_contacts', 'arguments': kwargs})
        return copy.deepcopy([x for x in self.contacts
                              if all(x.get(k) == v for k, v in kwargs.items())])
    def add_to_database(self, namespace, rows):
        if namespace != 'MESSAGING': raise ValueError('Unexpected namespace')
        self.messages.extend(copy.deepcopy(rows))
    def get_cellular(self):
        self.events.append({'dependency': 'get_cellular_service_status'})
        return self.cellular

class DuplicateErrorDouble(Exception): pass

class FixedDateTime:
    @classmethod
    def now(cls): return datetime.datetime(2024, 1, 1, tzinfo=datetime.timezone.utc)

def validate_phone_double(phone):
    if not isinstance(phone, str): raise TypeError('Fixture phone must be a string')
    if not phone.startswith('+') or not phone[1:].isdigit():
        raise ValueError('Fixture phone must use +digits')

def source_identity(path: Path) -> dict:
    raw = path.read_bytes()
    sha1 = hashlib.sha1(b'blob ' + str(len(raw)).encode() + b'\0' + raw).hexdigest()
    return {'commit': COMMIT, 'git_blob_sha1': sha1,
            'sha256': hashlib.sha256(raw).hexdigest(), 'bytes': len(raw)}

def load_sender(path: Path, world: WorldDouble):
    identity = source_identity(path)
    if identity['git_blob_sha1'] != EXPECTED_BLOB:
        raise ValueError('Upstream source differs from pinned Git blob')
    tree = ast.parse(path.read_text(encoding='utf-8'))
    selected = [n for n in tree.body if isinstance(n, ast.FunctionDef)
                and n.name == 'send_message_with_phone_number']
    if len(selected) != 1: raise ValueError('Exactly one upstream function is required')
    node = copy.deepcopy(selected[0])
    body = '\n'.join(ast.dump(x, include_attributes=False) for x in node.body)
    node.decorator_list = []  # Deliberate unit-test boundary; NOT native decorators.
    module = ast.fix_missing_locations(ast.Module(body=[node], type_ignores=[]))
    ns = {'validate_phone_number': validate_phone_double,
          'get_current_context': lambda: world,
          'get_cellular_service_status': world.get_cellular,
          'uuid4': lambda: 'test-message-0001',
          'search_contacts': world.search_contacts,
          'DuplicateError': DuplicateErrorDouble,
          'DatabaseNamespace': SimpleNamespace(MESSAGING='MESSAGING'),
          'datetime': SimpleNamespace(datetime=FixedDateTime)}
    exec(compile(module, str(path), 'exec'), ns)
    fn = ns['send_message_with_phone_number']
    fn.__source_body_ast__ = body
    return fn

def indistinguishability_bound() -> dict:
    # Distinct recipient facts, same public pre-action observation, disjoint
    # correct phone actions. Under a uniform prior error is 1/2 for ANY mixture.
    rows = []
    for k in range(101):
        p = Fraction(k, 100)
        risk = Fraction(1, 2) * (1 - p) + Fraction(1, 2) * p
        rows.append(risk)
    assert len(set(rows)) == 1
    return {'uniform_two_world_error_lower_bound': str(rows[0]),
            'tight_at_rational_randomization': str(min(rows)),
            'checked_randomizations': len(rows), 'novel_theorem_claim': False,
            'qualification': 'Elementary two-world construction, no dataset or LLM estimate; '
                             'abstention removes wrong sends only by reducing completion.'}

def run_diagnostics(source: Path) -> dict:
    cases = []
    for condition in ('stable', 'unrelated_change', 'retired_target_number',
                      'reassigned_target_number'):
        for action in ('reuse_cached', 'read_then_send'):
            w = WorldDouble()
            if condition == 'unrelated_change': w.contacts[2]['phone_number'] = '+12025550114'
            if condition in ('retired_target_number', 'reassigned_target_number'):
                w.contacts[1]['phone_number'] = w.new_phone
            if condition == 'reassigned_target_number': w.contacts[2]['phone_number'] = w.old_phone
            phone = (w.search_contacts(person_id='target')[0]['phone_number']
                     if action == 'read_then_send' else w.old_phone)
            value = load_sender(source, w)(phone, 'synthetic fixture message')
            cases.append({'fixture': condition, 'script': action, 'immediate_return': value,
                          'writes': w.messages, 'dependency_events': w.events,
                          'fixture_target_received': w.messages[0]['recipient_person_id'] == 'target',
                          'additional_contact_query': int(action == 'read_then_send')})
    return {'evidence_type': 'SOURCE_LEVEL_UNIT_TEST_WITH_TEST_DOUBLES',
            'source': source_identity(source), 'native_toolsandbox_executed': False,
            'new_llm_calls': 0, 'cases': cases,
            'double_boundaries': ['ExecutionContext/database storage', 'exact contact filtering',
                                 'phone validator', 'registration/typecheck decorators removed',
                                 'UUID generator', 'clock', 'DuplicateError type'],
            'interpretation': 'Software counterexamples, not empirical policy success rates.',
            'elementary_information_boundary': indistinguishability_bound()}

if __name__ == '__main__':
    root = Path(__file__).resolve().parent
    report = run_diagnostics(root / 'upstream_excerpt' / 'messaging.py')
    out = root / 'results' / 'source_contract_diagnostics.json'
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(out)
