# Transfer-window continuity

Check every block in a saved Ethereum ERC-20 transfer window of **1–64 blocks**.
The tool revalidates the original raw Transfer logs, reads each numbered block's
hash, parent hash and timestamp, compares every adjacent parent link, and
compares every saved boundary/event-block hash. This fills the interior-block
gap left by the existing anchor audit. ZTO is the default/demo subject; valid
IMD captures also work. Python's standard library is the only dependency.

From the repository root, one command works offline with retained real evidence:

```sh
python3 -B line-4/tools/transfer-window-continuity/continuity.py --demo
```

Tried on **2026-10-13 at 10:30:59 UTC**: a fresh direct public read from
`https://ethereum-rpc.publicnode.com` returned all 12 blocks in the retained ZTO
window **26177298–26177309**. All **11 parent links** matched, timestamps
increased, and both saved anchors matched. The tool observed the **10 interior
blocks** absent from the earlier anchor audit. The original capture contains
three transfers, all at the final block. `observations.json` retains the exact
four selected fields of each response; `live-report.json` retains the resulting
report and evidence. This live run refreshed block observations, not token logs.

For an existing small capture, explicitly request a new read:

```sh
python3 -B line-4/tools/transfer-window-continuity/continuity.py --capture line-4/tools/transfer-crosscheck/publicnode.json --live
```

`--rpc https://eth.drpc.org` selects another public provider. The inherited
transport uses a dedicated User-Agent, disables proxy discovery and redirects,
and permits only public read methods. This tool calls `eth_chainId` once and
`eth_getBlockByNumber` once per block (at most 65 requests), without retries,
polling, wallets, keys, environment lookup, signing or transaction submission.
An RPC failure aborts without a partial JSON report. It never creates files;
JSON goes to stdout, and diagnostics go to stderr.

Replay the saved block observations against the original capture:

```sh
python3 -B line-4/tools/transfer-window-continuity/continuity.py --capture line-4/tools/transfer-crosscheck/publicnode.json --evidence line-4/tools/transfer-window-continuity/observations.json
```

To replay your own live result, retain its `evidence` object as an observations
JSON file and keep the original capture. `--evidence` expects that object, not
the whole report. All paths must be regular workspace files without symlinks
or `..` traversal. Capture input is limited to 16 MiB; evidence to 99,000 bytes.
Both use strict UTF-8 JSON, reject duplicate keys and non-finite numbers, and
cap nesting at 64. Keep the sibling `transfer-anchor-audit`,
`transfer-transaction-groups`, `transfer-crosscheck`, `erc20-transfer-window`,
`strict-rpc-json` and `bounded-capture-reader` folders with this tool. File
confinement requires POSIX no-follow support.

Exit codes are **0** for consistent observations, **1** for conflicting or
unavailable observations, and **2** for invalid input or a failed read.
Missing blocks stay null; affected links are unavailable. Conflicts take
precedence in the overall status, while missing-block counts remain visible.
Each block and link has its own verdict. Single-block windows check the saved
anchor and have no internal parent link. Timestamps and elapsed seconds are
exact decimal strings; no floating-point arithmetic is used.

The check compares **provider-reported fields**. It does not recompute header
hashes or authenticate consensus, finality, event inclusion or complete logs.
Sequential reads are not an atomic snapshot. A conflict alone does not prove
a reorganization. The first block's parent is outside the window. An empty
transfer capture still gets a full block check; matching links cannot establish
absence of events. Neither transfer sums nor these headers establish token
balances, trade volume, prices or activity in the particular ZTO/IMD v4 pool.

All 23 focused tests passed, including a socket-disabled real-evidence demo,
null blocks, conflicting anchors and parent links, non-increasing timestamps,
single-block windows, bounds before network I/O, strict schema/type rejection,
exact read calls and CLI status behavior. Synthetic mutations appear only in
tests, never in the retained observation files. The 18 anchor-audit and 15
transaction-group regression tests also passed (56 tests across three suites).

```sh
python3 -B line-4/tools/transfer-window-continuity/test_continuity.py
```
