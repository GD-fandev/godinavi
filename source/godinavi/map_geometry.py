"""Independent image-axis scaling; annotations do not enable player tracking."""
import math


def project_coordinate(record, x, y, display_size=None, *, annotations=False):
    try:
        x, y = float(x), float(y)
        if not all(math.isfinite(v) for v in (x, y)):
            return None
        geometry = record.get('geometry', {})
        if geometry.get('kind') == 'isometric-tiles':
            if not (0 <= x < geometry['tileWidth'] and 0 <= y < geometry['tileHeight']):
                return None
        t = record.get('annotationTransform') if annotations else record.get('transform')
        if not t and annotations:
            t = record.get('transform')
        u = t['imageX']['gameX'] * x + t['imageX']['gameY'] * y + t['imageX']['offset']
        v = t['imageY']['gameX'] * x + t['imageY']['gameY'] * y + t['imageY']['offset']
        if display_size:
            u *= display_size[0] / record['imageSize']['width']
            v *= display_size[1] / record['imageSize']['height']
        return (u, v) if math.isfinite(u) and math.isfinite(v) else None
    except (KeyError, TypeError, ValueError, ZeroDivisionError):
        return None
