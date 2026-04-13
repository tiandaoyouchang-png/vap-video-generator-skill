---
name: "vap-master"
description: "Generates Tencent VAP (Video Animation Player) MP4 files from PNG sequences. Invoke when user needs to create VAP videos from PNG frames with different layout modes."
---

# VAP Master

## Overview

VAP Master is a professional, unified CLI tool designed to streamline the generation of Tencent VAP (Video Animation Player) MP4 files from PNG sequences. It serves as a powerful wrapper around the official VapTool Java API, offering advanced features such as automatic frame normalization and custom layout post-processing.

## Key Features

- **Unified Interface**: Simplifies the VAP generation process into a single command.
- **Multiple Layout Modes**: Supports both the standard VAP layout and a specialized mask-left layout.
- **Automatic Normalization**: Automatically detects frame dimensions and crops frames from target_h + 10 height to target_h height (e.g., 1344px to 1334px) to meet specific platform requirements.
- **Dynamic Resolution**: Automatically adapts the output video resolution based on the input PNG frames (Width = FrameWidth * 2, Height = FrameHeight).
- **Advanced Post-Processing**: Handles complex region swapping and vapc atom manipulation for custom layouts.
- **Headless Execution**: Wraps the VapTool Java API for seamless integration into automated pipelines.

## Prerequisites

To use VAP Master, ensure your environment meets the following requirements:

- Java Runtime: Java 17 or higher.
- VapTool: VapTool version 2.0.6 (requires animtool.jar and mp4edit).
- FFmpeg Suite: ffmpeg and ffprobe must be installed and available in your system's PATH.

## Usage

### Standard Mode

Generates a VAP MP4 with the default layout: RGB on the left, Alpha on the right (scaled to 0.5x by default, configurable via --standard-scale).

```bash
python3 vap_master.py \
  --input /path/to/png_sequence \
  --output /path/to/output.mp4 \
  --fps 25 \
  --mode standard
```

### Mask-Left Mode

Generates a VAP MP4 with a custom layout: Alpha/Mask on the left, RGB on the right. The output resolution is automatically calculated (Total Width = FrameWidth * 2, Height = FrameHeight).

```bash
python3 vap_master.py \
  --input /path/to/png_sequence \
  --output /path/to/output.mp4 \
  --fps 25 \
  --mode mask-left
```

## CLI Arguments

| Argument | Description | Default |
|----------|-------------|---------|
| --input | Required. Path to the directory containing the PNG sequence. | N/A |
| --output | Required. Path where the final MP4 will be saved. | N/A |
| --fps | Frames per second for the output video. | 25 |
| --mode | Layout mode: standard or mask-left. | standard |
| --standard-scale | Alpha scaling factor for standard mode. | 0.5 |
| --bitrate | VapTool encoding bitrate in kbps. | 2000 |
| --swap-bitrate | Re-encoding bitrate for mask-left mode in kbps. | 3000 |
| --java | Path to the java binary. | System Default |
| --vaptool-home | Path to the VapTool home directory. | System Default |
| --keep-work | Keep the temporary working directory for debugging. | False |

## Technical Details

### Layout Specifications

#### Standard Mode:
- Left: RGB (Original size)
- Right: Alpha (Scaled by --standard-scale, default 0.5x)

#### Mask-Left Mode:
- Left: Alpha/Mask (FrameWidth x FrameHeight)
- Right: RGB (FrameWidth x FrameHeight)
- Total Resolution: (FrameWidth * 2) x FrameHeight

### Frame Normalization

The tool automatically detects dimensions from the first frame. If the raw height (raw_h) is exactly target_h + 10 (e.g., 1344px vs 1334px), it will automatically crop the frame from the top (0,0) to target_h to ensure compatibility with specific VAP requirements.

### Mask-Left Workflow

When running in mask-left mode, the tool performs the following steps:

1. **Initial Encoding**: Uses VapTool to generate a standard VAP MP4.
2. **Region Swapping**: Uses FFmpeg to re-encode the video, swapping the Alpha and RGB regions to the specified positions.
3. **Atom Manipulation**: Manually parses and updates the vapc atom within the MP4 container using mp4edit to ensure the player correctly interprets the new layout.

## Troubleshooting

- **Missing Dependencies**: Ensure ffmpeg, ffprobe, and java are correctly installed and accessible.
- **Invalid Frame Sizes**: Ensure all input PNGs have consistent dimensions. The tool supports dynamic resolution but requires uniform input frames.
- **VapTool Errors**: Check the VapTool home directory path and ensure animtool.jar is present.
- **Playback Issues**: If the video doesn't play correctly in mask-left mode, verify that the target player supports custom vapc configurations.