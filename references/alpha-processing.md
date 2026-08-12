# Alpha processing

- Convert every source frame to RGBA before inspecting alpha. Palette PNG (`P`/`pal8`) may store transparency in `tRNS`.
- Default low-alpha cleanup: alpha <= 16 becomes 0, then remaining alpha is remapped from 17..255 to 0..255.
- Always set RGB to black where cleaned alpha is 0. This prevents hidden RGB in transparent pixels from becoming visible in side-by-side preview or after lossy compression.
- `straight` keeps source RGB for nonzero alpha and is the default runtime contract.
- `premultiplied` multiplies RGB by cleaned alpha. Use only if the shader/runtime expects premultiplied input; multiplying again at runtime darkens edges.
- `white-connected` removes only near-white pixels connected to the image boundary. It intentionally preserves enclosed white features inside the subject.
