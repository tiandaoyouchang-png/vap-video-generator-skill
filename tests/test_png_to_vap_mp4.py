from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import png_to_vap_mp4 as pipeline  # noqa: E402


class AlphaProcessingTests(unittest.TestCase):
    def test_natural_sort_handles_unpadded_frames(self) -> None:
        paths = [Path("10.png"), Path("2.png"), Path("1.png")]
        self.assertEqual(
            [path.name for path in sorted(paths, key=pipeline.natural_key)],
            ["1.png", "2.png", "10.png"],
        )

    def test_low_alpha_cleanup_and_premultiply_remove_hidden_rgb(self) -> None:
        image = Image.new("RGBA", (4, 1))
        image.putdata(
            [
                (20, 40, 80, 0),
                (64, 80, 120, 8),
                (100, 120, 160, 32),
                (200, 100, 50, 255),
            ]
        )
        cleaned = pipeline.clean_rgba(image, 16, True, "premultiplied", "alpha", 245, 18, 12)
        pixels = pipeline.image_data(cleaned)
        self.assertEqual(pixels[0], (0, 0, 0, 0))
        self.assertEqual(pixels[1], (0, 0, 0, 0))
        self.assertGreater(pixels[2][3], 0)
        self.assertLess(pixels[2][2], 160)
        self.assertEqual(pixels[3], (200, 100, 50, 255))

    def test_white_connected_softness_preserves_enclosed_white(self) -> None:
        image = Image.new("RGBA", (9, 9), (255, 255, 255, 255))
        pixels = image.load()
        pixels[1, 4] = (238, 238, 238, 255)
        for y in range(3, 6):
            for x in range(3, 6):
                pixels[x, y] = (20, 20, 20, 255)
        pixels[4, 4] = (255, 255, 255, 255)

        result = pipeline.white_connected_alpha(image, 245, 18, 12)
        alpha = result.getchannel("A")
        self.assertEqual(alpha.getpixel((0, 0)), 0)
        self.assertGreater(alpha.getpixel((1, 4)), 0)
        self.assertLess(alpha.getpixel((1, 4)), 255)
        self.assertEqual(alpha.getpixel((4, 4)), 255)


@unittest.skipUnless(shutil.which("ffmpeg") and shutil.which("ffprobe"), "FFmpeg is required")
class PipelineIntegrationTests(unittest.TestCase):
    def test_yuv444_output_is_clean_and_validated(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vap_skill_test_") as temp:
            root = Path(temp)
            frames = root / "frames with spaces"
            frames.mkdir()
            for number, color in ((10, (30, 120, 220)), (1, (220, 60, 30)), (2, (60, 220, 30))):
                image = Image.new("RGBA", (16, 16), (40, 60, 140, 8))
                for y in range(5, 11):
                    for x in range(5, 11):
                        image.putpixel((x, y), (*color, 255))
                image.save(frames / f"{number}.png")

            output = root / "output with spaces" / "video.mp4"
            subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "scripts" / "png_to_vap_mp4.py"),
                    "--input",
                    str(frames),
                    "--output",
                    str(output),
                    "--target",
                    "bytedance-alpha",
                    "--fps",
                    "24",
                    "--pixel-format",
                    "yuv444p",
                    "--crf",
                    "10",
                ],
                check=True,
                capture_output=True,
                text=True,
            )

            qa = json.loads((output.parent / "qa.json").read_text(encoding="utf-8"))
            stream = qa["probe"]["streams"][0]
            self.assertTrue(qa["ok"])
            self.assertEqual(qa["expected"]["frames"], 3)
            self.assertEqual(qa["expected"]["alpha_mode"], "premultiplied")
            self.assertEqual((stream["width"], stream["height"]), (32, 16))
            self.assertEqual(stream["pix_fmt"], "yuv444p")
            self.assertIn("4:4:4", stream["profile"])
            self.assertTrue(all(sample["safe_blue_ratio"] == 0 for sample in qa["samples"]))
            self.assertTrue(all(sample["safe_nonblack_ratio"] == 0 for sample in qa["samples"]))
            self.assertTrue((output.parent / "md5.txt").is_file())


if __name__ == "__main__":
    unittest.main()
