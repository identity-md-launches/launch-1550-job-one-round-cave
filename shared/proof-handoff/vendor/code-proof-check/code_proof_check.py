#!/usr/bin/env python3
"""Capture ZTO runtime code and check its preimage against a saved account proof."""
import argparse
import datetime as dt
import hashlib
import http.client
import json
from pathlib import Path
import sys
import urllib.request

TOOLS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(TOOLS / 'account-proof-check'))
try:
    import account_proof_check as account
finally:
    sys.path.pop(0)
rpc = account.rpc
ZTO = account.ZTO
SCHEMA = 'pinned-zto-code-proof/1'
MAX_FILE = 99000
MAX_CODE = 24576
USER_AGENT = 'Pepeolithic-Code-Proof/1.0 (read-only public Ethereum)'
HERE = Path(__file__).resolve().parent
DEMO_SNAPSHOT = TOOLS / 'account-proof-check/live-zto.json'
DEMO_PROOF = TOOLS / 'account-proof-check/live-proof.json'


def load(path):
    raw = path if type(path) is bytes else account.seal.read_bytes(path)
    if len(raw) > MAX_FILE:
        raise ValueError('evidence file exceeds 99000 bytes')
    return raw, rpc.strict_json(raw)


def proof_context(snapshot_path, proof_path):
    raw, proof = load(proof_path)
    result = account.verify_bundle(snapshot_path, proof)
    return raw, proof, result


def code_bytes(value):
    # Resource limit for this finite observation tool, not a claim about all forks.
    return account.data(value, maximum=MAX_CODE)


def selector(block_hash):
    account.data(block_hash, 32)
    return {'blockHash': block_hash, 'requireCanonical': True}


def validate_request(method, params):
    if method == 'eth_chainId' and params == []:
        return
    if (method == 'eth_getCode' and isinstance(params, list) and len(params) == 2
            and params[0] == ZTO and isinstance(params[1], dict)
            and set(params[1]) == {'blockHash', 'requireCanonical'}
            and params[1]['requireCanonical'] is True):
        account.data(params[1]['blockHash'], 32)
        return
    raise ValueError('only mainnet chain ID and hash-pinned ZTO code reads allowed')


def public_read(endpoint, method, params):
    rpc.validate_endpoint(endpoint)
    validate_request(method, params)
    body = json.dumps({'jsonrpc': '2.0', 'id': 1, 'method': method,
                       'params': params}, allow_nan=False).encode('ascii')
    request = urllib.request.Request(endpoint, data=body, headers={
        'Content-Type': 'application/json', 'Accept': 'application/json',
        'Accept-Encoding': 'identity', 'User-Agent': USER_AGENT})
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), rpc.NoRedirect())
    with opener.open(request, timeout=20) as response:
        if response.status != 200:
            raise ValueError('RPC requires HTTP 200')
        if response.headers.get('Content-Encoding', 'identity').lower() != 'identity':
            raise ValueError('compressed response refused')
        raw = response.read(MAX_FILE + 1)
    if len(raw) > MAX_FILE:
        raise ValueError('RPC response exceeds bound')
    value = rpc.strict_json(raw)
    if not isinstance(value, dict) or set(value) != {'jsonrpc', 'id', 'result'}:
        raise ValueError('expected exact successful JSON-RPC envelope')
    return rpc.validate_response(value)


def verify(snapshot_path, proof_path, bundle):
    proof_raw, proof, context = proof_context(snapshot_path, proof_path)
    if not isinstance(bundle, dict) or set(bundle) != {
            'schema', 'captured_at', 'endpoint', 'chain_id', 'snapshot_sha256',
            'account_proof_sha256', 'block_number', 'block_hash', 'address',
            'method', 'params', 'result'}:
        raise ValueError('unexpected code bundle fields')
    if bundle['schema'] != SCHEMA or bundle['chain_id'] != '0x1':
        raise ValueError('unsupported schema or chain')
    rpc.validate_endpoint(bundle['endpoint'])
    stamp = bundle['captured_at']
    if not isinstance(stamp, str) or not stamp.endswith('Z'):
        raise ValueError('capture time must be UTC')
    dt.datetime.fromisoformat(stamp[:-1] + '+00:00')
    if (bundle['snapshot_sha256'] != context['snapshot_sha256'] or
            bundle['account_proof_sha256'] != hashlib.sha256(proof_raw).hexdigest()):
        raise ValueError('code bundle belongs to different evidence bytes')
    if (bundle['block_number'] != proof['block_number'] or
            bundle['block_hash'] != context['block_hash'] or bundle['address'] != ZTO):
        raise ValueError('code anchor differs from proved account')
    validate_request(bundle['method'], bundle['params'])
    if (bundle['method'] != 'eth_getCode' or
            bundle['params'] != [ZTO, selector(context['block_hash'])]):
        raise ValueError('code request differs from proof anchor')
    code = code_bytes(bundle['result'])
    computed = '0x' + account.header.keccak256(code).hex()
    if computed != context['account']['code_hash']:
        raise ValueError('runtime code does not match proved code hash')
    return {
        'schema': 'pinned-zto-code-proof-check/1', 'verified': True,
        'network_used': False, 'token': ZTO,
        'snapshot_sha256': context['snapshot_sha256'],
        'account_proof_sha256': bundle['account_proof_sha256'],
        'block_number': context['block_number'], 'block_hash': context['block_hash'],
        'state_root': context['state_root'], 'bytecode_bytes': len(code),
        'bytecode_sha256': hashlib.sha256(code).hexdigest(),
        'proved_code_hash': computed, 'account_proof_nodes': context['account']['proof_nodes'],
        'reported_provenance': {**context['reported_provenance'],
            'code_endpoint': bundle['endpoint'], 'code_captured_at': stamp},
        'evidence_limits': ('Runtime code preimage and account inclusion relative to the '
            'supplied self-consistent Prague header. No trusted mainnet anchor, consensus '
            'or finality verification. Endpoints and capture times are reported metadata. '
            'No code execution, source-code equivalence, proxy-target resolution, storage '
            'slot, ZTO balance, totalSupply or eth_call result is proved. '
            'Matching bytecode does not establish contract safety or current state.')}


def capture(snapshot_path, proof_path, endpoint=rpc.DEFAULT_RPC, read=None):
    proof_raw, proof, context = proof_context(snapshot_path, proof_path)
    rpc.validate_endpoint(endpoint)
    read = read or (lambda method, params: public_read(endpoint, method, params))
    if read('eth_chainId', []) != '0x1':
        raise ValueError('Ethereum mainnet chain ID required')
    params = [ZTO, selector(context['block_hash'])]
    result = read('eth_getCode', params)
    code_bytes(result)
    bundle = {
        'schema': SCHEMA,
        'captured_at': dt.datetime.now(dt.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'),
        'endpoint': endpoint, 'chain_id': '0x1',
        'snapshot_sha256': context['snapshot_sha256'],
        'account_proof_sha256': hashlib.sha256(proof_raw).hexdigest(),
        'block_number': proof['block_number'], 'block_hash': context['block_hash'],
        'address': ZTO, 'method': 'eth_getCode', 'params': params, 'result': result}
    verify(snapshot_path, proof_path, bundle)
    return bundle


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    sub.add_parser('demo', help='offline verification of retained real ZTO bytecode')
    check = sub.add_parser('check', help='offline check of three saved evidence files')
    check.add_argument('snapshot')
    check.add_argument('account_proof')
    check.add_argument('code_bundle')
    cap = sub.add_parser('capture', help='two public read-only RPC requests')
    cap.add_argument('snapshot')
    cap.add_argument('account_proof')
    cap.add_argument('--rpc', default=rpc.DEFAULT_RPC)
    args = parser.parse_args()
    try:
        if args.command == 'capture':
            result = capture(args.snapshot, args.account_proof, args.rpc)
        elif args.command == 'demo':
            result = verify(DEMO_SNAPSHOT, DEMO_PROOF, load(HERE / 'live-code.json')[1])
        else:
            result = verify(args.snapshot, args.account_proof, load(args.code_bundle)[1])
        output = json.dumps(result, indent=2, sort_keys=True, allow_nan=False) + '\n'
        if len(output.encode('utf-8')) > MAX_FILE:
            raise ValueError('output exceeds bound')
    except (ValueError, TypeError, KeyError, OSError, RuntimeError, RecursionError,
            http.client.HTTPException):
        print('code-proof-check: invalid evidence or public RPC failure; no result emitted',
              file=sys.stderr)
        return 1
    sys.stdout.write(output)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
