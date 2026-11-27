"""Import NGN map artwork/geometry without changing gameplay metadata.

NGN is read-only. The baseline and report make the import auditable/repeatable.
"""
import argparse
import copy
import hashlib
import json
from pathlib import Path
import shutil

ROOT = Path(__file__).resolve().parents[1]
ADDITIONS = {'carl1f': '림치', 'cback1f': '림치',
             'carl2f': 'SERE', 'carl3f': 'SERE', 'cback2f': 'SERE', 'cback3f': 'SERE'}
CHANGED_KEYS = {'image', 'images', 'imageSize', 'transform', 'controlPoints'}
ADDED_KEYS = {'gameMapIds', 'geometry', 'portals', 'excludedPortals',
              'annotationTransform', 'facilities', 'mapArtworkSource'}
# User-supplied live entry-level table (2026-11-27), matched by destination ID.
# Spellings, spaces and the optional 층 suffix are not availability evidence.
LIVE_DUNGEON_DESTINATIONS = {
    *range(615, 621),  # 루크레시아/람파스 지하로 1-3
    *range(450, 470),  # 칼리/레게 1-10
    *range(330, 336), *range(490, 496),  # 사에프/샤드뮴 1-6
    *range(607, 612), *range(621, 626),  # 서부/동부등뼈 1-5
    603, 394, 395, 604, 396, 397,  # 중부등뼈/카를마뉴 1-3
    *range(626, 636),  # 헬 1-10
    694, 695, 696, 636, 639, 691, 692, 693, 638, 637,  # 에칠린/에블린 1-5
    470, 471, 472, 473, 474, 475, 508, 576,  # 수련장
}
# Field/town travel and PvP arenas are outside the dungeon-entry table.
NON_DUNGEON_DESTINATIONS = {
    *range(0, 11), *range(12, 23), 37, 103, 336, 699,
    24, 73, 123, 188, 340, 350, 400, 500, 550, 640, 700,
    476, 600,
}
UNRELEASED_DESTINATIONS = {276}  # User explicitly confirmed 중부사막동굴.


def exclude_unreleased_portals(record):
    visible = []
    excluded = record.setdefault('excludedPortals', [])
    for portal in record.get('portals', []):
        target = portal.get('targetMapId')
        if target not in LIVE_DUNGEON_DESTINATIONS | NON_DUNGEON_DESTINATIONS:
            reason = 'not-live-service' if target in UNRELEASED_DESTINATIONS else 'not-in-live-entry-table'
            portal = dict(portal, exclusionReason=reason)
            if portal not in excluded:
                excluded.append(portal)
        else:
            visible.append(portal)
    record['portals'] = visible


def read(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--apply', action='store_true')
    args = parser.parse_args()
    ngn = ROOT.parent / 'New_gdnv'
    source = ngn / 'legacy_resources'
    audit = ROOT / '.tmp/ngn-map-migration'
    baseline_path = audit / 'baseline.json'
    if baseline_path.exists():
        baseline = read(baseline_path)
    else:
        baseline = {'maps': {p.relative_to(ROOT).as_posix(): read(p)
                            for p in sorted((ROOT / 'content-source/maps').rglob('*.json'))},
                    'protected': {p.relative_to(ROOT).as_posix(): digest(p)
                                  for folder in ('content-source/monsters', 'private/content-source/map-images/other')
                                  for p in (ROOT / folder).rglob('*') if p.is_file()}}
        write(baseline_path, baseline)
    incoming = {r['id']: r for r in (read(p) for p in (source / 'content-source/maps').rglob('*.json'))}
    facilities = read(ngn / 'assets/map-facilities.json')['facilities']
    report = {'replacedCoordinates': [], 'addedCoordinates': [], 'withoutCoordinates': [], 'imageExceptions': []}
    for relative, old in baseline['maps'].items():
        record = copy.deepcopy(old)
        mid = old['id']
        new = incoming[mid]
        rendered = new.get('geometry', {}).get('kind') == 'isometric-tiles'
        entry = {'id': mid, 'name': old['names']['ko'][0]}
        if rendered:
            for key in ('image', 'images', 'imageSize'):
                record[key] = copy.deepcopy(new[key])
            for key in ('gameMapIds', 'geometry', 'portals', 'excludedPortals'):
                record[key] = copy.deepcopy(new.get(key, []))
            record['annotationTransform'] = copy.deepcopy(new['transform'])
            if old.get('transform') or mid in ADDITIONS:
                record['transform'] = copy.deepcopy(new['transform'])
                record['controlPoints'] = copy.deepcopy(new.get('controlPoints', []))
            else:
                # Old image-space calibration points must never fit the new artwork.
                record['controlPoints'] = []
            record['facilities'] = [copy.deepcopy(p) for p in facilities if p['mapKey'] == mid]
            record['mapArtworkSource'] = {'kind': 'ngn-rendered',
                                          'sha256': digest(source / 'private/content-source/map-images' / new['image'][5:])}
            if args.apply:
                target = ROOT / 'private/content-source/map-images' / new['image'][5:]
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(source / 'private/content-source/map-images' / new['image'][5:], target)
        else:
            report['imageExceptions'].append(entry)
            if old.get('transform'):
                raise ValueError(f'Cannot replace calibrated map without NGN geometry: {mid}')
        if mid in ADDITIONS:
            names = record.get('contributors', [])
            names = [names] if isinstance(names, str) else list(names)
            if ADDITIONS[mid] not in names:
                names.append(ADDITIONS[mid])
            record['contributors'] = names
        for key, value in old.items():
            if key not in CHANGED_KEYS and not (key == 'contributors' and mid in ADDITIONS):
                assert record[key] == value, (mid, key)
        bucket = 'replacedCoordinates' if old.get('transform') else 'addedCoordinates' if mid in ADDITIONS else 'withoutCoordinates'
        report[bucket].append(entry)
        exclude_unreleased_portals(record)
        if args.apply:
            write(ROOT / relative, record)
    for relative, expected in baseline['protected'].items():
        assert digest(ROOT / relative) == expected, relative
    report['summary'] = {k: len(v) for k, v in report.items()}
    report['summary']['maps'] = len(baseline['maps'])
    report['summary']['replacedImages'] = len(baseline['maps']) - len(report['imageExceptions'])
    write(audit / 'report.json', report)
    if args.apply:
        lines = ['# 가디내비 지도 교체 내역', '', 'NGN은 읽기 전용으로 참조. 기존 몬스터 정보·지도 ID·명칭·기여자·월드맵은 보존.',
                 '입구/시설용 annotationTransform과 내 위치용 transform을 분리하여 좌표 미지원 지도에 내 위치를 새로 활성화하지 않음.', '']
        for key, title in [('replacedCoordinates', '기존 위치 좌표 교체'), ('addedCoordinates', '위치 좌표 신규 추가 (1층 림치 / 2·3층 SERE)'),
                           ('withoutCoordinates', '위치 좌표 미지원 유지'), ('imageExceptions', '이미지 유지 예외 — NGN에도 새 원본 없음')]:
            lines += [f'## {title} ({len(report[key])}개)', '', '| 지도 | ID |', '|---|---|']
            lines += [f'| {r["name"]} | `{r["id"]}` |' for r in report[key]]
            lines += ['']
        (ROOT / 'docs/map-migration.md').write_text('\n'.join(lines), encoding='utf-8')
    print(json.dumps(report['summary']))


if __name__ == '__main__':
    main()
