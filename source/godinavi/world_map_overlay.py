"""Localized world-map labels. Blinking changes only the current marker tag."""
import tkinter.font as tkfont
from datetime import datetime, timedelta, timezone
import math

KST = timezone(timedelta(hours=9), 'KST')
EVENT_EXCLUDED_FIELDS = {'calibria', 'gamria', 'lampas', 'lucre', 'calbiron', 'shaadmum', 'saiefe'}
TOWN_IDS = {'1_militard', '2_dihol', '3_baldium', '4_hilock', '5_gratiz',
            '6_pagohol', '7_laslan', '8_caswell', '9_rocky', '10_deeval', '11_liberty'}
PERMANENT_FREE_PK = {'iskald', 'goldred'}


def reaper_schedule(now=None):
    now = datetime.now(KST) if now is None else now.astimezone(KST)
    start = now.replace(hour=(now.hour // 4) * 4, minute=0, second=0, microsecond=0)
    active = now < start + timedelta(hours=1)
    boundary = start + timedelta(hours=1 if active else 4)
    return now, active, max(0, math.ceil((boundary - now).total_seconds()))


def event_free_pk(region, record, active):
    return bool(active and not region.get('faction') and record['id'] not in TOWN_IDS | EVENT_EXCLUDED_FIELDS)


def map_pk_level(record, event_active=False):
    if not record:
        return 0
    if record.get('id') in PERMANENT_FREE_PK or event_free_pk({}, record, event_active):
        return 2
    return 1 if record.get('isPKArea') else 0


def clock_text(schedule, language):
    now, active, remaining = schedule
    hours, seconds = divmod(remaining, 3600)
    minutes, seconds = divmod(seconds, 60)
    if active:
        minutes += hours * 60
    if language == 'KR':
        count = f'{minutes:02d}분 {seconds:02d}초' if active else f'{hours:02d}시 {minutes:02d}분 {seconds:02d}초'
        return f'현재 시각 (KST) {now:%H:%M}\n사신의 칼날 {"종료" if active else "시작"}까지 {count}'
    count = f'{minutes:02d}:{seconds:02d}' if active else f'{hours:02d}:{minutes:02d}:{seconds:02d}'
    if language == 'JP':
        return f'現在時刻 (JST) {now:%H:%M}\n死神の刃 {"終了" if active else "開始"}まで {count}'
    return f'Current time (KST) {now:%H:%M}\nReaper’s Blade {"ends" if active else "starts"} in {count}'


def draw_clock(canvas, size, language, schedule):
    text = clock_text(schedule, language)
    if getattr(canvas, '_world_clock_text', None) == text and canvas.find_withtag('world_clock_text'):
        return
    canvas._world_clock_text = text
    if not canvas.find_withtag('world_clock_text'):
        family = {'KR': 'Malgun Gothic', 'JP': 'Yu Gothic'}.get(language, 'Segoe UI')
        font_size = max(11, min(22, round(size[0] / 100)))
        canvas.create_text(size[0]-16, 14, text=text, anchor='ne', justify='right',
                           font=(family, -font_size, 'bold'), fill='#ffc45b' if schedule[1] else '#f4e7bc',
                           tags=('world_clock', 'world_clock_text'))
        canvas.create_rectangle(0, 0, 1, 1, fill='#0b1b27', outline='#48606f',
                                tags=('world_clock', 'world_clock_bg'))
        canvas.tag_lower('world_clock_bg', 'world_clock_text')
    else:
        canvas.itemconfigure('world_clock_text', text=text,
                             fill='#ffc45b' if schedule[1] else '#f4e7bc')
    box = canvas.bbox('world_clock_text')
    if box:
        canvas.coords('world_clock_bg', box[0]-8, box[1]-6, box[2]+8, box[3]+6)

COLORS = {'belk': '#ff656d', 'taperi': '#769dff', 'neutral': '#f2f2f2',
          'field': '#d8e5a1', 'pk': '#ff8c80', 'free': '#ffc45b'}
LEGEND = {
    'ko': ('벨크 마을', '타페리 마을', '중립 마을', 'PK', 'FREE PK'),
    'ja': ('ベルクの町', 'タペリの町', '中立の町', 'PK', 'FREE PK'),
    'en': ('Belk town', 'Taperi town', 'Neutral town', 'PK', 'FREE PK'),
}


def region_style(region, record, event_active=False):
    skulls = map_pk_level(record, event_active)
    color = COLORS.get(region.get('faction'), COLORS['free' if skulls == 2 else 'pk' if skulls else 'field'])
    return skulls, color


def marker_visibility(canvas, visible):
    canvas.itemconfigure('world_current', state='normal' if visible else 'hidden')


def draw_overlay(canvas, layout, records, active_id, size, language, event_active=False):
    canvas.delete('world_labels')
    canvas.delete('world_current')
    canvas.delete('world_legend')
    locale = {'KR': 'ko', 'JP': 'ja', 'EN': 'en'}.get(language, 'en')
    width, height = size
    sx, sy = width / layout['size'][0], height / layout['size'][1]
    font_size = max(10, min(22, round(width / 105)))
    family = {'ko': 'Malgun Gothic', 'ja': 'Yu Gothic', 'en': 'Segoe UI'}[locale]
    font = tkfont.Font(root=canvas, family=family, size=-font_size, weight='bold')
    emoji = tkfont.Font(root=canvas, family='Segoe UI Emoji', size=-font_size)
    by_id = {r['id']: r for r in records}
    for region in layout['regions']:
        record = by_id.get(region['id'])
        if record is None:
            continue
        x, y = region['center'][0] * sx, region['center'][1] * sy
        if region['id'] == active_id:
            r = max(12, font_size)
            canvas.create_polygon(x-r*.45, y-r, x+r*.45, y-r,
                                  x+r*.45, y, x+r, y, x, y+r,
                                  x-r, y, x-r*.45, y,
                                  fill='#ffdf62', outline='#101820', width=2,
                                  tags='world_current')
            continue
        names = record.get('names', {})
        name = (names.get(locale) or names.get('ko') or [record['id']])[0]
        skulls, color = region_style(region, record, event_active)
        prefix = '💀' * skulls
        prefix_width = emoji.measure(prefix) + (3 if skulls else 0)
        wrap = max(75, min(200, region['rect'][2] * sx * .95))
        text = canvas.create_text(x + prefix_width/2, y, text=name, font=font,
                                  width=wrap, justify='center', fill=color, tags='world_labels')
        box = canvas.bbox(text)
        if box:
            left, top, right, bottom = box
            bg = canvas.create_rectangle(left-prefix_width-4, top-2, right+4, bottom+2,
                                         fill='#0b1b27', outline='', tags='world_labels')
            canvas.tag_lower(bg, text)
            if prefix:
                canvas.create_text(left-3, y, text=prefix, anchor='e', font=emoji,
                                   fill=color, tags='world_labels')
    # Font objects must remain alive while Tk canvas items reference them.
    canvas._world_label_fonts = (font, emoji)
    titles = LEGEND[locale]
    symbols = ('●', '●', '●', '💀', '💀💀')
    icon_width = max(emoji.measure(symbol) for symbol in symbols)
    text_offset = 7 + icon_width + 12
    line_height = max(font.metrics('linespace'), emoji.metrics('linespace')) + 7
    legend_width = max(font.measure(t) for t in titles) + text_offset + 12
    left, top = width-legend_width-12, height-line_height*len(titles)-20
    canvas.create_rectangle(left, top, width-8, height-8, fill='#0b1b27',
                            outline='#48606f', tags='world_legend')
    for i, (symbol, color, title) in enumerate(zip(
            symbols,
            (COLORS['belk'], COLORS['taperi'], COLORS['neutral'], COLORS['pk'], COLORS['free']), titles)):
        y = top+8+i*line_height
        canvas.create_text(left+7, y, text=symbol, anchor='nw', font=emoji,
                           fill=color, tags='world_legend')
        canvas.create_text(left+text_offset, y, text=title, anchor='nw', font=font,
                           fill=color, tags='world_legend')
