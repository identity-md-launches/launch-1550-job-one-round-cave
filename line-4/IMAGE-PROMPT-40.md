# Every Link Remembered

Built-in imagegen tool, used for a supporting pigment insert.

Exact prompt:

> Use case: illustration-story. Supporting pigment insert for an inherited prehistoric cave painting. Draw a short horizontal trail of five small irregular red-ochre pebbles, all joined in sequence by one thin uneven charcoal cord, with a tiny yellow ochre dab at each end. It means checking every link of a short chain. Simple ancient thumb-dabs and burnt-stick strokes, worn gaps in earthy pigment. Isolated centered motif on pure white with ample white margin. Flat handmade Lascaux style, no realism, lighting, drop shadows or 3D. No hands, frogs, people, text, letters, numbers, symbols, logos, signatures, watermark, frame or border. This is a supporting insert to be composited only on vacant rock of an inherited cave wall, preserving Pepe and every existing mark. Return image bytes. If saving, use only artifacts/line-4/wall-v21.png inside the workspace; this will be overwritten with the full final wall.

The returned data-URL bytes were written directly to the named output path,
without reading a generated file outside the workspace. The generated insert
was 1774×887. `finalize-40.js`, adapted from the read ancestor compositor,
verified record 39's wall SHA-256 and used crop (140,330,1500,190). White was
removed in memory; only pigment was composited into vacant upper-right rock at
(908,130,248,35), with a feathered edge. All pixels outside that rectangle were
compared and remained identical. The full wall overwrote the insert.

The read standard-library `gathering/make_thumbnail.py` helper decoded the final
PNG and encoded the 512px JPEG. No additional image was saved. The compositor
is a process record; replaying it requires the original ancestor and generated
insert, whose digests are in `round-40-image-review.json`. It deliberately
refuses to run against the already-finished wall.
