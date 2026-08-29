import threading
import time

import dxcam
from PIL import Image, ImageGrab


class CaptureCoordinator:
    """Own one capture backend and share a recent full-client frame."""

    def __init__(self, performance=None, max_age_seconds=0.12):
        self.performance = performance
        self.max_age_seconds = max(0.0, float(max_age_seconds))
        self.lock = threading.RLock()
        self.cached_rect = None
        self.cached_frame = None
        self.cached_at = 0.0
        self.camera = None
        self.backend = "Desktop Duplication"
        try:
            self.camera = dxcam.create(output_color="RGB", processor_backend="numpy")
        except Exception:
            self.backend = "ImageGrab fallback"

    def capture_client(self, client_rect, max_age_seconds=None):
        rect = tuple(int(value) for value in client_rect)
        max_age = self.max_age_seconds if max_age_seconds is None else max(0.0, float(max_age_seconds))
        now = time.monotonic()
        with self.lock:
            if (
                self.cached_frame is not None
                and self.cached_rect == rect
                and now - self.cached_at <= max_age
            ):
                if self.performance is not None:
                    self.performance.record("capture_shared_hit", 0.0)
                return self.cached_frame

            started = time.perf_counter()
            cpu_started = time.process_time()
            if self.camera is not None:
                array = self.camera.grab(region=rect, new_frame_only=False)
                frame = None if array is None else Image.fromarray(array, mode="RGB")
            else:
                frame = ImageGrab.grab(bbox=rect).convert("RGB")
            if self.performance is not None:
                self.performance.record(
                    "capture_full_client",
                    time.perf_counter() - started,
                    time.process_time() - cpu_started,
                )
            if frame is not None:
                self.cached_rect = rect
                self.cached_frame = frame
                self.cached_at = time.monotonic()
            return frame

    def invalidate(self):
        with self.lock:
            self.cached_rect = None
            self.cached_frame = None
            self.cached_at = 0.0

    def close(self):
        with self.lock:
            camera, self.camera = self.camera, None
            self.invalidate()
        if camera is not None:
            try:
                camera.release()
            except Exception:
                pass
