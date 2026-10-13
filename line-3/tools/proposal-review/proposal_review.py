#!/usr/bin/env python3
"""Review original unsigned type-2 bytes with explicit offline context."""
import argparse
import hashlib
import json
from pathlib import Path
import sys

TOOLS = Path(__file__).resolve().parents[1]
for folder in ('gas-budget', 'fee-context', 'native-budget', 'nonce-context'):
    sys.path.insert(0, str(TOOLS / folder))
import gas_budget
import fee_context
import native_budget
import nonce_context

reader = gas_budget.reader
MAX_INPUT_CHARS = reader.MAX_JSON_CHARS


def original_bytes(text, input_format, evidence):
    """Normalize only after strict original-input validation, never a summary input."""
    if input_format == 'rlp':
        return bytes.fromhex(text.removeprefix('0x'))
    tx = evidence['transaction']
    fields = [int(tx[name]) for name in ('chainId', 'nonce', 'maxPriorityFeePerGas',
                                       'maxFeePerGas', 'gasLimit')]
    fields += [b'' if tx['to'] is None else bytes.fromhex(tx['to'][2:]),
               int(tx['value']), bytes.fromhex(tx['data'][2:]),
               [[bytes.fromhex(entry['address'][2:]),
                 [bytes.fromhex(slot[2:]) for slot in entry['storageKeys']]]
                for entry in tx['accessList']]]
    return b'\x02' + reader.D.rlp_encode(fields)


def review(text, profile, context_chain, input_format='rlp', *, base_fee=None,
           balance=None, latest_nonce=None, pending_nonce=None):
    """Join inherited diagnostics; absent context is reported, never filled in."""
    chain = fee_context.decimal(context_chain)
    if chain == 0:
        raise ValueError('context chain must be positive')
    if (latest_nonce is None) != (pending_nonce is None):
        raise ValueError('latest and pending nonce must be supplied together')
    gas = gas_budget.inspect(text, profile, input_format)
    evidence = gas['inspection']
    if int(evidence['transaction']['chainId']) != chain:
        raise ValueError('transaction chain does not match the supplied context chain')
    raw = original_bytes(text, input_format, evidence)
    envelope = '0x' + raw.hex()
    violations = list(gas['checkedViolations'])
    skipped = []
    fees = funds = nonce = None
    if base_fee is None:
        skipped.append('base-fee-coverage')
    else:
        fees = fee_context.inspect(envelope, fee_context.decimal(base_fee), chain)
        fees.pop('inspection')
        violations.extend(fees['checkedViolations'])
    if balance is None:
        skipped.append('native-balance-coverage')
    else:
        if chain != 1:
            raise ValueError('native balance review supports Ethereum chain 1 only')
        funds = native_budget.compare(envelope, balance)
        funds.pop('transaction')
        if not funds['coversMaximumEnvelope']:
            violations.append('native-balance-below-maximum-envelope')
    if latest_nonce is None:
        skipped.append('account-nonce-context')
    else:
        nonce = nonce_context.inspect(envelope, context_chain, latest_nonce, pending_nonce)
        if nonce['status'] == 'below-latest':
            violations.append('nonce-below-asserted-latest')
    violations = list(dict.fromkeys(violations))
    gas.pop('inspection')
    return {
        'schema': 'proposal-review/v1',
        'inputFormat': input_format,
        'unsignedBytesSha256': hashlib.sha256(raw).hexdigest(),
        'contextChainId': str(chain),
        'inspection': evidence,
        'gasReview': gas,
        'feeReview': fees,
        'nativeBalanceReview': funds,
        'nonceReview': nonce,
        'checkedViolations': violations,
        'passesCheckedConstraints': not violations,
        'status': ('checked-constraint-violation' if violations
                   else 'no-checked-constraint-violation'),
        'skippedContextChecks': skipped,
        'limitations': [
            'Only original unsigned type-2 RLP or a complete unsigned JSON-RPC object is accepted.',
            'Profile and chain are explicit caller choices; fork activation is not detected.',
            'Fee, balance and nonce context are unauthenticated caller assertions; no freshness or account association is established.',
            'Unsigned input has no recoverable sender; token contract state is not sender context.',
            'Pending-window competition and nonce gaps are diagnostics, not fee-replacement policy checks.',
            'Unchecked context stays null. Passing the listed constraints is not full validity, execution, inclusion or safety to sign.',
            'Fingerprint is SHA-256 of normalized unsigned bytes, not an Ethereum transaction hash; JSON spelling is not fingerprinted.',
        ],
    }


def main(argv):
    parser = argparse.ArgumentParser(description=__doc__)
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument('--demo', action='store_true')
    source.add_argument('--transaction')
    source.add_argument('--stdin', action='store_true')
    parser.add_argument('--format', choices=('rlp', 'json'), default='rlp')
    parser.add_argument('--profile', required=True, choices=gas_budget.PROFILES)
    parser.add_argument('--context-chain', required=True)
    parser.add_argument('--base-fee-wei')
    parser.add_argument('--balance-wei')
    parser.add_argument('--latest-nonce')
    parser.add_argument('--pending-nonce')
    args = parser.parse_args(argv)
    try:
        if args.demo:
            text = (json.dumps(reader.demo_object()) if args.format == 'json'
                    else reader.D.demo_transaction())
        elif args.stdin:
            text = sys.stdin.read(MAX_INPUT_CHARS + 1)
            if len(text) > MAX_INPUT_CHARS:
                raise ValueError('input exceeds 512 Ki characters')
            if args.format == 'rlp':
                text = text.removesuffix('\n').removesuffix('\r')
        else:
            text = args.transaction
        report = review(text, args.profile, args.context_chain, args.format,
                        base_fee=args.base_fee_wei, balance=args.balance_wei,
                        latest_nonce=args.latest_nonce, pending_nonce=args.pending_nonce)
    except (ValueError, UnicodeError) as error:
        print('error: ' + str(error), file=sys.stderr)
        return 2
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report['passesCheckedConstraints'] else 1


if __name__ == '__main__':
    raise SystemExit(main(sys.argv[1:]))
