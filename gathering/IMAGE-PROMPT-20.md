# The Code Under Stone

Built-in `image_gen.imagegen` with the Gathering 19 wall as a style and
continuity reference, transparent background enabled. Final prompt:

> Use case: illustration-story. Create an isolated prehistoric cave-pigment
> motif intended to be composited onto the lower open stone of the supplied
> cave wall. The supplied image is a STYLE REFERENCE and continuity reference:
> rough warm Lascaux-like stone painting made with charcoal black, red ochre,
> yellow ochre, chalk white, worn uneven finger and burnt-stick marks. Output
> ONLY the small pigment motif on a fully transparent background, no cave wall
> or rectangular patch. Motif: a compact charcoal oval enclosing four tiny
> red/yellow ochre pebble shapes connected by a fine branching charcoal line
> to one small chalk-white center speck. The oval and branches should feel
> hand-made, irregular, slightly faded. No frog, no hands, no handprints, no
> letters, no numbers, no logos, no caption, no signature, no border, no frame,
> no symbols beyond the pebble-and-branch motif. Keep ample transparent margin
> around it. It must read as a discreet new mark in the ancestral cave
> painting, not a polished icon.

The tool returned a 1325×1187 RGBA PNG. `finish_wall20.cjs` discarded alpha
at or below 180, area-averaged the remaining motif extent (202,260)–(1161,931)
into 145×100 pixels, mapped it to charcoal, ochre and chalk pigment, and placed
it over the preserved rock at (760,1055). The original rock remains visible
through the pigment. The generated insert at the named output path was
overwritten by the final complete wall. No extra workspace image remains.

Output: `artifacts/gathering/wall-v21.png`, identical continuation
`artifacts/gathering/wall.png`, and `dist/gathering/20.jpg`. Exact bytes,
dimensions, preservation counts and visual review are in
`checks/round-20/image-preservation.json`.
