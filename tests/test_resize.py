"""Behavior tests against the real ComfyUI CPU image loader and resize."""

import importlib.util
import os
from pathlib import Path
import sys
import tempfile
import unittest

import numpy as np
from PIL import Image
import torch

# ComfyUI parses argv during import; force this isolated test process to CPU.
test_argv = sys.argv
sys.argv = [sys.argv[0], "--cpu"]
import folder_paths
import nodes
sys.argv = test_argv

spec = importlib.util.spec_from_file_location("resize_mp_under_test", Path(__file__).resolve().parents[1] / "__init__.py")
resize_mp = importlib.util.module_from_spec(spec)
spec.loader.exec_module(resize_mp)
torch.set_num_threads(2)


class ResizeTests(unittest.TestCase):
    def image(self, width, height, batch=1):
        return torch.full((batch, height, width, 3), 0.25)

    def resize(self, image, mask=None, **overrides):
        params = dict(resize=True, megapixels=1.0, divisible_by="32", upscale_method="lanczos",
                      rounding="nearest", fit_mode="crop (keep aspect)", only_downscale=True)
        params.update(overrides)
        return resize_mp.ImageResizeMP().resize(image, mask=mask, **params)

    def test_small_image_is_unchanged(self):
        image = self.image(640, 640)
        mask = torch.rand((1, 640, 640))
        output, width, height, output_mask = self.resize(image, mask)
        self.assertIs(output, image)
        self.assertIs(output_mask, mask)
        self.assertEqual((width, height), (640, 640))

    def test_exact_limit_keeps_non_multiple_dimensions(self):
        image = self.image(1000, 1000)
        output, width, height, _ = self.resize(image)
        self.assertIs(output, image)
        self.assertEqual((width, height), (1000, 1000))

    def test_below_limit_does_not_snap_dimensions(self):
        image = self.image(641, 639)
        output, width, height, _ = self.resize(image, divisible_by="128")
        self.assertIs(output, image)
        self.assertEqual((width, height), (641, 639))

    def test_large_square_is_reduced_with_strict_cap(self):
        output, width, height, mask = self.resize(self.image(2048, 2048))
        self.assertEqual((width, height), (992, 992))
        self.assertEqual(tuple(output.shape), (1, 992, 992, 3))
        self.assertEqual(tuple(mask.shape), (1, 992, 992))
        self.assertLessEqual(width * height, 1_000_000)

    def test_1024_square_is_above_decimal_megapixel(self):
        _, width, height, _ = self.resize(self.image(1024, 1024))
        self.assertEqual((width, height), (992, 992))

    def test_selected_rounding_cannot_exceed_cap(self):
        for rounding in resize_mp.ROUNDING:
            with self.subTest(rounding=rounding):
                _, width, height, _ = self.resize(self.image(1024, 1024), rounding=rounding)
                self.assertEqual((width, height), (992, 992))

    def test_other_limits_and_divisors(self):
        image = self.image(640, 640)
        for megapixels in (0.01, 0.05, 0.25, 0.5, 2.0, 64.0):
            for divisor in ("8", "16", "32", "64"):
                with self.subTest(megapixels=megapixels, divisor=divisor):
                    output, width, height, _ = self.resize(image, megapixels=megapixels, divisible_by=divisor)
                    self.assertLessEqual(width * height, megapixels * 1_000_000)
                    self.assertLessEqual(width, 640)
                    self.assertLessEqual(height, 640)
                    if 640 * 640 <= megapixels * 1_000_000:
                        self.assertIs(output, image)
                    else:
                        self.assertEqual(width % int(divisor), 0)
                        self.assertEqual(height % int(divisor), 0)

    def test_rectangular_image_and_mask_stay_aligned(self):
        image = self.image(1920, 1080)
        mask = torch.zeros((1, 1080, 1920))
        mask[:, :, 960:] = 1.0
        image[:, :, 960:, :] = 0.75
        for fit_mode in resize_mp.FIT_MODES:
            with self.subTest(fit_mode=fit_mode):
                output, width, height, output_mask = self.resize(image, mask, fit_mode=fit_mode)
                self.assertEqual((width, height), (1312, 736))
                self.assertEqual(tuple(output_mask.shape), (1, height, width))
                self.assertLessEqual(width * height, 1_000_000)
                self.assertLess(abs(width / height - 1920 / 1080), 0.02)
                self.assertTrue(torch.all(output_mask[:, :, :width // 4] == 0))
                self.assertTrue(torch.all(output_mask[:, :, 3 * width // 4:] == 1))
                self.assertAlmostEqual(float(output[0, height // 2, width // 4, 0]), 0.25, places=2)
                self.assertAlmostEqual(float(output[0, height // 2, 3 * width // 4, 0]), 0.75, places=2)

    def test_all_interpolation_methods_and_batches(self):
        for method in resize_mp.UPSCALE_METHODS:
            with self.subTest(method=method):
                output, width, height, mask = self.resize(self.image(512, 256, batch=2),
                                                         megapixels=0.05, upscale_method=method)
                self.assertEqual((width, height), (288, 128))
                self.assertEqual(tuple(output.shape), (2, height, width, 3))
                self.assertEqual(tuple(mask.shape), (2, height, width))

    def test_resize_off_takes_precedence(self):
        image = self.image(640, 640)
        mask = torch.zeros((1, 64, 64))
        output, width, height, output_mask = self.resize(image, mask, resize=False, megapixels=0.01)
        self.assertIs(output, image)
        self.assertIs(output_mask, mask)
        self.assertEqual((width, height), (640, 640))

    def test_old_api_call_still_enlarges(self):
        image = self.image(640, 640)
        mask = torch.zeros((1, 640, 640))
        # Old positional arguments, including the optional mask, retain their meaning.
        output, width, height, output_mask = resize_mp.ImageResizeMP().resize(
            image, True, 1.0, "32", "lanczos", "ceil (>= MP)", "stretch", mask)
        self.assertEqual((width, height), (1024, 1024))
        self.assertEqual(tuple(output.shape), (1, 1024, 1024, 3))
        self.assertEqual(tuple(output_mask.shape), (1, 1024, 1024))

    def test_new_input_is_optional_and_defaults_to_false(self):
        for cls in (resize_mp.LoadImageResizeMP, resize_mp.ImageResizeMP):
            schema = cls.INPUT_TYPES()
            self.assertNotIn("only_downscale", schema["required"])
            self.assertFalse(schema["optional"]["only_downscale"][1]["default"])
            self.assertEqual(list(schema["required"])[-6:], list(resize_mp.resize_inputs()))
            self.assertEqual(list(schema["optional"])[-1], "only_downscale")

    def test_incompatible_limit_and_multiple_raise_clear_error(self):
        with self.assertRaisesRegex(ValueError, "Increase megapixels or choose a smaller divisible_by"):
            self.resize(self.image(640, 640), megapixels=0.01, divisible_by="128")

    def test_narrow_image_never_grows_one_dimension(self):
        with self.assertRaisesRegex(ValueError, "Cannot downscale"):
            self.resize(self.image(16, 1000), megapixels=0.01)

    def test_native_loader_preserves_rgba_below_cap_and_old_call(self):
        old_input = folder_paths.get_input_directory()
        try:
            with tempfile.TemporaryDirectory() as input_dir:
                folder_paths.set_input_directory(input_dir)
                pixels = np.zeros((127, 255, 4), dtype=np.uint8)
                pixels[:, :, :3] = 128
                pixels[:, 128:, 3] = 255
                Image.fromarray(pixels).save(os.path.join(input_dir, "alpha.png"))
                original_image, original_mask = nodes.LoadImage().load_image("alpha.png")
                output, width, height, mask = resize_mp.LoadImageResizeMP().load_and_resize(
                    "alpha.png", True, 1.0, "32", "lanczos", "nearest", "stretch", only_downscale=True)
                self.assertEqual((width, height), (255, 127))
                self.assertTrue(torch.equal(output, original_image))
                self.assertTrue(torch.equal(mask, original_mask))
                _, width, height, _ = resize_mp.LoadImageResizeMP().load_and_resize(
                    "alpha.png", True, 1.0, "32", "lanczos", "nearest", "stretch")
                self.assertGreater(width * height, 255 * 127)
        finally:
            folder_paths.set_input_directory(old_input)


if __name__ == "__main__":
    unittest.main(verbosity=2)
