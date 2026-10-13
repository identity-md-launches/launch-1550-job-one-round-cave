# Code proof check

Capture ZTO's runtime bytecode at a saved Ethereum block and verify it offline
against the code hash in a Merkle Patricia account proof. A recipient can now
check the actual code bytes, in addition to the account fields already supported
by `account-proof-check`. Python standard library only, with no installation.

From the repository root, run this complete offline demonstration:

```sh
python3 -B line-1/tools/code-proof-check/code_proof_check.py demo
```

It reads the retained real `live-code.json` and the ancestor's
`account-proof-check/live-zto.json` and `live-proof.json`. It recomputes the
Prague execution headers, verifies the ZTO account inclusion proof, hashes the
runtime code with Ethereum Keccak-256, and compares that hash with the proved
account's code hash. SHA-256 digests bind the exact snapshot and proof files.
The report goes to stdout; the demo opens no network connection. Exit 0 means
the bytes verify relative to the supplied root; exit 1 means invalid evidence
or failed capture, without a partial JSON report.

## What happened when tried

At **2026-10-13T10:04:02Z**, two read-only requests through the assignment's
Ethereum relay returned chain ID `0x1` and **1,287 bytes** of ZTO runtime code.
The recorded public source alias is
<https://ethereum-rpc.publicnode.com>. The relay's actual upstream identity is
not authenticated by that alias. The request used the inherited snapshot's
exact block hash, with `requireCanonical: true`; there is no fallback to a
number or to `latest`.

| Observation | Value |
| --- | --- |
| ZTO contract | `0xd782bdea4ef02a0bd391eb9089470c8080f0a68e` |
| Block | 26182473 |
| Block hash | `0x9df535d2c4325171af456d416f0f7ca969209b5c10076b4a412fd2c7e2051f5a` |
| Proved code hash | `0x24e03ed7d7d3d6dc010b9a9836e419a3eb4215383b463f4e6685b4816435f16d` |
| Runtime bytes SHA-256 | `7d6c46f53a4441c9b7d4cf3d00ff7b28bd31a84dbc9d18a8ebcce33b1e8b34fb` |
| Account proof | 10 nodes, verified against the saved state root |

The captured code matched the proved hash. The real demo also passed with
socket creation disabled. All **21 new tests** passed: changed, truncated,
appended and empty code; hash algorithm distinction; all evidence/anchor
fields; exact proof bytes; rehashed but false account claims; request selector
types; file bounds and workspace path guards; strict JSON; failure output;
two-call capture behavior; and direct, bounded RPC transport.

```sh
python3 -B -m unittest discover -s line-1/tools/code-proof-check -p 'test_*.py' -v
```

`demo-result.json` retains the verified report. `check-results.json` records
the local test outcomes. These are local checks, not independent certification.

## Check or capture another observation

Check the three existing files explicitly, offline:

```sh
python3 -B line-1/tools/code-proof-check/code_proof_check.py check line-1/tools/account-proof-check/live-zto.json line-1/tools/account-proof-check/live-proof.json line-1/tools/code-proof-check/live-code.json
```

Capture code against a compatible snapshot/proof pair, printing the new bundle
to stdout:

```sh
python3 -B line-1/tools/code-proof-check/code_proof_check.py capture line-1/tools/account-proof-check/live-zto.json line-1/tools/account-proof-check/live-proof.json --rpc https://ethereum-rpc.publicnode.com
```

Use the assigned contributor relay for `--rpc` when one is supplied. Capture
requests only `eth_chainId` and `eth_getCode` for ZTO at the proved hash. It
uses its own User-Agent, an explicit empty proxy handler, no redirects, a
20-second request timeout and a 99,000-byte response bound. Capture refuses
unsupported hash selectors or unavailable historical state; it does not
silently downgrade. Nothing is signed, sent as a transaction, or executed.

Code and proof bundle files are limited to 99,000 bytes before JSON parsing;
the reused snapshot reader is bounded at 4 MiB. Reads are confined to regular
workspace files and reject symlinks at every component. Code is limited to
24,576 bytes as this tool's resource policy. That bound is not a claim about
all Ethereum forks. Output is at most 99,000 bytes. The three retained input
files each fit the assignment's 100 KB limit.

## Meaning and limits

The result proves that these code bytes hash to the code commitment in the
ZTO account under the **supplied** state root. A fabricated, self-consistent
header and proof can still pass: this is not a trusted mainnet anchor or a
consensus/finality check. The inherited header verifier supports the 21-field
Prague layout. Canonicality in the request is a provider assertion, not an
offline consensus proof. Capture timestamps and endpoint labels are reported
metadata. `network_used: false` describes verification, not the earlier capture.

The tool does not execute bytecode, match Solidity source, resolve proxy
implementation contracts, or prove storage slots, totalSupply, holder balances,
pool liquidity, or any `eth_call` result. Matching code is not a contract safety
assessment and does not establish its present-day state.

The code hash/account relationship follows [EIP-1186](https://eips.ethereum.org/EIPS/eip-1186);
the hash selector follows [EIP-1898](https://eips.ethereum.org/EIPS/eip-1898).
The runtime imports the unchanged sibling tools `account-proof-check`,
`header-hash-check` (including its vendored Keccak), `snapshot-seal`,
`pinned-snapshot`, and `rpc-snapshot`. Keep these folders in the same layout
when copying the tool. All dependencies and demo evidence are ordinary source
files already in the repository; there are no packages or submodules.
