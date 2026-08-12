# PNG to VAP MP4

Single canonical Skill for transparent-video generation and Tencent VapTool dependency management.

This repository replaces the overlapping `vap-master`, `vap-generator`, legacy `vap-video-generator-skill`, and standalone `vap-tool` Skill entrypoints.

## Canonical commands

Install Python dependency:

```bash
python3 -m pip install -r scripts/requirements.txt
```

Verify Tencent VapTool dependencies:

```bash
python3 scripts/vaptool.py verify
```

Install official VapTool 2.0.6 on macOS/Windows when needed:

```bash
python3 scripts/vaptool.py install
```

Generate ByteDance Alpha Player video:

```bash
python3 scripts/png_to_vap_mp4.py \
  --input ./frames \
  --output ./output/video.mp4 \
  --target bytedance-alpha
```

Generate Tencent VAP:

```bash
python3 scripts/png_to_vap_mp4.py \
  --input ./frames \
  --output ./output/video.mp4 \
  --target tencent-vap \
  --layout standard
```

## What is unified here

- natural numeric PNG ordering (`1.png`, `2.png`, `10.png`)
- explicit RGBA conversion including palette/pal8 transparency
- low-alpha cleanup and alpha remapping
- hidden RGB cleanup in fully transparent pixels
- explicit straight/premultiplied alpha contract
- connected-white background removal that preserves enclosed white details
- dynamic layouts derived from source `W x H`
- yuv420p mobile-compatible default and optional yuv444p
- isolated temporary encoding plus atomic publication
- ffprobe metadata checks and full decode validation
- sampled alpha/background contamination QA
- final-file MD5 and `qa.json`
- Tencent official VapTool `vapc` atom path
- VapTool install / verify / GUI launch inside the same Skill

For a `280x280` source in a side-by-side layout, the final video is `560x280`: each half is 1:1, while the combined canvas is 2:1.

## Legacy compatibility

`--platform` remains an alias for `--target`, and `--mode` remains an alias for `--layout` during migration. The root `vap_master.py` compatibility wrapper remains temporarily, but new workflows should call `scripts/png_to_vap_mp4.py` directly.

The standalone `vap-master` and `opencode-skill-vap-tool` repositories are deprecated migration stubs and are no longer independent Skill entrypoints.

See `SKILL.md` and `references/` for the processing, alpha, QA, layout, and toolchain contracts.
