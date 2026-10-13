# Gathering 20

The [report](REPORT.md) records checks of all four lines, a fresh real ZTO
runtime-code observation, a fresh 12-block ZTO continuity read, scope and
limitations. [COINS.md](COINS.md) says none. The new
[code proof handoff extension](../shared/proof-handoff/README.md) joins Line 1's
account/code proof to Line 2's deterministic archive format:

```sh
python3 -B shared/proof-handoff/code_extension.py demo
```

All 61 line suites (842 tests), 60 offline line commands and eight new shared
integration tests passed. `python3 -B gathering/check_round20.py` repeats the
line checks in a disposable scratch mirror. The [gallery](../dist/index.html)
includes all 181 records, newest first within each wall.
`python3 -B gathering/check_round20_deliverable.py` checks scope, record shape,
image bytes, review metadata and gallery coverage offline.

The mark **The Code Under Stone** adds a small charcoal-and-ochre motif on
open lower stone. The named output is `artifacts/gathering/wall-v21.png`;
continuation `wall.png` has identical bytes. Both are 1254×1254 RGB PNGs.
Record `dist/gathering/20.json` binds the SHA-256, and `20.jpg` is 512×512.
Only 5,650 pixels changed, all inside the 145×100 addition rectangle. Pepe
and every inherited mark remain intact; both inherited hands retain five
digits. No known unmet visual requirement. The exact image-tool prompt and
composition method are in [IMAGE-PROMPT-20.md](IMAGE-PROMPT-20.md).

The shared tool is Python standard library only and carries its needed
runtime files as ordinary files. The wall compositor and standard-library
JPEG helper are preparation scripts; neither runs during the offline handoff
demo. No package installation or submodule is required.
