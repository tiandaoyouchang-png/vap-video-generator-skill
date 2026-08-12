---
name: png-to-vap-mp4
description: Convert PNG frame sequences or ordinary video into validated transparent MP4 assets for Tencent VAP or ByteDance Alpha Player, and install/verify/launch the Tencent VapTool dependency. Use for PNG-to-VAP/Alpha conversion, VapTool setup, pal8/GIF-derived transparency, dirty low-alpha edges, hidden RGB contamination, premultiplied-vs-straight alpha handling, dynamic RGB/alpha layouts, white-background removal, yuv420p/yuv444p encoding, vapc.json/MD5 generation, and output QA/troubleshooting.
---

# PNG to VAP MP4

Use `scripts/png_to_vap_mp4.py` as the single canonical execution entrypoint. Do not use or recreate the older `vap-master`, `vap-generator`, or legacy fixed-layout FFmpeg pipelines.

Install the Python dependency when needed:

```bash
python3 -m pip install -r scripts/requirements.txt
```

## Route the request

1. Use `--target tencent-vap` for Tencent VAP / `vapc` requests.
2. Use `--target bytedance-alpha` for ByteDance Alpha Player / AlphaVideo requests.
3. For Tencent, use `--layout standard` unless alpha/mask must be left of RGB; then use `--layout mask-left`.
4. Treat `--platform` as the legacy alias of `--target`, and `--mode` as the legacy alias of `--layout`.

Read `references/layouts.md` for layout semantics, `references/alpha-processing.md` before changing alpha cleanup/background removal, `references/qa.md` when diagnosing failed output, and `references/toolchain.md` for VapTool installation or dependency failures.

## Input contract

- Accept a PNG directory or source video.
- Discover PNGs first, natural-sort numeric portions, and renumber a temporary sequence from zero. Never depend on `%03d`, zero padding, or original start index.
- Convert every source frame explicitly to RGBA before alpha operations; this covers palette (`P`/`pal8`) PNG with `tRNS` transparency.
- Reject inconsistent dimensions.
- Preserve 1344 -> 1334 crop only as compatibility behavior; disable with `--no-auto-crop` or set `--crop-height`.
- Reject opaque input by default. For white-background material, use `--background-mode white-connected`; use `--allow-opaque` only when an opaque mask is intentional.

## Alpha cleanup contract

Default to:

- `--alpha-threshold 16`: set alpha <= 16 to zero.
- Remap remaining alpha back to 0..255; disable only with `--no-alpha-remap`.
- Force RGB to pure black wherever cleaned alpha is zero.
- Use `--alpha-mode straight` by default.
- Use `--alpha-mode premultiplied` only when the runtime/shader expects premultiplied RGB or direct-preview cleanliness is explicitly preferred.

Do not silently switch alpha conventions; multiplying already-premultiplied RGB again darkens antialiased edges.

For opaque white backgrounds, `white-connected` removes only near-white regions connected to the image border and preserves enclosed white details such as eyes, mouths, highlights, and decorations.

## Dynamic layout rules

Never hard-code source or canvas dimensions. For a cleaned source `W x H`:

- ByteDance: RGB `[0,0,W,H]`, alpha `[W,0,W,H]`, video `2W x H`.
- Tencent `mask-left`: alpha `[0,0,W,H]`, RGB `[W,0,W,H]`, video `2W x H`.
- Tencent `standard`: let official VapTool define packed layout and validate its metadata.

When `W == H`, each half is individually 1:1 but the combined video is 2:1.

## Quality defaults

- Default `25 fps`, `CRF 18`, `preset=medium`, `yuv444p` (H.264 High 4:4:4). Full-chroma sampling keeps color edges crisp; in practice `yuv420p` visibly blurs colored edges on 280px-class sprites while `yuv444p` stays sharp at nearly the same file size, and Tencent VAP / ByteDance Alpha Player SDKs decode High 4:4:4.
- Switch to `--pixel-format yuv420p` only when the target player/device is known not to support H.264 High 4:4:4 (e.g., some older mobile webview); always validate on-device.
- Use explicit `--bitrate` only for delivery constraints. Do not use legacy `100 kbps`, `CRF 35`, or `ultrafast` production defaults.
- Do not promise a file-size ceiling before measuring output.

## Tencent dependencies

Keep dependency management inside this Skill. Do not invoke a separate `vap-tool` Skill.

Verify the toolchain:

```bash
python3 scripts/vaptool.py verify
```

Install the official VapTool bundle on macOS/Windows when needed:

```bash
python3 scripts/vaptool.py install
```

Launch the GUI only when explicitly requested:

```bash
python3 scripts/vaptool.py run
```

Require Java, `javac`, and VapTool only for Tencent. Resolve Java from flags/JAVA_HOME/PATH and VapTool from `--vaptool-home` or `VAPTOOL_HOME`. Reuse an existing legacy `~/.opencode/tools/vaptool/tool2.0.6` installation when present; never hard-code user-specific paths. Keep the official VapTool wrapper for Tencent atom generation; preprocess frames with the canonical pipeline first.

## Output and validation

Encode to an isolated temporary file and publish only after QA passes; never let concurrent/failed encodes write the formal path.

Always generate beside the final MP4:

- `md5.txt`: hash of final published MP4.
- `qa.json`: structural/decode/content validation report.

For Tencent also preserve/generate `vapc.json` and required embedded `vapc` atom through VapTool.

Mandatory checks:

1. Probe codec, width, height, pixel format, FPS, frame count, duration.
2. Decode the entire video with FFmpeg.
3. Check expected dynamic dimensions and frame count.
4. For side-by-side layouts, compare first/middle/last decoded frames with cleaned source alpha.
5. Inspect safe transparent pixels for non-black/blue-biased contamination.
6. For Tencent, cross-check metadata geometry against video.
7. Generate MD5 only after final publication.

Preserve the work directory on failure and report its path. Target-player and real-device playback remain the final acceptance gate.
