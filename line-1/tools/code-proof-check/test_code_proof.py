"""Real-bytecode verification and adversarial evidence/transport regressions."""
import copy
import hashlib
import io
import json
import os
from pathlib import Path
import socket
import sys
import tempfile
import unittest
from unittest.mock import Mock, patch

import code_proof_check as tool


class EvidenceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.bundle = tool.load(tool.HERE / 'live-code.json')[1]

    def verify(self, bundle):
        return tool.verify(tool.DEMO_SNAPSHOT, tool.DEMO_PROOF, bundle)

    def test_real_code_offline(self):
        with patch.object(socket, 'socket', side_effect=AssertionError('offline')):
            result = self.verify(self.bundle)
        self.assertTrue(result['verified'])
        self.assertFalse(result['network_used'])
        self.assertEqual(result['bytecode_bytes'], 1287)
        self.assertEqual(result['proved_code_hash'],
                         '0x24e03ed7d7d3d6dc010b9a9836e419a3eb4215383b463f4e6685b4816435f16d')
        self.assertEqual(result['bytecode_sha256'],
                         hashlib.sha256(bytes.fromhex(self.bundle['result'][2:])).hexdigest())
        self.assertIn('No trusted mainnet anchor', result['evidence_limits'])
        self.assertIn('totalSupply', result['evidence_limits'])

    def test_code_mutations_rejected(self):
        code = bytearray.fromhex(self.bundle['result'][2:])
        for offset in (0, len(code)//2, len(code)-1):
            changed = bytearray(code)
            changed[offset] ^= 1
            bundle = copy.deepcopy(self.bundle)
            bundle['result'] = '0x' + changed.hex()
            with self.subTest(offset=offset), self.assertRaises(ValueError):
                self.verify(bundle)

    def test_empty_truncated_appended_or_invalid_code(self):
        for code in ('0x', self.bundle['result'][:-2], self.bundle['result']+'00',
                     '0x1', '0xzz', '', True, None, [], '0x'+'ab'*(tool.MAX_CODE+1)):
            bundle = copy.deepcopy(self.bundle)
            bundle['result'] = code
            with self.subTest(code_type=type(code)), self.assertRaises(ValueError):
                self.verify(bundle)

    def test_byte_limit_and_uppercase_hex(self):
        self.assertEqual(len(tool.code_bytes('0x'+'AB'*tool.MAX_CODE)), tool.MAX_CODE)
        bundle = copy.deepcopy(self.bundle)
        bundle['result'] = '0x'+bundle['result'][2:].upper()
        self.assertTrue(self.verify(bundle)['verified'])

    def test_sha3_is_not_ethereum_keccak(self):
        code = bytes.fromhex(self.bundle['result'][2:])
        self.assertNotEqual(hashlib.sha3_256(code).digest(), tool.account.header.keccak256(code))

    def test_all_anchor_and_schema_fields_bound(self):
        replacements = {'schema': 'unknown', 'chain_id': '0x2', 'snapshot_sha256': '',
            'account_proof_sha256': '', 'block_number': '0x1', 'block_hash': '',
            'address': tool.ZTO[:-1]+'f', 'method': 'eth_chainId',
            'captured_at': 'bad', 'endpoint': 'file:///workspace/evidence'}
        for field, value in replacements.items():
            bundle = copy.deepcopy(self.bundle)
            bundle[field] = value
            with self.subTest(field=field), self.assertRaises(ValueError):
                self.verify(bundle)

    def test_missing_and_extra_fields(self):
        for field in self.bundle:
            bundle = copy.deepcopy(self.bundle)
            del bundle[field]
            with self.subTest(field=field), self.assertRaises(ValueError):
                self.verify(bundle)
        bundle = dict(self.bundle, unexpected=True)
        with self.assertRaises(ValueError):
            self.verify(bundle)

    def test_hash_selector_is_exact_and_canonical_boolean(self):
        for selected in ('latest', self.bundle['block_number'],
                         {'blockHash': self.bundle['block_hash']},
                         {'blockHash': self.bundle['block_hash'], 'requireCanonical': 1},
                         {'blockHash': self.bundle['block_hash'], 'requireCanonical': False},
                         {'blockHash': self.bundle['block_hash'], 'requireCanonical': True, 'extra': 1},
                         {'blockHash': '0x'+'12'*32, 'requireCanonical': True}):
            bundle = copy.deepcopy(self.bundle)
            bundle['params'] = [tool.ZTO, selected]
            with self.subTest(selected=selected), self.assertRaises(ValueError):
                self.verify(bundle)

    def test_proof_bytes_binding_includes_whitespace(self):
        raw, proof = tool.load(tool.DEMO_PROOF)
        with patch.object(tool, 'load', return_value=(raw+b' ', proof)):
            with self.assertRaisesRegex(ValueError, 'different evidence bytes'):
                self.verify(self.bundle)

    def test_actual_proof_is_verified_not_just_its_digest(self):
        raw, proof = tool.load(tool.DEMO_PROOF)
        proof['proof']['codeHash'] = '0x'+hashlib.sha3_256(b'wrong').hexdigest()
        raw = json.dumps(proof).encode()
        bundle = dict(self.bundle, account_proof_sha256=hashlib.sha256(raw).hexdigest())
        with patch.object(tool, 'load', return_value=(raw, proof)):
            with self.assertRaisesRegex(ValueError, 'proved account'):
                self.verify(bundle)

    def test_demo_and_check_cli_without_network(self):
        for args in (['demo'], ['check', str(tool.DEMO_SNAPSHOT), str(tool.DEMO_PROOF),
                              str(tool.HERE / 'live-code.json')]):
            with patch.object(socket, 'socket', side_effect=AssertionError('offline')), \
                    patch.object(sys, 'argv', ['code_proof_check.py']+args), \
                    patch.object(sys, 'stdout', new_callable=io.StringIO) as output:
                self.assertEqual(tool.main(), 0)
            self.assertTrue(json.loads(output.getvalue())['verified'])

    def test_failure_emits_no_partial_json(self):
        with patch.object(sys, 'argv', ['code_proof_check.py', 'demo']), \
                patch.object(tool, 'load', side_effect=ValueError('bad')), \
                patch.object(sys, 'stdout', new_callable=io.StringIO) as output, \
                patch.object(sys, 'stderr', new_callable=io.StringIO) as error:
            self.assertEqual(tool.main(), 1)
        self.assertEqual(output.getvalue(), '')
        self.assertIn('no result emitted', error.getvalue())

    def test_strict_json_and_file_size(self):
        for raw in (b'{"x":1,"x":2}', b'{"x":NaN}', b'{"x":1e10000}',
                    b' '*(tool.MAX_FILE+1)):
            with patch.object(tool.account.seal, 'read_bytes', return_value=raw):
                with self.assertRaises(ValueError):
                    tool.load(tool.HERE / 'live-code.json')

    def test_workspace_file_guards(self):
        scratch = tool.account.seal.WORKSPACE / 'test/scratch'
        scratch.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=scratch) as directory:
            folder = Path(directory)
            (folder/'linked').symlink_to(tool.HERE/'live-code.json')
            (folder/'linked-dir').symlink_to(tool.HERE, target_is_directory=True)
            os.mkfifo(folder/'fifo')
            for path in (folder/'linked', folder/'linked-dir/live-code.json', folder/'fifo', folder):
                with self.subTest(path=path), self.assertRaises((ValueError, OSError)):
                    tool.load(path)
        with patch.object(tool.account.seal.os, 'open', side_effect=AssertionError('outside')):
            with self.assertRaises(ValueError):
                tool.load('/outside-workspace/code.json')


class CaptureTests(unittest.TestCase):
    def test_capture_only_two_bound_reads(self):
        code = tool.load(tool.HERE/'live-code.json')[1]
        reader = Mock(side_effect=['0x1', code['result']])
        result = tool.capture(tool.DEMO_SNAPSHOT, tool.DEMO_PROOF, read=reader)
        self.assertEqual(reader.call_args_list[0].args, ('eth_chainId', []))
        self.assertEqual(reader.call_args_list[1].args,
                         ('eth_getCode', [tool.ZTO, tool.selector(code['block_hash'])]))
        self.assertEqual(reader.call_count, 2)
        self.assertTrue(tool.verify(tool.DEMO_SNAPSHOT, tool.DEMO_PROOF, result)['verified'])

    def test_wrong_chain_stops_before_code(self):
        reader = Mock(return_value='0x2')
        with self.assertRaises(ValueError):
            tool.capture(tool.DEMO_SNAPSHOT, tool.DEMO_PROOF, read=reader)
        self.assertEqual(reader.call_count, 1)

    def test_wrong_bytecode_aborts_capture(self):
        reader = Mock(side_effect=['0x1', '0x'])
        with self.assertRaisesRegex(ValueError, 'code hash'):
            tool.capture(tool.DEMO_SNAPSHOT, tool.DEMO_PROOF, read=reader)

    def test_bad_evidence_aborts_before_network(self):
        reader = Mock(side_effect=AssertionError('no network'))
        with patch.object(tool.account, 'verify_bundle', side_effect=ValueError('invalid proof')):
            with self.assertRaises(ValueError):
                tool.capture(tool.DEMO_SNAPSHOT, tool.DEMO_PROOF, read=reader)
        reader.assert_not_called()

    def test_request_policy_before_transport(self):
        for method, params in [('eth_sendRawTransaction', ['0x01']), ('eth_call', []),
                               ('eth_getCode', [tool.ZTO, 'latest']), ('eth_getProof', []),
                               ('eth_chainId', [1]), ('eth_getCode', [tool.ZTO, {}])]:
            with patch.object(tool.urllib.request, 'build_opener', side_effect=AssertionError('network')):
                with self.subTest(method=method), self.assertRaises(ValueError):
                    tool.public_read(tool.rpc.DEFAULT_RPC, method, params)

    def test_transport_empty_proxies_user_agent_and_bounds(self):
        response = Mock(status=200, headers={})
        response.read.return_value = b'{"jsonrpc":"2.0","id":1,"result":"0x1"}'
        context = Mock(__enter__=Mock(return_value=response), __exit__=Mock(return_value=False))
        opener = Mock(open=Mock(return_value=context))
        with patch.object(tool.urllib.request, 'build_opener', return_value=opener) as build, \
                patch.object(tool.urllib.request, 'getproxies', side_effect=AssertionError('environment')):
            self.assertEqual(tool.public_read(tool.rpc.DEFAULT_RPC, 'eth_chainId', []), '0x1')
        self.assertEqual(build.call_args.args[0].proxies, {})
        self.assertIsInstance(build.call_args.args[1], tool.rpc.NoRedirect)
        self.assertEqual(opener.open.call_args.args[0].get_header('User-agent'), tool.USER_AGENT)
        self.assertEqual(opener.open.call_args.kwargs['timeout'], 20)
        self.assertEqual(response.read.call_args.args, (tool.MAX_FILE+1,))

    def test_malformed_rpc_responses(self):
        cases = [(302, {}, b'{}'), (200, {'Content-Encoding': 'gzip'}, b'{}'),
                 (200, {}, b'{"jsonrpc":"2.0","id":true,"result":1}'),
                 (200, {}, b'{"jsonrpc":"2.0","id":1,"error":{}}'),
                 (200, {}, b'{"jsonrpc":"2.0","id":1,"result":1,"extra":2}'),
                 (200, {}, b'{"jsonrpc":"2.0","id":1,"result":1,"result":2}'),
                 (200, {}, b'x'*(tool.MAX_FILE+1))]
        for status, headers, raw in cases:
            response = Mock(status=status, headers=headers, read=Mock(return_value=raw))
            context = Mock(__enter__=Mock(return_value=response), __exit__=Mock(return_value=False))
            with patch.object(tool.urllib.request, 'build_opener',
                              return_value=Mock(open=Mock(return_value=context))):
                with self.assertRaises((ValueError, RuntimeError)):
                    tool.public_read(tool.rpc.DEFAULT_RPC, 'eth_chainId', [])


if __name__ == '__main__':
    unittest.main()
