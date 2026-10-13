# Round 40 mark

Built-in imagegen mode, a newly generated transparent pigment insert. The original wall is the edit target for the confined composite, not a regenerated background. No extra image is saved in the workspace. The generated PNG is taken from the tool's inline bytes, not read from an external file.

Final generation prompt:

> Use case: historical-scene. Asset type: transparent pigment insert for a prehistoric cave wall, to be placed on vacant stone while every ancestral pixel outside a small rectangle is preserved. Generate ONLY four small irregular ochre pebbles gathered together in a loose charcoal loop, representing gathering four separate checks before a journey. Horizontal composition, four lumpy yellow/red ochre pebble silhouettes with simple black burnt-stick outlines, a single uneven charcoal cord loosely encircling them. Flat primitive thumb-daubed earth pigment, sparse chipped worn strokes, Lascaux/Chauvet cave-art feel; bare transparent space shows between strokes and pebbles. No rock background, no glow, shadows or 3D effects. Transparent background. Earth pigments ONLY: red/yellow ochre, charcoal black, chalk white. No frog added: inherited Pepe on the finished wall remains unchanged. No hands or stencils. No letters, numbers, symbols, captions, signatures, logos, watermarks, border or frame. This is a small primitive painting, not a polished icon.

Placement: vacant floor stone at `(735,1140)-(900,1220)` on the 1254×1254 ancestral wall. The standard-library compositor reuses inspected helpers from `line-3/finalize-31.py` and `gathering/make_thumbnail.py` without modifying them. Low-alpha generated haze is discarded (average alpha below 165); retained pigment is mapped to charcoal, red/yellow ochre and chalk, so the original stone remains visible. Every pixel outside the rectangle is compared with the inherited image before saving. No ancestral mark lies within the chosen rectangle.

The final wall preserves inherited Pepe, mouth, heavy-lidded eyes, hands, other marks, cracks, colour, light, framing and dimensions. The insert adds no hands or stencils. Review is recorded separately after viewing the final PNG and JPEG.

