# Output QA

A generated file is not accepted merely because it exists or has an MD5.

Required checks:
1. ffprobe width, height, pixel format, FPS, frame count, duration.
2. Full FFmpeg decode to null output.
3. For side-by-side layouts, first/middle/last frames are decoded and compared with the cleaned source alpha.
4. Safe transparent background pixels are inspected separately for non-black and blue-biased contamination; record maximum RGB and failure ratios.
5. For Tencent, `vapc.json` geometry must match the actual video geometry.
6. Publish only after QA succeeds. Encode to an isolated temporary file and atomically replace the destination.
7. Compute MD5 from the final published MP4.
8. When requesting `yuv444p`, verify both the pixel format and H.264 High 4:4:4 profile.
9. Device/runtime playback remains a required final acceptance step, especially for yuv444p/High 4:4:4.
