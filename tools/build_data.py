#!/usr/bin/env python3
"""Regenerate data.js (elevation grids + OpenStreetMap layout) for the La Silla model.

    python3 tools/build_data.py            # writes ../data.js
    python3 tools/build_data.py out.js     # writes somewhere else, e.g. to compare

Needs numpy and Pillow. Downloads are cached in tools/cache/; delete a cached file to
refetch it. The committed cache holds the exact inputs data.js was built from, so a run
without network access reproduces it byte for byte. Deleting cache/osm.json pulls the
current OpenStreetMap state, which may have changed (new buildings, renamed telescopes
that no longer match SPEC in index.html).

Downloads go through curl because the python.org Python on macOS often lacks CA
certificates for urllib.
"""
import base64, json, math, subprocess, sys
from pathlib import Path

import numpy as np
from PIL import Image

LAT0, LON0 = -29.2562, -70.7362                     # scene origin, roughly mid-ridge
BBOX = '-29.275,-70.755,-29.240,-70.715'            # south,west,north,east for the OSM query
OVERPASS = ['https://overpass.kumi.systems/api/interpreter', 'https://overpass-api.de/api/interpreter']
TILES = 'https://s3.amazonaws.com/elevation-tiles-prod/terrarium/{z}/{x}/{y}.png'
INNER, OUTER = (13, 400), (10, 400)                 # (zoom, cells): 16.7 m and 133 m per cell

ROOT = Path(__file__).resolve().parent
CACHE = ROOT / 'cache'
C = math.cos(math.radians(LAT0))


def curl(url, dest, *extra):
    subprocess.run(['curl', '-sf', '-m', '90', '-A', 'LaSilla3D-model/1.0 (personal project)', *extra, '-o', str(dest), url], check=True)


def gpx(lat, lon, z):
    """Web-Mercator global pixel coordinates at zoom z."""
    n = 256 * 2**z
    return (lon + 180) / 360 * n, (1 - math.asinh(math.tan(math.radians(lat))) / math.pi) / 2 * n


def tile(z, x, y):
    fn = CACHE / f'tile_{z}_{x}_{y}.png'
    if not fn.exists():
        curl(TILES.format(z=z, x=x, y=y), fn)
    a = np.asarray(Image.open(fn).convert('RGB')).astype(np.float64)
    return a[..., 0] * 256 + a[..., 1] + a[..., 2] / 256 - 32768          # Terrarium encoding, metres


def grid(z, n):
    """n x n elevation window centred on the origin, as base64 uint16 decimetres (row 0 = north)."""
    cx, cy = gpx(LAT0, LON0, z)
    x0, y0 = int(round(cx - n / 2)), int(round(cy - n / 2))
    tx0, ty0, tx1, ty1 = x0 // 256, y0 // 256, (x0 + n - 1) // 256, (y0 + n - 1) // 256
    mosaic = np.block([[tile(z, tx, ty) for tx in range(tx0, tx1 + 1)] for ty in range(ty0, ty1 + 1)])
    h = mosaic[y0 - ty0 * 256: y0 - ty0 * 256 + n, x0 - tx0 * 256: x0 - tx0 * 256 + n]
    mpp = 156543.03392 * C / 2**z                                         # ground metres per pixel at LAT0
    ox, oz = (x0 + 0.5 - cx) * mpp, (y0 + 0.5 - cy) * mpp                 # scene x/z of cell (0, 0)
    print(f'zoom {z}: {n} cells of {mpp:.2f} m = {n * mpp / 1000:.1f} km, elevation {h.min():.0f}..{h.max():.0f} m')
    q = np.clip(np.round(h * 10), 0, 65535).astype('<u2')
    return dict(n=n, cell=round(mpp, 4), ox=round(ox, 2), oz=round(oz, 2), b64=base64.b64encode(q.tobytes()).decode())


def loc(lat, lon):
    """Scene coordinates [x east, z south] in metres."""
    x, y = gpx(lat, lon, 0)
    x0, y0 = gpx(LAT0, LON0, 0)
    m = 156543.03392 * C
    return [round((x - x0) * m, 1), round((y - y0) * m, 1)]


def osm():
    fn = CACHE / 'osm.json'
    if not fn.exists():
        q = (f'[out:json][timeout:60];(nwr["man_made"~"telescope|observatory"]({BBOX});'
             f'nwr["building"]({BBOX});way["highway"]({BBOX}););out geom;')
        for url in OVERPASS:
            try:
                curl(url, fn, '--data-urlencode', 'data=' + q)
                json.loads(fn.read_text())
                break
            except (subprocess.CalledProcessError, ValueError):
                fn.unlink(missing_ok=True)
        else:
            sys.exit('all Overpass servers failed')
    return json.loads(fn.read_text())['elements']


def main():
    out_path = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT.parent / 'data.js'
    CACHE.mkdir(exist_ok=True)
    inner, outer = grid(*INNER), grid(*OUTER)
    buildings, roads, nodes = [], [], []
    for e in osm():
        t = e.get('tags', {})
        ring = lambda geom: [loc(g['lat'], g['lon']) for g in geom]
        if e['type'] == 'way' and 'highway' in t:
            roads.append(dict(k=t['highway'], p=ring(e['geometry'])))
        elif e['type'] == 'way' and 'building' in t:
            buildings.append(dict(name=t.get('name', ''), alt=t.get('alt_name', ''), kind=t['building'], mm=t.get('man_made', ''), p=ring(e['geometry'])[:-1]))
        elif e['type'] == 'relation':                                     # multipolygon (the hotel): keep the outer rings
            for m in e['members']:
                if m.get('role') == 'outer' and 'geometry' in m:
                    buildings.append(dict(name=t.get('name', ''), alt='', kind=t['building'], p=ring(m['geometry'])[:-1]))
        elif e['type'] == 'node':
            nodes.append(dict(name=t.get('name', ''), p=loc(e['lat'], e['lon'])))
    data = dict(lat0=LAT0, lon0=LON0, inner=inner, outer=outer, buildings=buildings, roads=roads, nodes=nodes)
    text = ('// La Silla site data. Terrain: Mapzen/AWS Terrain Tiles (SRTM). Buildings & roads: (c) OpenStreetMap contributors, ODbL.\n'
            'window.LASILLA = ' + json.dumps(data, separators=(',', ':')) + ';\n')
    out_path.write_text(text)
    print(f'{out_path}: {len(text)} bytes, {len(buildings)} buildings, {len(roads)} roads, {len(nodes)} nodes')


if __name__ == '__main__':
    main()
