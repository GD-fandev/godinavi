"""Automatic regions from researched layout laws and native UI pixels.

All builds use the same rules. No executable inspection or game-memory access.
An obscured/unrecognizable UI pauses automatic reading, preserving manual setup.
"""
from dataclasses import dataclass, field
from threading import RLock
import time

from .geometry import observe_geometry
from .layout import regions
from .window_info import window_context, display_heights


@dataclass
class Layout:
    supported: bool = False
    rect: tuple = ()
    geometry: dict = field(default_factory=dict)
    boxes: dict = field(default_factory=dict)
    reason: str = ""

    def bbox(self, kind, include_inactive=False):
        box = self.boxes.get(kind)
        if not box or box[2] <= box[0] or box[3] <= box[1]:
            return None
        if kind == 'experience?' and not include_inactive and not self.geometry.get('status_panel_open'):
            return None
        x, y = self.rect[:2]
        return box[0]+x, box[1]+y, box[2]+x, box[3]+y


def project_geometry(rect, geometry):
    width, height = rect[2]-rect[0], rect[3]-rect[1]
    if min(width, height) <= 0 or any(abs(a-b) > 3 for a, b in
            zip((width, height), geometry['render_size'])):
        return Layout(True, tuple(rect), reason='resizing')
    return Layout(True, tuple(rect), geometry, regions((width, height), geometry['scale'], geometry))


class RegionService:
    def __init__(self, capture_provider=None):
        self._capture = capture_provider
        self._scales = {}
        self._cached_key = None
        self._cached_layout = None
        self._cached_at = 0.0
        self._lock = RLock()

    def set_capture_provider(self, capture_provider):
        with self._lock:
            self._capture = capture_provider
            self._cached_key = None
            self._cached_layout = None

    def invalidate(self):
        with self._lock:
            self._cached_key = None
            self._cached_layout = None
            self._cached_at = 0.0

    def snapshot(self, hwnd, rect):
        if not hwnd or not rect:
            return Layout(reason='no_window')
        with self._lock:
            pending = Layout(True, tuple(rect), reason='waiting_for_visible_ui')
            try:
                context = window_context(hwnd)
                if not context or context['rect'] != tuple(rect) or self._capture is None:
                    return pending
                key = (context['identity'], tuple(rect), context['monitor_height'])
                now = time.monotonic()
                if key == self._cached_key and now-self._cached_at < .10:
                    return self._cached_layout
                frame = self._capture(rect)
                if frame is None or frame.size != (rect[2]-rect[0], rect[3]-rect[1]):
                    return pending
                if window_context(hwnd) != context:
                    return pending
                previous = self._scales.get(context['identity'])
                geometry = observe_geometry(frame, context['monitor_height'], previous)
                if geometry is None:
                    geometry = observe_geometry(frame, context['monitor_height'], previous,
                                                display_heights(context['device']))
                result = project_geometry(rect, geometry) if geometry else pending
                if geometry:
                    if len(self._scales) >= 8 and context['identity'] not in self._scales:
                        self._scales.clear()
                    self._scales[context['identity']] = geometry['scale']
                self._cached_key, self._cached_layout, self._cached_at = key, result, time.monotonic()
                return result
            except (OSError, RuntimeError, ValueError):
                return pending


service = RegionService()


def durability_box(frame, layout, part):
    """Choose normal or raised LOW digits only when the native icon is visible."""
    from .icons import ICONS, similarity, icon_structure_score, icon_color_error
    template = ICONS[part]
    for icon, number in ((f'icon_low:{part}', f'durability_low:{part}'),
                         (f'icon:{part}', f'durability:{part}')):
        box = layout.boxes.get(icon)
        if not box:
            continue
        # Sprite rasterization has the same one-physical-pixel rounding as the
        # header artwork. Only validation moves; the numeric OCR ROI does not.
        for dx, dy in ((0, 0), (0, -1), (0, 1), (-1, 0), (1, 0),
                       (-1, -1), (1, -1), (-1, 1), (1, 1)):
            sample = tuple(value + (dx if i % 2 == 0 else dy) for i, value in enumerate(box))
            if sample[0] < 0 or sample[1] < 0 or sample[2] > frame.width or sample[3] > frame.height:
                continue
            score = similarity(frame, sample, template)
            structure = icon_structure_score(frame, sample, template)
            color = icon_color_error(frame, sample, template)
            if score >= .75 or (score >= .5 and structure >= .92) or (structure >= .90 and color <= .08):
                return layout.bbox(number)
    return None
