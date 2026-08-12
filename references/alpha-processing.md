# Alpha processing

- Convert every source frame to RGBA before inspecting alpha. Palette PNG (`P`/`pal8`) may store transparency in `tRNS`.
- Default low-alpha cleanup: alpha <= 16 becomes 0, then remaining alpha is remapped from 17..255 to 0..255.
- Always set RGB to black where cleaned alpha is 0. This prevents hidden RGB in transparent pixels from becoming visible in side-by-side preview or after lossy compression.
- `auto` is the default: use `premultiplied` for ByteDance side-by-side output so low-alpha hidden RGB cannot appear as blue haze in direct preview; use `straight` before Tencent VapTool to avoid double premultiplication.
- `straight` keeps source RGB for nonzero alpha. Request it explicitly only when the runtime expects straight RGB.
- `premultiplied` multiplies RGB by cleaned alpha. Multiplying again in a straight-alpha shader darkens edges, so validate the runtime contract.
- `white-connected` removes only near-white pixels connected to the image boundary. `--white-softness` controls the feathered transition, while enclosed white features inside the subject remain opaque.
