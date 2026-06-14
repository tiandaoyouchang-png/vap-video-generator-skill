# Contributing

Contributions are welcome through GitHub issues and pull requests.

Useful areas for contribution:

- Compatibility fixes for Tencent VAP and ByteDance Alpha Player workflows.
- Better validation for PNG sequence naming, dimensions, and alpha channels.
- More output presets for common animation delivery requirements.
- Documentation improvements, examples, and troubleshooting notes.

Before opening a pull request, please run:

```bash
python3 vap_master.py --help
```

If your change affects generated video output, include the input frame size,
platform mode, bitrate, and FFmpeg version used for validation.
