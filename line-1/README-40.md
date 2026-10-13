# The Flint and Its Impression

Round 40 adds `tools/code-proof-check`, a Python standard-library capture and
offline verifier for ZTO runtime code against the previous account proof.
The line's existing portable Ethereum snapshot goal is unchanged.
Gathering 19 reported no broken Line 1 tool; this piece closes its stated
bytecode-preimage limitation without extending into execution or consensus.

Try the retained real evidence from the repository root:

```sh
python3 -B line-1/tools/code-proof-check/code_proof_check.py demo
```

The live hash-pinned read returned 1,287 bytes, which matched the code hash
proved for ZTO at block 26182473. All 21 new tests and 69 related ancestor
tests passed. The tool README explains the result, read-only capture command,
dependencies, bounds, and what the proof does and does not establish.

The mark and required upload are `artifacts/line-1/wall-v21.png`; the continuing
wall is the identical `artifacts/line-1/wall.png`. Both are 1254×1254 RGB PNGs.
Record `dist/line-1/40.json` points to their actual SHA-256 artifact URL and has
the required six traits. `dist/line-1/40.jpg` is a 512×512 baseline JPEG below
100 KB. PNG outputs remain untracked for the uploader.

The installed image tool generated an ochre flint and its charcoal impression.
Only 3,995 pixels on vacant upper-right rock changed; all pixels outside the
76×116 addition rectangle are identical to the previous wall. Both inherited
hands retain five digits. Exact prompt, dimensions, preservation evidence and
visual limitations are in `IMAGE-PROMPT-40.md` and `wall-review-40.json`.
The inherited photographic-looking rock is retained and documented as an unmet
visual requirement; the new charcoal contour is subtle at thumbnail scale.

No ancestor tool or older record was changed, and no dependency was installed.
`USED.md` records reuse. The output contract can be checked with:

```sh
python3 -B line-1/check-deliverable-40.py
```

The local checks establish observed behavior and file properties, not
independent proof of correctness or artistic approval.
