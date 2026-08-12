# VapTool dependency management

Use this reference when Tencent VAP generation fails because Java, VapTool, `animtool.jar`, bundled FFmpeg, or `mp4edit` is missing.

## One Skill, two responsibilities

`png-to-vap-mp4` is the only active Skill. It owns both:

1. transparent-video generation and QA (`scripts/png_to_vap_mp4.py`), and
2. Tencent VapTool dependency setup (`scripts/vaptool.py`).

Do not install or invoke the old `vap-master`, `vap-generator`, or `vap-tool` Skills.

## Verify first

```bash
python3 scripts/vaptool.py verify
```

Verification requires:

- Java runtime (`java`)
- Java compiler (`javac`), because the bundled `VapBatch.java` wrapper is compiled at runtime
- system `ffmpeg` and `ffprobe`
- VapTool `animtool.jar`
- VapTool-bundled `ffmpeg`
- VapTool `mp4edit`

The home directory resolves from `--home`, then `VAPTOOL_HOME` / `VAP_TOOL_HOME`, then the default application-data location. Existing legacy `~/.opencode/tools/vaptool/tool2.0.6` is reused when present.

## Install

On macOS or Windows, install the official Tencent VapTool 2.0.6 bundle:

```bash
python3 scripts/vaptool.py install
```

Use a local archive when automatic download is unavailable or when the runtime has no internet access:

```bash
python3 scripts/vaptool.py install --archive /path/to/vaptool.zip
```

Use `--force` only when intentionally replacing an existing installation.

Automatic installation is not assumed on Linux because Tencent's official desktop VapTool bundles are macOS/Windows-oriented. A pre-provisioned VapTool home may still be verified and used if it contains compatible binaries.

## Launch GUI

```bash
python3 scripts/vaptool.py run
```

GUI launching is only for macOS/Windows. Headless generation should use `scripts/png_to_vap_mp4.py` directly.

## Use with generation

When VapTool was installed outside `VAPTOOL_HOME`, pass the exact path:

```bash
python3 scripts/png_to_vap_mp4.py \
  --input /path/to/frames \
  --output /path/to/video.mp4 \
  --target tencent-vap \
  --vaptool-home /path/to/tool2.0.6
```

Never hard-code a user-specific Java or VapTool path into the Skill.
