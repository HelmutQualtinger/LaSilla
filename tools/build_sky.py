#!/usr/bin/env python3
"""Regenerate sky.js (catalogue stars, galaxies and constellation figures) for the La Silla model.

    python3 tools/build_sky.py            # writes ../sky.js

Stars:    HYG database v4.1 (Hipparcos + Yale Bright Star + Gliese), every star down to MAG_STARS.
Galaxies: OpenNGC (NGC/IC plus addendum), every galaxy down to MAG_GALAXIES.
Both are CC BY-SA 4.0, and so is the derived sky.js.
Constellation figures: the stick figures in FIGURES below, written by hand as chains of Bayer
designations and resolved to HYG positions, so they end exactly on the drawn stars.

The raw catalogues (about 38 MB) are downloaded into tools/cache/ on first use and are
not committed. Standard library only.
"""
import base64, csv, json, struct, subprocess, sys
from pathlib import Path

MAG_STARS, MAG_GALAXIES = 7.5, 12.0
HYG = 'https://raw.githubusercontent.com/astronexus/HYG-Database/main/hyg/CURRENT/hygdata_v41.csv'
NGC = 'https://raw.githubusercontent.com/mattiaverga/OpenNGC/master/database_files/'
# The constellations worth seeing from latitude -29. Paths are separated by ';', consecutive stars are joined. A bare letter
# also matches its brightest numbered component (Alp -> Alp-1); Alp_And names a star of another constellation.
FIGURES = {
    'Ori': 'Alp Zet Kap Bet Del Gam Alp Lam Gam; Del Eps Zet',
    'CMa': 'Bet Alp Omi-2 Del Eta; Del Eps',
    'CMi': 'Alp Bet',
    'Tau': 'Zet Alp The Gam Del Eps Bet; Gam Lam',
    'Gem': 'Alp Tau Eps Mu; Bet Del Zet Gam; Alp Bet',
    'Aur': 'Alp Bet The Bet_Tau Iot Alp',
    'Ari': 'Alp Bet Gam',
    'Leo': 'Eps Mu Zet Gam Eta Alp The Bet Del Gam; Del The',
    'Vir': 'Bet Eta Gam The Alp Zet Del Gam; Del Eps',
    'Lib': 'Sig Alp Bet Gam Alp',
    'Sco': 'Bet Del Pi; Del Sig Alp Tau Eps Mu Zet Eta The Iot Kap Lam Ups',
    'Sgr': 'Gam Del Eps Zet Phi Del Lam Phi Sig Tau Zet; Gam Eps',
    'Cap': 'Alp Bet Psi Ome Zet Eps Del Gam Iot The Bet',
    'Aqr': 'Eps Bet Alp Gam Zet Eta; Alp The Lam Del',
    'Cru': 'Alp Gam; Bet Del',
    'Cen': 'Alp Bet Eps Zet Mu Nu The; Mu Eta Kap; Eps Gam Del; Nu Iot',
    'Lup': 'Alp Bet Del Gam Eps Zet Alp; Gam Eta; Del Phi Chi',
    'TrA': 'Alp Bet Gam Alp',
    'Ara': 'The Alp Bet Gam Del; Alp Eps Zet Eta',
    'Mus': 'Lam Eps Alp Bet Del Gam Alp',
    'Car': 'Alp Bet Ome The Iot Eps Chi Alp',
    'Vel': 'Gam Lam Psi Mu Phi Kap Del Gam',
    'Pup': 'Zet Rho Xi Pi Nu Tau Sig Zet',
    'Pav': 'Alp Bet Del Lam Xi Pi Eta Zet Eps Del; Bet Gam',
    'Gru': 'Gam Lam Mu Del Bet Eps Zet; Del Alp Bet',
    'PsA': 'Alp Eps Lam The Iot Mu Bet Gam Del Alp',
    'Eri': 'Alp Chi Phi Kap Iot The Ups-4 Ups-2 Tau-6 Tau-5 Tau-4 Tau-3 Tau-1 Eta Eps Del Gam Nu Mu Bet',
    'Hya': 'Sig Del Eps Zet The Iot Alp Ups Lam Mu Nu Xi Bet Gam Pi; Zet Eta Sig',
    'Crv': 'Alp Eps Gam Del Bet Eps',
    'Aql': 'Gam Alp Bet; Zet Del The; Alp Del Lam',
    'Lyr': 'Alp Zet Bet Gam Del Zet',
    'Cyg': 'Alp Gam Eta Bet; Zet Eps Gam Del',
    'Peg': 'Alp Bet Alp_And Gam Alp Zet The Eps; Bet Eta',
    'And': 'Alp Del Bet Gam',
    'Boo': 'Alp Eps Del Bet Gam Rho Alp Eta',
    'CrB': 'The Bet Alp Gam Del Eps',
    'Her': 'Pi Eta Zet Eps Pi; Zet Bet Gam; Eps Del',
    'Oph': 'Alp Kap Lam Del Eps Zet Eta Bet Alp',
    'UMa': 'Eta Zet Eps Del Alp Bet Gam Del',
}
ROOT = Path(__file__).resolve().parent
CACHE = ROOT / 'cache'


def cached(name, url):
    fn = CACHE / name
    if not fn.exists():
        subprocess.run(['curl', '-sfL', '-m', '300', '-A', 'LaSilla3D-model/1.0 (personal project)', '-o', str(fn), url], check=True)
    return fn


def stars(bayer):
    """6 bytes per star: RA uint16 (turn/65536), Dec int16 (90 deg/32767), magnitude uint8 ((m+2)*25), B-V uint8 ((c+0.5)*100)."""
    rows = []
    with open(cached('hyg.csv', HYG), newline='') as f:
        for r in csv.DictReader(f):
            if r['id'] == '0' or not r['mag']:          # id 0 is the Sun
                continue
            mag = float(r['mag'])
            if r['bayer']:                               # (constellation, designation) -> brightest star carrying it
                for key in {r['bayer'], r['bayer'].split('-')[0]}:
                    bayer.setdefault((r['con'], key), []).append((mag, float(r['ra']) * 15, float(r['dec'])))
            if mag <= MAG_STARS:
                rows.append((mag, float(r['ra']), float(r['dec']), float(r['ci']) if r['ci'] else 0.6))
    rows.sort()                                          # brightest first
    buf = bytearray()
    for mag, ra, dec, ci in rows:
        buf += struct.pack('<HhBB', int(ra / 24 * 65536) % 65536, round(dec / 90 * 32767),
                           max(0, min(255, round((mag + 2) * 25))), max(0, min(255, round((ci + 0.5) * 100))))
    return dict(n=len(rows), b64=base64.b64encode(bytes(buf)).decode())


def figures(bayer):
    """Flat [RA deg, Dec deg, RA deg, Dec deg, ...], two points per line segment."""
    out, seen = [], set()
    for con, paths in FIGURES.items():
        for path in paths.split(';'):
            pts = []
            for tok in path.split():
                name, _, other = tok.partition('_')
                if (other or con, name) not in bayer:
                    sys.exit(f'constellation figure {con}: no star {tok}')
                pts.append(min(bayer[(other or con, name)])[1:])
            for a, b in zip(pts, pts[1:]):
                if (a, b) not in seen and (b, a) not in seen:
                    seen.add((a, b))
                    out += [round(v, 3) for v in a + b]
    return out


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
    bayer = {}
    data = dict(magStars=MAG_STARS, stars=stars(bayer), galaxies=galaxies(), lines=figures(bayer))
    text = ('// Catalogue sky. Stars: HYG database v4.1 (astronexus). Galaxies: OpenNGC (Mattia Verga). Both CC BY-SA 4.0, as is this file.\n'
            'window.LASILLA_SKY = ' + json.dumps(data, separators=(',', ':'), ensure_ascii=False) + ';\n')
    out_path.write_text(text)
    print(f"{out_path}: {len(text)} bytes, {data['stars']['n']} stars to mag {MAG_STARS}, {len(data['galaxies'])} galaxies to mag {MAG_GALAXIES}, "
          f"{len(data['lines']) // 4} constellation line segments")
    print('brightest galaxies:', [(g[6], g[5], g[2]) for g in data['galaxies'][:8]])


if __name__ == '__main__':
    main()
