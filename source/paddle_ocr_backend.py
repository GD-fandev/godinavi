"""Offline PaddleOCR recognition backend powered by RapidOCR and ONNX Runtime."""

import os
from pathlib import Path

# Microsoft OpenMP otherwise keeps a large worker pool active between the
# frequent, very small OCR calls used by GodiNavi.
os.environ["OMP_NUM_THREADS"] = "1"
os.environ["OMP_WAIT_POLICY"] = "PASSIVE"

import cv2
import numpy as np
from rapidocr import EngineType, LangRec, ModelType, OCRVersion, RapidOCR
from rapidocr.inference_engine.onnxruntime.main import OrtInferSession
from v2_ocr_models import materialize_ocr_models


_original_session_options = OrtInferSession._init_sess_opts


def _low_cpu_session_options(config):
    options = _original_session_options(config)
    options.add_session_config_entry("session.intra_op.allow_spinning", "0")
    options.add_session_config_entry("session.inter_op.allow_spinning", "0")
    return options


OrtInferSession._init_sess_opts = staticmethod(_low_cpu_session_options)


class PaddleOcrBackend:
    LANGUAGES = {
        "ko": LangRec.KOREAN,
        "ja": LangRec.JAPAN,
        "en": LangRec.EN,
    }

    def __init__(self, model_root):
        self.model_root = materialize_ocr_models(model_root)
        self.engines = {}

    def get_engine(self, language_key):
        if language_key not in self.engines:
            self.engines[language_key] = RapidOCR(
                params={
                    "Global.model_root_dir": str(self.model_root),
                    "Global.use_det": False,
                    "Global.use_cls": False,
                    "Global.use_rec": True,
                    "Global.log_level": "warning",
                    "EngineConfig.onnxruntime.intra_op_num_threads": 1,
                    "EngineConfig.onnxruntime.inter_op_num_threads": 1,
                    "Rec.engine_type": EngineType.ONNXRUNTIME,
                    "Rec.lang_type": self.LANGUAGES[language_key],
                    "Rec.model_type": ModelType.MOBILE,
                    "Rec.ocr_version": OCRVersion.PPOCRV4,
                }
            )
        return self.engines[language_key]

    @staticmethod
    def tighten_text_crop(image):
        rgb = np.asarray(image.convert("RGB"), dtype=np.uint8)
        channel_min = rgb.min(axis=2)
        channel_max = rgb.max(axis=2)
        neutral_bright = (channel_min >= 115) & ((channel_max - channel_min) <= 75)
        line_rows = neutral_bright.sum(axis=1) > rgb.shape[1] * 0.45
        line_columns = neutral_bright.sum(axis=0) > rgb.shape[0] * 0.55
        neutral_bright[line_rows, :] = False
        neutral_bright[:, line_columns] = False
        component_count, labels, stats, _centroids = cv2.connectedComponentsWithStats(
            neutral_bright.astype(np.uint8), connectivity=8
        )
        filtered = np.zeros_like(neutral_bright)
        for component in range(1, component_count):
            _x, _y, width, height, area = stats[component]
            if area >= 3 and width < rgb.shape[1] * 0.8 and height < rgb.shape[0] * 0.8:
                filtered[labels == component] = True
        neutral_bright = filtered
        ys, xs = np.where(neutral_bright)
        if len(xs) < 8:
            return image.convert("RGB")
        left = max(0, int(xs.min()) - 6)
        top = max(0, int(ys.min()) - 6)
        right = min(rgb.shape[1], int(xs.max()) + 7)
        bottom = min(rgb.shape[0], int(ys.max()) + 7)
        return image.crop((left, top, right, bottom)).convert("RGB")

    @classmethod
    def to_bgr(cls, image):
        rgb = np.asarray(cls.tighten_text_crop(image), dtype=np.uint8)
        return np.ascontiguousarray(rgb[:, :, ::-1])

    def recognize(self, image, language_key):
        result = self.get_engine(language_key)(
            self.to_bgr(image),
            use_det=False,
            use_cls=False,
            use_rec=True,
        )
        if not result or not result.txts:
            return ""
        return (result.txts[0] or "").strip()

    def recognize_multilingual(self, name_image, coordinate_image):
        name_results = {
            language_key: self.recognize(name_image, language_key)
            for language_key in ("ko", "ja", "en")
        }
        coordinate_text = self.recognize(coordinate_image, "en")
        return name_results, coordinate_text

    def recognize_map_language(self, name_image, coordinate_image, language_key):
        return (
            {language_key: self.recognize(name_image, language_key)},
            self.recognize(coordinate_image, "en"),
        )

    def recognize_coordinates(self, coordinate_image):
        """Recognize only coordinates between the less frequent map-name passes."""
        return self.recognize(coordinate_image, "en")
