"""Frozen return-label policy, not an assertion about underlying model weights.
The additional response label is based on one retained R7C smoke response.
No alias inference, prefix matching, alternative endpoint, or model fallback.
"""
from pilot.client import RunStopped

POLICY_ID='R7C1_RESPONSE_LABELS_V1'
REQUEST_MODEL='deepseek-v4-flash'
ACCEPTED_RESPONSE_LABELS=('deepseek-v4-flash','deepseek-flash')

def response_identity(cfg, body):
    requested=cfg.get('model')
    returned=body.get('model')
    fingerprint=body.get('system_fingerprint')
    if cfg.get('backend_kind')=='live':
        if requested!=REQUEST_MODEL:
            raise RunStopped('Requested model differs from the frozen request label; no fallback.')
        if type(returned) is not str or returned not in ACCEPTED_RESPONSE_LABELS:
            raise RunStopped('Returned model is outside the explicit R7C1 response-label allowlist; raw evidence retained.')
        if type(fingerprint) is not str or not fingerprint.strip():
            raise RunStopped('Missing or invalid system_fingerprint; cannot establish the response-metadata cohort.')
    elif cfg.get('backend_kind')=='test_fixture':
        if returned!=requested:
            raise RunStopped('Software fixture response label differs from its requested fixture label.')
    else:
        raise RunStopped('Unknown backend kind.')
    return {'policy_id':POLICY_ID,'requested_model':requested,'returned_model':returned,
            'system_fingerprint':fingerprint,'weight_identity_verified':False}
