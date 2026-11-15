"""Reproduce the researched client layout using window dimensions and pixels only.

No process handles, executable parsing, hashes, or game-memory reads. Window and
monitor dimensions are physical pixels. Sprite matches validate the formula's
scale; they never supply per-field OCR coordinates.
"""
from functools import lru_cache
from pathlib import Path
import math
import struct

import cv2
import numpy as np
from PIL import Image
from .layout import logical_size

ASSETS = Path(__file__).parent / 'assets'


def float32(value):
    return struct.unpack('<f', struct.pack('<f', value))[0]


def default_scale(monitor_height):
    # Client's monitor-height rule and the researched UIScale default (1.1).
    return float32(float32(max(1.0, monitor_height / 1080.0)) * float32(1.1))


def geometry_for_size(size, scale):
    if not math.isfinite(scale) or not .25 <= scale <= 16 or min(size) < 4:
        raise ValueError('Invalid UI geometry')
    render = tuple(max(4, int(v) & ~3) for v in size)
    scale = float32(scale)
    return dict(source='client layout formula + native UI pixels', verified=True,
                scale=scale, render_size=render, logical_size=logical_size(render, scale),
                status_panel_open=False)


@lru_cache(maxsize=3)
def sprite(index):
    return np.asarray(Image.open(ASSETS / f'playmenu8x6_{index}.png').convert('RGBA'))


def sprite_error(frame, geometry, index, origin, areas):
    """Compare only immutable native UI artwork, excluding all live text."""
    original = sprite(index)
    rh, rw = original.shape[:2]
    sx = geometry['scale'] * frame.width / geometry['render_size'][0]
    sy = geometry['scale'] * frame.height / geometry['render_size'][1]
    left, top = math.floor(origin[0]*sx), math.floor(origin[1]*sy)
    right, bottom = math.ceil((origin[0]+rw)*sx), math.ceil((origin[1]+rh)*sy)
    if left < 0 or top < 0 or right > frame.width or bottom > frame.height:
        return 1.0
    sample = np.asarray(frame.crop((left,top,right,bottom)).convert('RGB'), dtype=np.float32)
    mask = np.zeros((rh,rw),np.uint8)
    for x1,y1,x2,y2 in areas:
        mask[y1:y2,x1:x2] = 1
    mask &= (original[:,:,3] >= 240).astype(np.uint8)
    source_mask = mask
    mask = cv2.resize(source_mask,(right-left,bottom-top),interpolation=cv2.INTER_NEAREST).astype(bool)
    if np.count_nonzero(mask) < 8:
        return 1.0
    expected = [cv2.resize(original[:,:,:3], (right-left,bottom-top), interpolation=method).astype(np.float32)[mask]
                for method in (cv2.INTER_LINEAR, cv2.INTER_NEAREST)]
    # Native sprite rasterization and client-size alignment can differ by one
    # physical pixel after resize. This tolerance validates art only; the OCR
    # rectangles still come exclusively from the researched layout formula.
    errors = []
    for dx in (-1, 0, 1):
        for dy in (-1, 0, 1):
            box = (left+dx, top+dy, right+dx, bottom+dy)
            if box[0] < 0 or box[1] < 0 or box[2] > frame.width or box[3] > frame.height:
                continue
            sample = np.asarray(frame.crop(box).convert("RGB"), dtype=np.float32)[mask]
            errors.extend(float(np.mean(np.abs(sample-template))/255) for template in expected)
    best = min(errors, default=1.0)
    if best <= .08:
        return best
    # A sprite's rasterized extent is rounded independently from its origin.
    # ceil(origin + extent) - floor(origin) can be 1–2 pixels wider than
    # floor/ceil(extent), particularly with a fractional client presentation
    # size. Validate those native extents too, without moving OCR rectangles.
    sizes = {(w, h) for w in (math.floor(rw*sx), math.ceil(rw*sx))
             for h in (math.floor(rh*sy), math.ceil(rh*sy))}
    sizes.discard((right-left, bottom-top))
    for width, height in sizes:
        if min(width, height) < 1:
            continue
        extent_mask = cv2.resize(source_mask, (width, height), interpolation=cv2.INTER_NEAREST).astype(bool)
        if np.count_nonzero(extent_mask) < 8:
            continue
        templates = [cv2.resize(original[:,:,:3], (width, height), interpolation=method).astype(np.float32)[extent_mask]
                     for method in (cv2.INTER_LINEAR, cv2.INTER_NEAREST)]
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                box = (left+dx, top+dy, left+dx+width, top+dy+height)
                if box[0] < 0 or box[1] < 0 or box[2] > frame.width or box[3] > frame.height:
                    continue
                sample = np.asarray(frame.crop(box).convert('RGB'), dtype=np.float32)[extent_mask]
                best = min(best, *(float(np.mean(np.abs(sample-template))/255) for template in templates))
    return best



def header_errors(frame, geometry):
    # Frame 210 at (58,1), frame 69 at (58,23), native sprite pivots are zero.
    # Exclude the text interiors; require both separately anchored frames.
    return tuple(sprite_error(frame, geometry, index, origin,
        ((0,0,width,2),(0,20,width,22),(0,0,2,22),(width-2,0,width,22)))
        for index,origin,width in ((210,(58,1),262),(69,(58,23),71)))


def status_panel_visible(frame, geometry):
    w,h = geometry['logical_size']
    origin = (int((w-800)/2)+175,h-102)
    # Frame 14 is the character panel. The portrait separates it from other
    # tabs sharing its ornamented border; neither area contains runtime text.
    portrait = sprite_error(frame,geometry,14,origin,((24,3,54,32),))
    border = sprite_error(frame,geometry,14,origin,((0,0,14,82),(436,0,450,82)))
    return portrait <= .10 and border <= .13


def observe_geometry(frame, monitor_height, previous_scale=None, candidate_heights=()):
    candidates = []
    for scale in (previous_scale,default_scale(monitor_height)):
        if scale is not None and scale not in candidates:
            candidates.append(scale)
    for scale in candidates:
        geometry = geometry_for_size(frame.size,scale)
        errors = header_errors(frame,geometry)
        panel_open = status_panel_visible(frame,geometry)
        if (max(errors) <= .16 and sum(errors) <= .23) or panel_open:
            geometry['status_panel_open'] = panel_open
            return geometry
    # Godius can retain the scale from startup after a display mode change.
    # Try the same researched formula for public display-mode heights, never
    # arbitrary positions or an OCR-derived box. Reject ambiguous evidence.
    matches = []
    for scale in sorted({default_scale(h) for h in candidate_heights} - set(candidates)):
        geometry = geometry_for_size(frame.size, scale)
        errors = header_errors(frame, geometry)
        if max(errors) <= .16 and sum(errors) <= .23:
            matches.append((sum(errors), geometry))
    matches.sort(key=lambda item: item[0])
    if matches and (len(matches) == 1 or matches[1][0]-matches[0][0] >= .04):
        geometry = matches[0][1]
        geometry['status_panel_open'] = status_panel_visible(frame, geometry)
        return geometry
    return None
