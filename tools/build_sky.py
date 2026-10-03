#!/usr/bin/env python3
"""Regenerate sky.js (catalogue stars and galaxies) for the La Silla model.

    python3 tools/build_sky.py            # writes ../sky.js

Stars:    HYG database v4.1 (Hipparcos + Yale Bright Star + Gliese), every star down to MAG_STARS.
Galaxies: OpenNGC (NGC/IC plus addendum), every galaxy down to MAG_GALAXIES.
Both are CC BY-SA 4.0, and so is the derived sky.js.

The raw catalogues (about 38 MB) are downloaded into tools/cache/ on first use and are
not committed. Standard library only.
"""
import base64, csv, json, struct, subprocess, sys
from pathlib import Path

MAG_STARS, MAG_GALAXIES = 7.5, 12.0
HYG = 'https://raw.githubusercontent.com/astronexus/HYG-Database/main/hyg/CURRENT/hygdata_v41.csv'
NGC = 'https://raw.githubusercontent.com/mattiaverga/OpenNGC/master/database_files/'
ROOT = Path(__file__).resolve().parent
CACHE = ROOT / 'cache'


def cached(name, url):
    fn = CACHE / name
    if not fn.exists():
        subprocess.run(['curl', '-sfL', '-m', '300', '-A', 'LaSilla3D-model/1.0 (personal project)', '-o', str(fn), url], check=True)
    return fn


def stars():
    """6 bytes per star: RA uint16 (turn/65536), Dec int16 (90 deg/32767), magnitude uint8 ((m+2)*25), B-V uint8 ((c+0.5)*100)."""
    rows = []
    with open(cached('hyg.csv', HYG), newline='') as f:
        for r in csv.DictReader(f):
            if r['id'] == '0' or not r['mag']:          # id 0 is the Sun
                continue
            mag = float(r['mag'])
            if mag <= MAG_STARS:
                rows.append((mag, float(r['ra']), float(r['dec']), float(r['ci']) if r['ci'] else 0.6))
    rows.sort()                                          # brightest first
    buf = bytearray()
    for mag, ra, dec, ci in rows:
        buf += struct.pack('<HhBB', int(ra / 24 * 65536) % 65536, round(dec / 90 * 32767),
                           max(0, min(255, round((mag + 2) * 25))), max(0, min(255, round((ci + 0.5) * 100))))
    return dict(n=len(rows), b64=base64.b64encode(bytes(buf)).decode())


def sexa(s, hours):
    sign = -1 if s.startswith('-') else 1
    a, b, c = (float(x) for x in s.lstrip('+-').split(':'))
    return sign * (a + b / 60 + c / 3600) * (15 if hours else 1)


def galaxies():
    """[RA deg, Dec deg, major axis arcmin, axis ratio, position angle deg, magnitude, name], brightest first."""
    out = []
    for name in ('NGC.csv', 'addendum.csv'):
        with open(cached(name, NGC + name), newline='') as f:
            for r in csv.DictReader(f, delimiter=';'):
                if r['Type'] not in ('G', 'GPair', 'GTrpl', 'GGroup') or not r['RA'] or not r['MajAx']:
                    continue
                mags = [float(r[k]) for k in ('V-Mag', 'B-Mag') if r[k]]
                if not mags or mags[0] > MAG_GALAXIES:
                    continue
                maj = float(r['MajAx'])
                ratio = float(r['MinAx']) / maj if r['MinAx'] else 1.0
                label = r['Common names'].split(',')[0] or ('M' + r['M'].lstrip('0') if r['M'] else r['Name'])
                out.append([round(sexa(r['RA'], True), 3), round(sexa(r['Dec'], False), 3), round(maj, 1), round(max(ratio, 0.2), 2),
                            int(r['PosAng']) if r['PosAng'] else 0, round(mags[0], 1), label])
    out.sort(key=lambda g: g[5])
    return out


def main():
    out_path = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT.parent / 'sky.js'
    CACHE.mkdir(exist_ok=True)
    data = dict(magStars=MAG_STARS, stars=stars(), galaxies=galaxies())
    text = ('// Catalogue sky. Stars: HYG database v4.1 (astronexus). Galaxies: OpenNGC (Mattia Verga). Both CC BY-SA 4.0, as is this file.\n'
            'window.LASILLA_SKY = ' + json.dumps(data, separators=(',', ':'), ensure_ascii=False) + ';\n')
    out_path.write_text(text)
    print(f"{out_path}: {len(text)} bytes, {data['stars']['n']} stars to mag {MAG_STARS}, {len(data['galaxies'])} galaxies to mag {MAG_GALAXIES}")
    print('brightest galaxies:', [(g[6], g[5], g[2]) for g in data['galaxies'][:8]])


if __name__ == '__main__':
    main()
