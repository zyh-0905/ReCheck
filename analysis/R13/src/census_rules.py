"""Candidate labels for offline review, explicitly not a human gold annotation."""
def classify(row):
    group=row['factory']; name=row['name']; dbs={c['db'] for c in row['explicit_state_constraints']}
    if group=='named_insufficient_information_scenarios':
        return 'insufficient_information_policy'
    if name=='update_contact_relationship_with_relationship_twice_multiple_user_turn':
        return 'ordered_revised_effects'
    if dbs & {'CONTACT','REMINDER','MESSAGING'}:
        return 'terminal_effect_candidate'
    if name in ('cellular_off','wifi_off') or name.startswith('turn_on_'):
        return 'terminal_setting_candidate'
    if 'SETTING' in dbs:
        return 'information_with_transient_prerequisites'
    return 'information_only'

def constraint_kind(db, function):
    if function=='guardrail_similarity': return 'preservation_guardrail'
    return 'interaction_constraint' if db=='SANDBOX' else 'explicit_state_constraint'
