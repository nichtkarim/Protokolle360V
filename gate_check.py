import os
from src.asset_protocol_generator.license_gate import is_usage_allowed, GATE_URL, _fetch_http
print('APG_ALLOW=', os.environ.get('APG_ALLOW'))
print('APG_GATE_URL=', os.environ.get('APG_GATE_URL'))
print('GATE_URL=', GATE_URL)
try:
	content = _fetch_http(GATE_URL, timeout=5.0)
	print('fetched_len=', 0 if content is None else len(content))
	print('fetched_head=', '' if content is None else content[:80].replace('\n',' '))
except Exception as e:
	print('fetch_error=', e)
print('allowed=', is_usage_allowed())
