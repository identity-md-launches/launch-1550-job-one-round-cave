"""Behavioral integration checks for the offline proposal review."""
import contextlib
import hashlib
import io
import json
from pathlib import Path
import subprocess
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent))
import proposal_review as R


def transaction(**changes):
    tx = R.reader.D.decode(R.reader.D.demo_transaction())
    tx.update(changes)
    fields = [tx[name] for name in ('chainId', 'nonce', 'maxPriorityFeePerGas',
                                  'maxFeePerGas', 'gasLimit')]
    fields += [b'' if tx['to'] is None else bytes.fromhex(tx['to'][2:]),
               tx['value'], bytes.fromhex(tx['data'][2:]),
               [[bytes.fromhex(entry['address'][2:]),
                 [bytes.fromhex(slot[2:]) for slot in entry['storageKeys']]]
                for entry in tx['accessList']]]
    return '0x02' + R.reader.D.rlp_encode(fields).hex()


class ProposalTests(unittest.TestCase):
    def review(self, tx=None, **kwargs):
        return R.review(tx or transaction(), 'prague', '1', **kwargs)

    def test_absent_context_stays_absent(self):
        report = self.review()
        self.assertTrue(report['passesCheckedConstraints'])
        self.assertEqual(report['skippedContextChecks'],
                         ['base-fee-coverage', 'native-balance-coverage', 'account-nonce-context'])
        for key in ('feeReview', 'nativeBalanceReview', 'nonceReview'):
            self.assertIsNone(report[key])
        self.assertEqual(report['inspection']['destinationLabel'], 'ZTO')
        self.assertEqual(report['gasReview']['gas']['requiredMinimumGasLimit'], '21160')

    def test_all_contexts_and_exact_large_arithmetic(self):
        # Synthetic assertions: no sender account observation is implied.
        report = self.review(transaction(nonce=2, value=2**200),
                             base_fee='1000000000', balance=str(2**200 + 200000000000000),
                             latest_nonce='1', pending_nonce='2')
        self.assertTrue(report['passesCheckedConstraints'])
        self.assertEqual(report['skippedContextChecks'], [])
        self.assertEqual(report['nativeBalanceReview']['surplusWei'], '0')
        self.assertEqual(report['nonceReview']['status'], 'at-pending-frontier')
        self.assertEqual(report['feeReview']['fees']['effectiveGasPriceWei'], '2000000000')

    def test_multiple_failures_are_all_retained(self):
        report = self.review(transaction(gasLimit=21000, maxPriorityFeePerGas=3000000000),
                             base_fee='4000000000', balance='1', latest_nonce='1', pending_nonce='1')
        self.assertEqual(report['checkedViolations'], [
            'gas-limit-below-required-minimum', 'priority-fee-exceeds-max-fee',
            'base-fee-exceeds-max-fee', 'native-balance-below-maximum-envelope',
            'nonce-below-asserted-latest'])
        self.assertFalse(report['passesCheckedConstraints'])
        self.assertIsNone(report['feeReview']['fees']['effectiveGasPriceWei'])

    def test_pending_competition_and_gap_are_diagnostics(self):
        for proposed, status in ((1, 'within-pending-window'), (4, 'above-pending-frontier')):
            report = self.review(transaction(nonce=proposed), latest_nonce='1', pending_nonce='2')
            self.assertTrue(report['passesCheckedConstraints'])
            self.assertEqual(report['nonceReview']['status'], status)

    def test_thresholds(self):
        report = self.review(transaction(gasLimit=21160), base_fee='2000000000',
                             balance=str(21160 * 2000000000))
        self.assertTrue(report['passesCheckedConstraints'])
        self.assertEqual(report['feeReview']['fees']['effectivePriorityFeePerGasWei'], '0')
        report = self.review(transaction(gasLimit=21159), base_fee='2000000001', balance='1')
        self.assertEqual(len(report['checkedViolations']), 3)

    def test_json_and_rlp_review_equivalence_with_ordered_duplicates(self):
        obj = R.reader.demo_object()
        obj['nonce'] = '0x2'
        entry = {'address': R.reader.D.ZTO, 'storageKeys': ['0x' + 'ab' * 32] * 2}
        obj['accessList'] = [entry, entry]
        text = json.dumps(obj)
        original = R.reader.inspect_json(text)['inspection']
        raw = R.original_bytes(text, 'json', original)
        context = dict(base_fee='1000000000', balance='999999999999999',
                       latest_nonce='1', pending_nonce='2')
        json_report = R.review(text, 'prague', '1', 'json', **context)
        rlp_report = self.review('0x' + raw.hex(), **context)
        self.assertEqual(json_report['inspection'], rlp_report['inspection'])
        self.assertEqual(json_report['unsignedBytesSha256'], hashlib.sha256(raw).hexdigest())
        for key in ('feeReview', 'nativeBalanceReview', 'nonceReview', 'checkedViolations'):
            self.assertEqual(json_report[key], rlp_report[key])
        self.assertEqual(json_report['gasReview']['counts']['accessStorageKeyOccurrences'], '4')
        self.assertEqual(json_report['gasReview']['counts']['uniqueAddressStorageKeyPairs'], '1')

    def test_creation_keeps_null_destination(self):
        report = self.review(transaction(to=None, data='0x1234', gasLimit=60000),
                             latest_nonce='0', pending_nonce='0')
        self.assertIsNone(report['inspection']['transaction']['to'])
        self.assertIsNone(report['nonceReview']['destination'])
        self.assertTrue(report['gasReview']['initcode']['isCreation'])

    def test_context_validation(self):
        for kwargs in ({'latest_nonce':'1'}, {'pending_nonce':'1'},
                       {'latest_nonce':'2','pending_nonce':'1'}, {'base_fee':True},
                       {'base_fee':'01'}, {'balance':'-1'}, {'balance':str(2**256)},
                       {'latest_nonce':'0','pending_nonce':str(2**256)}):
            with self.subTest(kwargs=kwargs), self.assertRaises(ValueError):
                self.review(**kwargs)
        for chain in ('0', '2', str(2**256), True):
            with self.subTest(chain=chain), self.assertRaises(ValueError):
                R.review(transaction(), 'prague', chain)

    def test_balance_is_ethereum_only(self):
        tx = transaction(chainId=8453)
        result = R.review(tx, 'london', '8453', base_fee='1')
        self.assertIsNone(result['inspection']['destinationLabel'])
        with self.assertRaises(ValueError):
            R.review(tx, 'london', '8453', balance='1')

    def test_original_input_only_and_bounds(self):
        for text in ('0x01c0', '0x02c0', transaction() + '00',
                     transaction() + ' ', 'x' * (R.MAX_INPUT_CHARS + 1),
                     transaction(maxFeePerGas=2**256)):
            with self.subTest(text=text[:40]), self.assertRaises(ValueError):
                self.review(text)
        obj = R.reader.demo_object()
        for text in (json.dumps(self.review()), json.dumps({'result':obj}),
                     json.dumps(dict(obj, **{'from':R.reader.D.ZTO})),
                     json.dumps(obj)[:-1] + ',"nonce":"0x1"}'):
            with self.assertRaises(ValueError):
                R.review(text, 'prague', '1', 'json')
        raw = bytes.fromhex(transaction()[2:])
        fields, _ = R.reader.D.rlp_item(raw, 1)
        with self.assertRaises(ValueError):
            self.review('0x02' + R.reader.D.rlp_encode(fields + [b'', b'', b'']).hex())

    def test_hex_case_is_not_a_change(self):
        tx = transaction()
        self.assertEqual(self.review(tx)['unsignedBytesSha256'],
                         self.review(tx[2:].upper())['unsignedBytesSha256'])

    def test_no_network_needed(self):
        with patch('socket.socket', side_effect=AssertionError('network forbidden')):
            self.assertTrue(self.review(base_fee='1')['passesCheckedConstraints'])

    def test_cli_exit_and_no_partial_report(self):
        command = [sys.executable, '-B', str(Path(R.__file__).resolve()),
                   '--profile', 'prague', '--context-chain', '1']
        for extras, expected in ((['--demo'], 0),
                                 (['--demo', '--base-fee-wei', '3000000000'], 1),
                                 (['--transaction', '0x02c0'], 2),
                                 (['--demo', '--latest-nonce', '1'], 2)):
            result = subprocess.run(command + extras, capture_output=True, text=True,
                                    cwd=Path(R.__file__).resolve().parent, check=False)
            self.assertEqual(result.returncode, expected, result.stderr)
            if expected == 2:
                self.assertEqual(result.stdout, '')
                self.assertNotIn('Traceback', result.stderr)
            else:
                self.assertEqual(json.loads(result.stdout)['passesCheckedConstraints'], expected == 0)

    def test_stdin_json_and_transport_newline(self):
        flags = ['--stdin', '--profile', 'prague', '--context-chain', '1']
        for fmt, text in (('rlp', transaction() + '\r\n'),
                          ('json', json.dumps(R.reader.demo_object()) + '\n')):
            output = io.StringIO()
            with patch('sys.stdin', io.StringIO(text)), contextlib.redirect_stdout(output):
                self.assertEqual(R.main(flags + ['--format', fmt]), 0)
            self.assertEqual(json.loads(output.getvalue())['inputFormat'], fmt)
        output = io.StringIO()
        with patch('sys.stdin', io.StringIO(' ' * (R.MAX_INPUT_CHARS + 1))), \
                contextlib.redirect_stdout(output), contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(R.main(flags), 2)
        self.assertEqual(output.getvalue(), '')


if __name__ == '__main__':
    unittest.main()
