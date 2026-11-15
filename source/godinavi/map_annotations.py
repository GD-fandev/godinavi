"""Name-only portal annotations, independent of the player marker."""
from functools import lru_cache
from pathlib import Path
from PIL import ImageDraw, ImageFont
from .map_geometry import project_coordinate

EXCLUDED_TOWN_DESTINATIONS = ('수련장', '헬피도', '미로')


def visible_destination(name, is_town):
    return not is_town or not any(term in name for term in EXCLUDED_TOWN_DESTINATIONS)


@lru_cache(maxsize=16)
def label_font(size, locale='ko', weight=600):
    import sys
    engine = sys.modules.get('map_engine')
    bundle = getattr(engine, 'BUNDLE_DIR', Path(__file__).resolve().parents[2] / 'private/content-source/runtime')
    fonts = bundle / 'assets/fonts'
    filename = {'ja':'notosansjp-variablefont_wght.ttf','ko':'notosanskr-variablefont_wght.ttf','en':'notosans-variablefont_wdth,wght.ttf'}.get(locale,'notosansjp-variablefont_wght.ttf')
    candidates = [fonts/filename, Path('C:/Windows/Fonts/malgun.ttf')]
    for path in candidates:
        if path.is_file():
            font = ImageFont.truetype(str(path), size)
            try:
                axes = font.get_variation_axes()
                font.set_variation_by_axes([weight if axis['name'] == b'Weight' else axis['default'] for axis in axes])
            except (OSError, ValueError):
                pass
            return font
    return ImageFont.load_default()


def annotate_portals(image, record, locale='ko', style=None):
    map_id = record.get('currentGameMapId', next(iter(record.get('gameMapIds', [])), None))
    points = [p for p in record.get('portals', [])
              if map_id is None or map_id in p.get('sourceMapIds', [p.get('sourceMapId', map_id)])]
    return annotate_points(image, record, points, style, locale)


def annotate_points(image, record, entries, style=None, locale='ko', *, annotations=True):
    """Draw at final resolution so labels remain readable on small minimaps."""
    from .map_preferences import LAYER_DEFAULT
    style = dict(LAYER_DEFAULT, **(style or {}))
    if not style['visible']: return image
    draw = ImageDraw.Draw(image)
    font_size = style['font_size']
    font = label_font(font_size, locale, style['font_weight'])
    points = []
    for p in entries:
        position = project_coordinate(record, p['x'], p['y'], image.size, annotations=annotations)
        if position is not None:
            points.append((p, *position))
    occupied = [(x-8,y-8,x+8,y+8) for _,x,y in points]

    def overlap(a, b):
        return max(0,min(a[2],b[2])-max(a[0],b[0])) * max(0,min(a[3],b[3])-max(a[1],b[1]))

    for p, x, y in points:
        if not style['labels']: continue
        text = p.get('names', {}).get(locale) or p['name']
        bbox = draw.textbbox((0,0), text, font=font)
        w, h = bbox[2]-bbox[0]+16, bbox[3]-bbox[1]+12
        preferred = -1 if x < image.width/2 else 1
        choices=[]
        for side in (preferred,-preferred):
            for offset in (0,-h,h,-2*h,2*h,-3*h,3*h):
                tx=x+14 if side==1 else x-14-w
                ty=y-h/2+offset
                tx=max(2,min(image.width-w-2,tx));ty=max(2,min(image.height-h-2,ty))
                rect=(tx,ty,tx+w,ty+h)
                score=sum(overlap(rect,r) for r in occupied)*100+abs(offset)+(side!=preferred)*5
                choices.append((score,rect))
        _,rect=min(choices,key=lambda item:item[0]);occupied.append(rect)
        tx,ty,right,bottom=rect
        endpoint=(max(tx,min(right,x)),max(ty,min(bottom,y)))
        if style['leaders']:
            draw.line((x,y,*endpoint),fill=style['leader_color'],width=1)
        if style['label_background']:
            draw.rounded_rectangle(rect,radius=4,fill=style['background'],outline=style['border'])
        draw.text((tx+8-bbox[0],ty+6-bbox[1]),text,font=font,fill=style['text_color'])
    # All dots are on top of label leaders and retain their exact tile position.
    radius=style['radius']
    for _,x,y in points:
        draw.ellipse((x-radius,y-radius,x+radius,y+radius),fill=style['color'],outline=style['outline'],width=2)
    return image
