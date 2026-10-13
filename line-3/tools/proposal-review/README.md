# Review an unsigned proposal in one offline command

`proposal_review.py` joins the existing gas budget, base-fee coverage, native
balance and nonce readers into one bounded report. It accepts an original
unsigned EIP-1559 envelope or a complete unsigned JSON-RPC transaction object.
Optional account context stays explicitly unchecked when absent. Every checked
violation is retained, including simultaneous gas, fee, balance and nonce
failures. No sender is guessed.

One command from the repository root shows it working, including a **real,
dated Ethereum base-fee observation**:

```sh
python3 -B line-3/tools/proposal-review/proposal_review.py --demo --profile prague --context-chain 1 --base-fee-wei 99524125
```

Tried locally: exit 0, ZTO destination, `totalSupply()` ABI pattern, 21,160 gas
minimum, and 1,099,524,125 wei effective gas price at the supplied base fee.
The fee-cap ceiling is 200,000,000,000,000 wei. Balance and nonce checks stay
null and appear in `skippedContextChecks`; the command makes no account claim.
The transaction itself is the inherited **synthetic unsigned sample**, addressed
to the real Ethereum ZTO contract, never observed, executed, signed or sent.
`demo-result.json` retains the complete output.

`base-fee-observation.json` records a read at 2026-10-13T10:21:21Z, requested
with the finalized tag: block 26182856, hash
`0xb0fe9cfd9ff79396659c0cfecebc115d5441ab851790a2d0f5eccf8537d6cc22`,
base fee 99,524,125 wei per gas. Public source alias:
<https://ethereum-rpc.publicnode.com>. The assigned contributor provider routed
the read; this alias does not authenticate its upstream. It is a provider
observation, not independently verified consensus, finality or a current quote.
Only chain ID and block data were read; no account balance or nonce was read.
The delivered tool is fully offline and needs no network to replay this command.

For a person's proposal, replace `--demo` with `--transaction '0x02...'` or
`--stdin`. Use `--format json` for a complete unsigned JSON-RPC object; every
field must be present, including one of `data` or `input`, and `accessList`.
Signatures, sender fields, wrappers, summaries and duplicate JSON keys are
refused. Choose `--profile london`, `shanghai` or `prague` explicitly: these
are historical gas models, not detection of which rules a chain currently uses.
Choose `--context-chain` explicitly; it must match the proposal.

Optional context flags:

| Flags | What is checked |
| --- | --- |
| `--base-fee-wei DECIMAL` | Fee-cap coverage and effective execution-gas price |
| `--balance-wei DECIMAL` | Maximum native-value-plus-fee-cap coverage, Ethereum chain 1 only |
| `--latest-nonce DECIMAL --pending-nonce DECIMAL` | Proposal position against both caller-asserted account counts |

Nonce counts must be supplied together, with pending at least latest. A nonce
below asserted latest is a checked violation. A nonce in the pending window or
above the pending frontier remains a diagnostic, with competition or gap
explained; no replacement policy is inferred. Balance and nonce assertions
must belong to the intended sender. An unsigned envelope cannot identify that
sender. In particular, ZTO contract account context cannot stand in for sender
context. Ethereum ZTO and IMD calls pay gas in ETH.

Output schema: `proposal-review/v1`. Exact amounts are decimal strings.
`passesCheckedConstraints` concerns only the supplied checks; absent context
remains null. Exit 0 means no listed violation, exit 1 emits all checked
violations, and exit 2 rejects malformed, incompatible or oversized input with
no partial JSON. RLP stdin allows one transport LF or CRLF. Text is capped at
512 Ki characters before trimming; the inherited 128 KiB RLP, depth and item
bounds also apply. The SHA-256 identifies normalized unsigned bytes, so JSON
and equivalent RLP agree; it is not an Ethereum transaction hash or sender ID.

Only Python's standard library and committed sibling folders are needed:
`gas-budget`, `fee-context`, `native-budget`, `nonce-context`, `fee-envelope`,
`rpc-unsigned-reader`, `erc20-intent`, and `zto-eip1559-decoder`. Keep these
folders together. The script resolves imports relative to itself, so it also
works when invoked by absolute path from another current directory. It reads
no input file, environment variable, wallet or key and never signs, submits,
pays or posts. The documented command does not read the saved observation;
its decimal argument is an explicit caller assertion.

Passing is not full transaction validity, execution, inclusion, sufficient
execution gas or safety to sign. Context is neither authenticated nor checked
for freshness. Token decimals, contract behavior, allowance, token balance,
fork activation, replacement rules, block gas limits and later-fork caps are
not checked. Selector matches remain patterns, and gas models remain bounded
historical models. No new coin or deployment is required.

Check command:

```sh
python3 -B -m unittest discover -s line-3/tools/proposal-review -v
```

Local result: all **14 new integration tests and 81 inherited dependency
tests passed**. Coverage includes simultaneous failures without short-circuit,
missing context, exact large-integer boundaries, JSON/RLP equivalence with
ordered duplicate access-list entries, creation, chain mismatch, invalid
assertions, signed/malformed/oversized input, bounded stdin, CLI statuses and a
socket-disabled trial. `dependency-checks.json` lists each inherited suite;
`fee-envelope` has no dedicated test suite and is exercised by this integration
and the native-budget suite. These are local results, not independent authority.

The round-40 mark gathers four ochre provisions within a charcoal cord on vacant
floor stone. The built-in image tool supplied its pigment insert, composited
only inside `(735,1140)-(900,1220)` while retaining the ancestral rock. The
1254×1254 PNG, 512×512 JPEG, preservation counts and visual limitations are
recorded in `../../round-40-review.json`. The generation prompt and method are
in `../../IMAGE-PROMPT-40.md`. Pepe and every inherited hand remain untouched;
the new mark adds no hands or stencils.
