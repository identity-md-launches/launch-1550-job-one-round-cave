#!/usr/bin/env python3
"""Carry a proved ZTO runtime-code observation beside an account-proof handoff."""
import argparse
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import struct
import sys
import zipfile

import proof_handoff as base
from workspace_io import file_parts, read_workspace, save_new

HERE = Path(__file__).resolve().parent
CODE = 'evidence/code.json'
LINK = 'link/account-archive.json'
REPORT = 'review/code.json'
PATHS = {CODE, LINK, REPORT}
MAX_BYTES = 99000
LIMITS = base.inspector.Limits(archive_bytes=MAX_BYTES, payload_bytes=MAX_BYTES,
                                manifest_bytes=4096, metadata_bytes=4096, files=3)


def load_code():
    path = HERE / 'vendor/code-proof-check/code_proof_check.py'
    spec = importlib.util.spec_from_file_location('shared_zto_code_proof', path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


code_check = load_code()


def canonical(value):
    raw = (json.dumps(value, sort_keys=True, separators=(',', ':'),
                      ensure_ascii=True, allow_nan=False) + '\n').encode('ascii')
    if len(raw) > MAX_BYTES:
        raise ValueError('JSON output exceeds byte bound')
    return raw


def bounded(raw):
    if type(raw) is not bytes or not raw or len(raw) > MAX_BYTES:
        raise ValueError('nonempty bytes of at most 99000 required')
    return raw


def account_payloads(account_archive):
    base.inspect_bytes(bounded(account_archive))
    with zipfile.ZipFile(io.BytesIO(account_archive)) as archive:
        return archive.read(base.SNAPSHOT), archive.read(base.PROOF)


def recompute(account_archive, code_raw):
    snapshot, proof = account_payloads(account_archive)
    bundle = base.proof.rpc.strict_json(bounded(code_raw))
    report = code_check.verify(snapshot, proof, bundle)
    report['code_bundle_sha256'] = hashlib.sha256(code_raw).hexdigest()
    return report


def build(account_archive, code_raw):
    report = recompute(account_archive, code_raw)
    link = {'schema': 'zto-code-extension-link/1',
            'account_archive_sha256': hashlib.sha256(account_archive).hexdigest()}
    files = {CODE: code_raw, LINK: canonical(link), REPORT: canonical(report)}
    archive = base.writer.build(files)
    if len(archive) > MAX_BYTES:
        raise ValueError('extension archive exceeds byte bound')
    inspect_bytes(account_archive, archive)
    return archive


def inspect_bytes(account_archive, extension_archive, expected_account=None,
                  expected_extension=None):
    account_archive = bounded(account_archive)
    extension_archive = bounded(extension_archive)
    account_receipt = base.inspect_bytes(account_archive, expected_account)
    receipt = base.inspector.inspect_stream(io.BytesIO(extension_archive), LIMITS,
                                            expected_extension)
    if {entry['path'] for entry in receipt['files']} != PATHS:
        raise ValueError('exact code, link and report payloads required')
    with zipfile.ZipFile(io.BytesIO(extension_archive)) as archive:
        files = {name: archive.read(name) for name in PATHS}
    link = {'schema': 'zto-code-extension-link/1',
            'account_archive_sha256': account_receipt['archive_sha256']}
    if files[LINK] != canonical(link):
        raise ValueError('extension linked to another account archive')
    report = recompute(account_archive, files[CODE])
    if files[REPORT] != canonical(report):
        raise ValueError('stored code report differs from recomputed evidence')
    if base.writer.build(files) != extension_archive:
        raise ValueError('extension is not reproducible under HANDOFF writer')
    return {'schema': 'zto-code-proof-handoff-extension/1', 'verified': True,
            'account_archive_sha256': account_receipt['archive_sha256'],
            'extension_archive_sha256': receipt['archive_sha256'],
            'account_proof_recomputed': True, 'code_hash_recomputed': True,
            'byte_reproducible': True, 'network_used': False,
            'payloads_extracted_or_executed': False, 'code': report,
            'limits': 'Proof is relative to a supplied state root; no trusted mainnet anchor, consensus, finality, source equivalence or code safety is established.'}


def demo():
    account_archive = (HERE / 'examples/zto-proof.zip').read_bytes()
    code_raw = (HERE / 'examples/zto-code.json').read_bytes()
    extension = build(account_archive, code_raw)
    if extension != build(account_archive, code_raw):
        raise ValueError('nondeterministic extension')
    result = inspect_bytes(account_archive, extension)
    result['demo'] = 'Dated real ZTO code and account proof; offline, no writes.'
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    sub.add_parser('demo')
    pack = sub.add_parser('pack')
    pack.add_argument('account_archive')
    pack.add_argument('code_bundle')
    pack.add_argument('extension_archive')
    check = sub.add_parser('check')
    check.add_argument('account_archive')
    check.add_argument('extension_archive')
    check.add_argument('--account-sha256')
    check.add_argument('--extension-sha256')
    args = parser.parse_args(argv)
    try:
        if args.command == 'demo':
            result = demo()
        elif args.command == 'pack':
            file_parts(args.extension_archive)
            account_archive = read_workspace(args.account_archive)
            data = build(account_archive, read_workspace(args.code_bundle))
            result = inspect_bytes(account_archive, data)
            result['output'] = args.extension_archive
            encoded = canonical(result)
            save_new(args.extension_archive, data)
            sys.stdout.write(encoded.decode('ascii'))
            return 0
        else:
            result = inspect_bytes(read_workspace(args.account_archive),
                                   read_workspace(args.extension_archive),
                                   args.account_sha256, args.extension_sha256)
        sys.stdout.write(canonical(result).decode('ascii'))
        return 0
    except (OSError, ValueError, TypeError, KeyError, RuntimeError, UnicodeError,
            RecursionError, OverflowError, zipfile.BadZipFile, EOFError,
            NotImplementedError, struct.error):
        print('code-extension: invalid, over-limit or inconsistent evidence; no receipt',
              file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
