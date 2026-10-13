#!/usr/bin/env python3
"""Check Gathering 20's scope, record, gallery and delivered bytes offline."""
import hashlib
from html.parser import HTMLParser
import json
from pathlib import Path
import struct
import subprocess

ROOT = Path(__file__).resolve().parents[1]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def require(ok, message):
    if not ok:
        raise ValueError(message)


def jpeg_size(data):
    require(data[:2] == b'\xff\xd8' and data[-2:] == b'\xff\xd9', 'JPEG signature')
    pos = 2
    while pos < len(data):
        require(data[pos] == 255, 'JPEG marker')
        marker = data[pos + 1]
        pos += 2
        length = int.from_bytes(data[pos:pos + 2], 'big')
        if marker == 0xc0:
            return struct.unpack('>HH', data[pos + 3:pos + 7])[::-1]
        if marker == 0xda:
            break
        pos += length
    raise ValueError('baseline JPEG dimensions missing')


class Gallery(HTMLParser):
    def __init__(self):
        super().__init__()
        self.sections = {}
        self.wall = None
        self.scripts = 0

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == 'section':
            self.wall = attrs['id']
            self.sections[self.wall] = []
        if tag == 'article':
            self.sections[self.wall].append(int(attrs['data-number']))
        if tag == 'script':
            self.scripts += 1


def main():
    wall = ROOT / 'artifacts/gathering/wall-v21.png'
    raw = wall.read_bytes()
    require(raw[:8] == b'\x89PNG\r\n\x1a\n', 'PNG signature')
    require(struct.unpack('>IIBB', raw[16:26]) == (1254, 1254, 8, 2),
            'PNG dimensions or format')
    require(raw == (wall.parent / 'wall.png').read_bytes(), 'continuation differs')
    require({p.name for p in wall.parent.iterdir()} == {'wall-v21.png', 'wall.png'},
            'unexpected gathering image')
    jpeg = ROOT / 'dist/gathering/20.jpg'
    require(jpeg_size(jpeg.read_bytes()) == (512, 512), 'JPEG dimensions')
    require(jpeg.stat().st_size < 100000, 'JPEG byte limit')
    review = json.loads((ROOT / 'gathering/checks/round-20/image-preservation.json').read_text())
    require(review['source_sha256'] == json.loads((ROOT / 'dist/gathering/19.json').read_text())['image'].rsplit('/', 1)[1],
            'ancestral digest')
    require(review['wall_sha256'] == sha(wall), 'review wall digest')
    require(review['png_dimensions'] == [1254, 1254] and
            review['jpeg_dimensions'] == [512, 512], 'review dimensions')
    require(review['changed_pixels'] > 0 and
            review['changed_pixels_outside_rectangle'] == 0,
            'ancestor preservation review')
    require(review['inherited_hand_digit_counts'] == [5, 5] and
            review['new_hand_or_handprint_count'] == 0 and
            review['unmet_visual_requirements'] == [], 'visual review')

    record = json.loads((ROOT / 'dist/gathering/20.json').read_text())
    require(set(record) == {'name', 'image', 'attributes'}, 'record fields')
    require(record['image'] == 'https://api.imd.fun/artifacts/' + sha(wall),
            'record artifact digest')
    expected = ['Cave', 'Wall', 'Number', 'Left behind', 'Meaning', 'One thing']
    require([item['trait_type'] for item in record['attributes']] == expected,
            'record trait order')
    require(all(set(item) == {'trait_type', 'value'} for item in record['attributes']),
            'record trait fields')
    traits = {item['trait_type']: item['value'] for item in record['attributes']}
    require(traits['Cave'] == 'Base' and traits['Wall'] == 'Gathering' and
            type(traits['Number']) is int and traits['Number'] == 20 and
            traits['One thing'] == 'Gathering', 'record identity')
    goals = [{'line': n, 'goal': (ROOT / f'line-{n}/GOAL.md').read_text().strip()}
             for n in range(1, 5)]
    require(json.loads((ROOT / 'dist/goals.json').read_text()) == goals, 'goal index')
    gallery = Gallery()
    gallery.feed((ROOT / 'dist/index.html').read_text())
    count = 0
    for folder in ('line-1', 'line-2', 'line-3', 'line-4', 'gathering'):
        painted, pending = [], []
        for path in sorted((ROOT / 'dist' / folder).glob('[0-9][0-9].json'), reverse=True):
            obj = json.loads(path.read_text())
            count += 1
            waiting = obj['name'] == 'Not painted yet'
            (pending if waiting else painted).append(int(path.stem))
            if waiting:
                require(not path.with_suffix('.jpg').exists(), 'placeholder JPEG')
        require(gallery.sections[folder] == painted + pending, 'gallery coverage/order')
    require(gallery.scripts == 0, 'gallery script')
    require((ROOT / 'dist/index.html').stat().st_size < 100000, 'gallery size')

    checks = json.loads((ROOT / 'gathering/checks/round-20/tool-checks.json').read_text())
    require(len(checks) == 121 and all(row['exit'] == 0 for row in checks),
            'line check failures or missing commands')
    require(sum(row['kind'] == 'suite' for row in checks) == 61 and
            sum(row['tests_run'] for row in checks) == 842, 'line test coverage')
    require('Ran 21 tests' in (ROOT / 'gathering/checks/round-20/shared-all-tests.txt').read_text(),
            'shared tests')
    require(json.loads((ROOT / 'gathering/checks/round-20/native-extension-review.json').read_text())['selected_checks_passed'],
            'native archive review')
    provenance = json.loads((ROOT / 'shared/proof-handoff/CODE-EXTENSION-PROVENANCE.json').read_text())
    require(sha(ROOT / provenance['source']) == provenance['source_sha256'], 'source provenance')
    require(sha(ROOT / 'shared/proof-handoff' / provenance['copy']) == provenance['copy_sha256'],
            'copy provenance')
    require(sha(ROOT / 'shared/proof-handoff' / provenance['extension_archive']) == provenance['extension_sha256'],
            'archive provenance')

    changed = subprocess.run(['git', 'diff', '--name-only'], cwd=ROOT,
                             check=True, capture_output=True, text=True).stdout.splitlines()
    added = subprocess.run(['git', 'ls-files', '--others', '--exclude-standard'], cwd=ROOT,
                           check=True, capture_output=True, text=True).stdout.splitlines()
    require(all(path.startswith(('gathering/', 'shared/', 'dist/', 'artifacts/gathering/',
                                 'test/scratch/')) for path in changed + added), 'out-of-scope changes')
    require(not any(path.startswith(('line-', 'dist/line-')) for path in changed + added),
            'line change')
    for raw_path in changed + added:
        path = ROOT / raw_path
        if path.is_file() and not raw_path.startswith(('artifacts/', 'test/scratch/')):
            require(path.stat().st_size < 100000, 'oversize ordinary file: ' + raw_path)
    require(not subprocess.run(['git', 'ls-files', 'artifacts/gathering'], cwd=ROOT,
                               check=True, capture_output=True, text=True).stdout.strip(),
            'named image output should remain untracked')
    require((ROOT / 'gathering/COINS.md').read_text().splitlines()[0] == 'none',
            'coin decision')
    require(not (ROOT / 'gathering/coin-order.json').exists() and
            not (ROOT / 'gathering/deploy-order.json').exists(), 'unexpected order')
    result = {'status': 'passed', 'records': count, 'line_suites': 61,
              'line_tests': 842, 'line_demos': 60, 'shared_tests': 21,
              'png_dimensions': [1254, 1254], 'png_format': '8-bit RGB PNG',
              'jpeg_dimensions': [512, 512], 'jpeg_format': 'baseline JPEG',
              'wall_sha256': sha(wall), 'unmet_visual_requirements': []}
    output = ROOT / 'gathering/checks/round-20/deliverable.json'
    output.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
