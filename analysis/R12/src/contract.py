"""Separate terminal checks for this source audit; not an official score override."""
def terminal_valid(state, field, expected):
    return type(expected) is bool and type(state.get(field)) is bool and state[field] is expected

def classify(similarity, valid):
    return ('full_score' if similarity == 1.0 else 'not_full_score') + ('_terminal_true' if valid else '_terminal_mismatch' if similarity == 1.0 else '_terminal_false')

def project(value):
    if isinstance(value, dict):
        return {k:project(v) for k,v in value.items() if k != 'elapsed_seconds'}
    if isinstance(value, list):return [project(v) for v in value]
    return value
