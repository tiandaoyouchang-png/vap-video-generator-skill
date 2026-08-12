# PNG to VAP MP4

Canonical transparent-video pipeline for Tencent VAP and ByteDance Alpha Player.

## What changed

This repository now exposes one generation workflow: `scripts/png_to_vap_mp4.py`. Older `vap-generator` / `vap-master` skill entrypoints are deprecated to avoid conflicting parameter names and fixed-layout implementations.

Key behavior:

- natural numeric PNG ordering (`1.png`, `2.png`, `10.png`)
- explicit RGBA conversion, including palette/pal8 PNG transparency
- low-alpha cleanup and optional alpha remapping
- hidden RGB cleanup in fully transparent pixels
- explicit `straight` vs `premultiplied` alpha contract
- dynamic `2W x H` side-by-side layouts
- connected-white background removal that preserves enclosed white details
- `yuv420p` mobile-compatible default and optional `yuv444p`
- isolated temporary encoding + atomic publication
- ffprobe metadata checks, full decode validation, sampled alpha/background QA
- final-file MD5 and `qa.json`
- Tencent official VapTool path retained for `vapc` atom generation

## Install

```bash
python3 -m pip install -r scripts/requirements.txt
```

Requires FFmpeg and ffprobe. Tencent output additionally requires Java/JDK and VapTool.

## ByteDance Alpha Player

```bash
python3 scripts/png_to_vap_mp4.py \
  --input ./frames \
  --output ./output/video.mp4 \
  --target bytedance-alpha \
  --fps 25
```

For a `280x280` source, the output is `560x280`: RGB is the left `280x280` half and alpha is the right `280x280` half.

## Low-alpha cleanup / premultiplied RGB

```bash
python3 scripts/png_to_vap_mp4.py \
  --input ./frames \
  --output ./output/video.mp4 \
  --target bytedance-alpha \
  --alpha-threshold 16 \
  --alpha-mode premultiplied
```

Use premultiplied mode only when the target shader/runtime expects it. Straight alpha remains the default.

## White-background source

```bash
python3 scripts/png_to_vap_mp4.py \
  --input ./source.mp4 \
  --output ./output/video.mp4 \
  --target bytedance-alpha \
  --background-mode white-connected
```

This removes only near-white background connected to the frame boundary; enclosed white eyes/highlights remain part of the subject.

## High-quality 4:4:4

```bash
python3 scripts/png_to_vap_mp4.py \
  --input ./frames \
  --output ./output/video.mp4 \
  --target bytedance-alpha \
  --pixel-format yuv444p \
  --crf 18
```

H.264 High 4:4:4 is not universally hardware-decodable. Validate on the target player and real device.

## Tencent VAP

```bash
python3 scripts/png_to_vap_mp4.py \
  --input ./frames \
  --output ./output/video.mp4 \
  --target tencent-vap \
  --layout standard \
  --vaptool-home /path/to/vaptool
```

Use `--layout mask-left` only when alpha must be on the left. Tencent generation keeps the official VapTool path so `vapc.json` and the embedded `vapc` atom remain player-compatible.

## Output QA

A successful run publishes the final MP4 only after validation and writes:

- `md5.txt` — MD5 of the final MP4
- `qa.json` — dimensions/FPS/frame-count/decode/content checks
- `vapc.json` — Tencent outputs only

See `SKILL.md` and `references/` for the full processing contract.
