import math

import torch

import comfy.utils
import nodes

UPSCALE_METHODS = ["lanczos", "bicubic", "bilinear", "area", "nearest-exact"]
DIVISIBLE_BY = ["8", "16", "32", "64", "112", "128"]
ROUNDING = ["nearest", "floor (<= MP)", "ceil (>= MP)"]
FIT_MODES = ["crop (keep aspect)", "stretch"]


def target_size(width, height, megapixels, divisible_by, rounding):
    scale = math.sqrt(megapixels * 1_000_000 / (width * height))
    fn = {"nearest": round, "floor (<= MP)": math.floor, "ceil (>= MP)": math.ceil}[rounding]
    new_w = max(divisible_by, int(fn(width * scale / divisible_by)) * divisible_by)
    new_h = max(divisible_by, int(fn(height * scale / divisible_by)) * divisible_by)
    return new_w, new_h


def resize_image(image, mask, enabled, megapixels, divisible_by, upscale_method, rounding, fit_mode,
                 only_downscale=False):
    height, width = image.shape[1], image.shape[2]
    if not enabled or (only_downscale and width * height <= megapixels * 1_000_000):
        return image, width, height, mask
    if only_downscale:
        rounding = "floor (<= MP)"
    new_w, new_h = target_size(width, height, megapixels, int(divisible_by), rounding)
    if only_downscale and (new_w * new_h > megapixels * 1_000_000 or new_w > width or new_h > height):
        raise ValueError(
            "Cannot downscale this image within the MP limit with the selected divisible_by. "
            "Increase megapixels or choose a smaller divisible_by."
        )
    crop = "center" if fit_mode.startswith("crop") else "disabled"

    if (new_w, new_h) != (width, height):
        image = comfy.utils.common_upscale(image.movedim(-1, 1), new_w, new_h, upscale_method, crop).movedim(1, -1)
        image = image.clamp(0.0, 1.0)

    # LoadImage returns a 64x64 placeholder mask when there's no alpha; only resize real masks.
    if mask.shape[-2:] == (height, width):
        mask = comfy.utils.common_upscale(mask.unsqueeze(1), new_w, new_h, "bilinear", crop).squeeze(1)
    else:
        mask = torch.zeros((image.shape[0], new_h, new_w), dtype=mask.dtype, device=mask.device)

    return image, new_w, new_h, mask


def resize_inputs():
    return {
        "resize": ("BOOLEAN", {"default": True, "label_on": "resize", "label_off": "original",
                               "tooltip": "Off: outputs the image at its original size."}),
        "megapixels": ("FLOAT", {"default": 1.0, "min": 0.01, "max": 64.0, "step": 0.05,
                                 "tooltip": "Total pixel target (1.0 = 1,000,000 pixels). With only_downscale, this is a maximum."}),
        "divisible_by": (DIVISIBLE_BY, {"default": "32", "tooltip": "Width and height become multiples of this."}),
        "upscale_method": (UPSCALE_METHODS, {"default": "lanczos"}),
        "rounding": (ROUNDING, {"default": "nearest",
                                "tooltip": "nearest: closest to the MP target; floor: never above it; ceil: never below it."}),
        "fit_mode": (FIT_MODES, {"default": "crop (keep aspect)",
                                 "tooltip": "crop: center-crops the few pixels lost to rounding; stretch: slightly distorts instead."}),
    }


def resize_optional_inputs():
    return {
        "only_downscale": ("BOOLEAN", {"default": False, "label_on": "Só reduzir", "label_off": "Permitir ampliar",
                                       "tooltip": "On: keep images at or below the MP limit unchanged. Larger images are reduced using floor rounding to stay within the limit. Ignored when resize is off."}),
    }


class LoadImageResizeMP(nodes.LoadImage):
    """Load Image + resize to a megapixel target with dimensions divisible by N."""

    @classmethod
    def INPUT_TYPES(cls):
        types = super().INPUT_TYPES()
        types["required"].update(resize_inputs())
        types.setdefault("optional", {}).update(resize_optional_inputs())
        return types

    CATEGORY = "image"
    SEARCH_ALIASES = ["load resize image by megapixel", "load image resize", "load image megapixels", "resize mp", "load image divisible"]
    RETURN_TYPES = ("IMAGE", "INT", "INT", "MASK")
    RETURN_NAMES = ("IMAGE", "width", "height", "MASK")
    FUNCTION = "load_and_resize"

    def load_and_resize(self, image, resize, megapixels, divisible_by, upscale_method, rounding, fit_mode,
                        only_downscale=False):
        img, mask = self.load_image(image)
        return resize_image(img, mask, resize, megapixels, divisible_by, upscale_method, rounding, fit_mode,
                            only_downscale)

    @classmethod
    def IS_CHANGED(cls, image, **kwargs):
        return super().IS_CHANGED(image)

    @classmethod
    def VALIDATE_INPUTS(cls, image, **kwargs):
        return super().VALIDATE_INPUTS(image)


class ImageResizeMP:
    """Same resize logic for an IMAGE coming from another node."""

    @classmethod
    def INPUT_TYPES(cls):
        return {"required": {"image": ("IMAGE",), **resize_inputs()},
                "optional": {"mask": ("MASK",), **resize_optional_inputs()}}

    CATEGORY = "image/transform"
    RETURN_TYPES = ("IMAGE", "INT", "INT", "MASK")
    RETURN_NAMES = ("IMAGE", "width", "height", "MASK")
    FUNCTION = "resize"

    def resize(self, image, resize, megapixels, divisible_by, upscale_method, rounding, fit_mode, mask=None,
               only_downscale=False):
        if mask is None:
            mask = torch.zeros((image.shape[0], 64, 64), dtype=image.dtype, device=image.device)
        return resize_image(image, mask, resize, megapixels, divisible_by, upscale_method, rounding, fit_mode,
                            only_downscale)


NODE_CLASS_MAPPINGS = {
    "LoadImageResizeMP": LoadImageResizeMP,
    "ImageResizeMP": ImageResizeMP,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "LoadImageResizeMP": "Load & Resize Image by Megapixel",
    "ImageResizeMP": "Resize Image by Megapixel",
}
