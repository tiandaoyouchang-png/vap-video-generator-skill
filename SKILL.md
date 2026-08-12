---
name: png-to-vap-mp4
description: Convert PNG frame sequences or ordinary video into validated transparent MP4 assets for Tencent VAP or ByteDance Alpha Player. Use for PNG-to-VAP/Alpha conversion, pal8/GIF-derived transparency, dirty low-alpha edges, hidden RGB contamination, premultiplied-vs-straight alpha handling, dynamic RGB/alpha layouts, white-background removal, yuv420p/yuv444p encoding, vapc.json/MD5 generation, and output QA/troubleshooting.
---

# PNG to VAP MP4

Use `scripts/png_to_vap_mp4.py` as the single canonical execution entrypoint. Do not use or recreate the older `vap-master`, `vap-generator`, or legacy fixed-layout FFmpeg pipelines.

Install the one Python dependency when needed:

```bash
python3 -m pip install -r scripts/requirements.txt
```

## Route the request

1. Use `--target tencent-vap` for Tencent VAP / `vapc` requests.
2. Use `--target bytedance-alpha` for ByteDance Alpha Player / AlphaVideo requests.
3. For Tencent, use `--layout standard` unless the user explicitly requires alpha/mask on the left and RGB on the right; then use `--layout mask-left`.
4. Treat `--platform` as the legacy alias of `--target`, and `--mode` as the legacy alias of `--layout`.

Read `references/layouts.md` for layout semantics and `references/alpha-processing.md` before changing alpha cleanup or background removal behavior. Read `references/qa.md` when diagnosing a failed output.

## Input contract

- Accept either a directory of PNG frames or a source video file.
- Discover PNGs first, sort them naturally by numeric portions, then renumber a temporary sequence from zero. Never depend on `%03d`, zero padding, or the original starting index.
- Convert every source frame explicitly to RGBA before alpha operations. This is required for palette (`P`/`pal8`) PNGs with `tRNS` transparency.
- Reject inconsistent frame dimensions.
- Preserve the legacy 1344 -> 1334 crop only as compatibility behavior; disable it with `--no-auto-crop` or set an explicit `--crop-height`.
- Reject opaque input by default. For white-background material, use `--background-mode white-connected`; use `--allow-opaque` only when a fully opaque alpha mask is intentional.

## Alpha cleanup contract

Default to:

- `--alpha-threshold 16`: set alpha <= 16 to zero.
- Remap the remaining alpha interval back to 0..255. Disable only with `--no-alpha-remap`.
- Force RGB to pure black wherever cleaned alpha is zero.
- Use `--alpha-mode straight` by default because most VAP/Alpha shaders expect straight RGB plus a separate alpha mask.
- Use `--alpha-mode premultiplied` only when the target runtime/shader explicitly expects premultiplied RGB, or when the user prioritizes clean direct preview and accepts that runtime contract.

Do not silently switch alpha conventions. Repeated multiplication of already-premultiplied RGB darkens antialiased edges.

## Opaque white-background material

Use:

```bash
python3 scripts/png_to_vap_mp4.py \
  --input /path/to/source.mp4 \
  --output /path/to/output/video.mp4 \
  --target bytedance-alpha \
  --background-mode white-connected
```

This removes only near-white regions connected to the image border. Preserve enclosed white details such as eyes, mouths, highlights, and internal decorations. Tune `--white-threshold`, `--white-softness`, and `--white-chroma-tolerance` only when the default matte is visibly wrong.

## Dynamic layout rules

Never hard-code source or canvas dimensions.

For a source frame `W x H`:

- ByteDance Alpha Player: RGB left `[0,0,W,H]`, alpha right `[W,0,W,H]`, final canvas `2W x H`.
- Tencent `mask-left`: alpha left `[0,0,W,H]`, RGB right `[W,0,W,H]`, final canvas `2W x H`.
- Tencent `standard`: let official VapTool define the packed layout and validate its `vapc.json` against the encoded video.

When `W == H`, each half is individually 1:1, but the combined side-by-side video is 2:1. Do not describe the final canvas as “1:1”.

## Quality defaults

- Default to `25 fps` unless the user specifies another rate.
- Default FFmpeg encoding to `CRF 18`, `preset=medium`, and `yuv420p` for mobile compatibility.
- Use `--pixel-format yuv444p` only when the target player/device is known to decode H.264 High 4:4:4; validate on the real target device.
- Use `--bitrate` only for delivery constraints that require explicit rate control. Do not use old defaults such as `100 kbps`, `CRF 35`, or `ultrafast` for production transparent animation.
- Do not promise a file-size ceiling before measuring the generated file.

## Tencent dependencies

Require Java, `javac`, and VapTool only for `--target tencent-vap`.

Resolve:

- Java from `--java`, then `JAVA_HOME`, then `PATH`.
- VapTool from `--vaptool-home` or `VAPTOOL_HOME`.
- `animtool.jar`, VapTool `ffmpeg`, and `mp4edit` from the resolved VapTool directory.

Compile `VapBatch.java` into the temporary work directory, never into the Skill folder.

## Output contract

Publish the requested MP4 only after validation passes. Encode into an isolated temporary file first, then atomically replace the destination.

Always generate beside the final MP4:

- `md5.txt`: hash of the final published MP4.
- `qa.json`: structural/decode/content validation report.

For Tencent VAP also generate:

- `vapc.json`: metadata matching the final video.
- A top-level `vapc` atom for the custom `mask-left` output.

Do not generate a fake VAP `vapc.json` for ByteDance Alpha Player.

## Mandatory validation

Before publishing:

1. Probe codec, width, height, pixel format, FPS, frame count, and duration.
2. Decode the entire video with FFmpeg; any decode error fails the build.
3. Check expected dynamic dimensions and frame count.
4. For Tencent, cross-check `vapc.json` source size, video size, FPS, frame count, `aFrame`, and `rgbFrame` against the actual MP4.
5. For side-by-side layouts, inspect first/middle/last decoded frames against the cleaned source alpha.
6. Check safe transparent-background pixels for non-black RGB contamination and blue-biased dirt.
7. Generate MD5 only after the final MP4 has been published.

Preserve the work directory on failure and report its path. Do not overwrite an existing good output with a failed encode.
