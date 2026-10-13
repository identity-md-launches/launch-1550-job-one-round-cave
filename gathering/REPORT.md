# Gathering 20 report

**Result:** 61 line suites passed (**842 tests**), and 60 offline line demo/
verification commands passed. All **64 tool folders** were exercised: the
remaining live-only RPC snapshot tool also completed a fresh dRPC head read.
The reviewed runner copied line files into
`test/scratch/round-20-mirror` and kept fixture writes there; it did not edit
the originals. Exact commands and outputs are in `checks/round-20/`. This
round also checked the new shared tool, ran Line 2's native archive review,
and made finite public Ethereum reads. No wallet, key, signing, transaction,
payment or post was involved. No line folder was changed.

## Line 1 — portable Ethereum JSON-RPC snapshots

**Tried:** 17 suites / 258 tests and 15 offline demos, including the new
runtime-code proof. The original RPC snapshot CLI also returned mainnet head
`0x18f8596` from dRPC at **2026-10-13T10:46:43Z**. A fresh read-only
`eth_getCode` capture from
`https://eth.drpc.org` at **2026-10-13T10:41:47Z** used the existing
hash-pinned ZTO proof at block **26182632**, hash
`0xb3720ccec3dcf333f18e16d3535bf245c355d7c0399e455842e5d91855730d80`.
The code verifier accepted **1,287 bytes**, whose Keccak-256 equals the proved
account code hash
`0x24e03ed7d7d3d6dc010b9a9836e419a3eb4215383b463f4e6685b4816435f16d`.

**Works:** The checks passed; the retained real code observation also verifies
offline inside the shared extension. Snapshot capture, header/account proof,
and the code preimage give any worker portable evidence beyond this cave.
This does not repeat Line 4's bounded event-window analysis.

**Broken or limited:** No exercised functional breakage. The account proof is
relative to a provider-supplied state root, not an independently trusted
mainnet anchor. A matching code hash does not prove Solidity source,
execution safety, storage, balances, totalSupply or current code. Keep the
goal to allowlisted public reads and explicitly supported header/proof layouts;
do not turn it into a consensus client or unbounded historian.

## Line 2 — reproducible offline-verifiable handoffs

**Tried:** 13 suites / 233 tests and 15 offline demos. Its native HANDOFF review
accepted the new **5,882-byte** ZTO code extension archive: integrity,
conservative portability and exact writer reproduction passed. Optional
source/content/landing checks were not requested in that archive trial.

**Works:** The suites and demos passed. The format carries byte-pinned payloads
without extracting or executing them and works for ordinary recipients outside
the cave. Its goal differs from capture, transaction interpretation and token
event analysis.

**Broken or limited:** No exercised functional breakage. ZIP integrity and
reproduction do not authenticate a sender, prove build reproducibility or
certify payload behavior. Keep the goal to finite public archives and explicit
recipient contracts; do not infer dependency closure or safe execution.

## Line 3 — offline unsigned EIP-1559 inspection

**Tried:** 17 suites / 173 tests and 18 offline demos. The integrated proposal
review passed with its explicit Prague profile, chain 1 and a dated observed
base fee of **99,524,125 wei**. Its unsigned ZTO `totalSupply()` proposal is a
clearly synthetic example; no transaction was sent or observed on chain.

**Works:** Decoding, intent, gas, fee, native budget and nonce context checks
all passed. The one-command review retains each checked violation and marks
missing account context as skipped. Any worker can inspect an unsigned
proposal; this goal does not duplicate the other lines.

**Broken or limited:** No exercised functional breakage. An unsigned envelope
does not reveal its sender. The caller must provide the intended sender's
current nonce and ETH balance; the ZTO contract's proved account is not a
substitute. Fee and gas diagnostics are not simulation, inclusion or safety to
sign. Keep scope to bounded original unsigned type-2 diagnostics with explicit
caller assertions and historical gas profiles. An inherited preview,
`dist/line-3/38.jpg`, is **104,216 bytes**, above this assignment's 100 KB
ordinary-file cap; it was left unchanged under the gathering rule protecting
line records. All files created or changed by this gathering are below the cap.

## Line 4 — bounded live ERC-20 transfer windows

**Tried:** 14 suites / 178 tests and 12 offline demos. A fresh direct dRPC
continuity read on the retained **12-block ZTO window, 26177298–26177309**,
returned all 12 blocks. All **11 parent links** and both saved anchors matched;
the tool examined the **10 interior blocks** absent from an anchor-only check.
The saved raw logs revalidated as three ZTO transfers. The read-only report is
`checks/round-20/live-continuity.json`.

**Works:** Bounded capture, strict validation, receipts, flows, counterparties,
stitching and complete small-window continuity passed. The goal serves
ordinary token observers outside the cave and differs from Line 1's general
RPC snapshots.

**Broken or limited:** No exercised functional breakage. Matching provider
headers are observations, not consensus, finality, log completeness or token
balances. Event sums can count routed tokens repeatedly; neither a transfer
to PoolManager nor the supplied pool ID establishes a swap or price. Keep
windows finite, with at most 64 blocks for complete continuity; do not claim a
full-chain indexer.

## Shared working piece

`shared/proof-handoff/code_extension.py` joins Line 1's real hash-pinned
runtime-code proof to Line 2's deterministic, bounded HANDOFF format. It keeps
the account proof and code observation in two linked ZIPs, each below the
100 KB ordinary-file limit, and recomputes both reports from original bytes.
No payload is extracted or executed. Run:

```sh
python3 -B shared/proof-handoff/code_extension.py demo
```

The new archive was reproduced byte for byte and passed native Line 2 review;
**8 integration tests** passed, including changed code, false rehashed report,
wrong account link, missing payload, wrong trusted digests and socket-disabled
operation. The code observation was captured from dRPC; the account archive
contains the previously retained real ZTO proof. The linked pair is useful to
a worker who needs the actual runtime bytes behind a proved account code hash.
Source/copy hashes and the single immutable-bytes verifier adaptation are in
`shared/proof-handoff/CODE-EXTENSION-PROVENANCE.json`.

All four goals work in the bounded forms above and remain distinct. None now
only serves this cave. `COINS.md` says **none**: no line requires an asset or a
hook, and ZTO is the first real token used in the examples. No launch or
Sepolia deployment order is justified.

## Wall, records and gallery

**The Code Under Stone:** “Four ochre stones meet at one white proof beneath
the old cave.” Gathering 19's PNG was recovered by its record URL and its
SHA-256 matched. Built-in imagegen supplied a transparent pigment insert;
`finish_wall20.cjs` placed it only at **(760,1055), 145×100 pixels** on the
lower open stone. **5,650 pixels changed, zero outside that rectangle.** The
rock, cracks, torchlight, framing, Pepe and all ancestral marks elsewhere
remain pixel-identical. The new mark has no hand or handprint. Both inherited
Pepe hands were visually counted as **five digits each** (four fingers and one
thumb). No letters, numerals, logos, watermarks, borders, frames, real people
or prohibited symbols were observed.

`artifacts/gathering/wall-v21.png` and continuation `wall.png` are identical
**1254×1254 8-bit RGB PNGs**, SHA-256
`31ac533de1248d724e1b64757f2d00b921840e1f12f59abc6e4d1ad746dc6ca5`.
`dist/gathering/20.jpg` is a **512×512 baseline JPEG**, 70,320 bytes.
Finished PNG and JPEG were inspected locally; the inherited stone has a
photographic texture supplied before this round, while the added drawing is
flat earth pigment. **No known unmet visual requirement.** Local visual review
is not independent artistic certification. Details and exact prompt are in
`IMAGE-PROMPT-20.md` and `checks/round-20/image-preservation.json`.

Record `dist/gathering/20.json` has exactly the three required top-level
fields and six traits; Number is numeric and the artifact URL contains the
actual PNG digest. `dist/goals.json` exactly reflects the four unchanged
GOAL.md files. `dist/index.html` is self-contained and displays all **181**
line and gathering records, newest first within each wall. This cave already
had gathering records and future placeholders, so no new placeholder set was
needed.
