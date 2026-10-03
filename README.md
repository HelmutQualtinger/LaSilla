# La Silla Observatory in 3D

A navigable three.js model of ESO's La Silla Observatory in Chile (29°15′S, 70°44′W, 2400 m), with a day/night switch, a Milky Way night sky, moonlight, domes lit in soft amber, switchable weather and three ground surfaces.

**Live: <https://helmutqualtinger.github.io/LaSilla/>** · Source: <https://github.com/HelmutQualtinger/LaSilla>

![La Silla at night: amber-lit domes along the ridge under the Milky Way](docs/night.jpg)

## Run it

Use the live page above, or open `index.html` in a browser. It needs an internet connection, because three.js is loaded from a CDN.

If the page does not load when opened directly, serve the folder instead:

```sh
python3 -m http.server 8377
```

Then open <http://127.0.0.1:8377/>.

## Controls

| Input | Action |
|---|---|
| Drag / right-drag / scroll | Orbit / pan / zoom |
| `W` `A` `S` `D` or arrow keys | Fly |
| `N` | Day / night |
| `T` | Cycle ground: meadow, desert, glacier |
| `1` `2` `3` `4` | Toggle clouds, rain, snow, fog (they combine) |
| `G` | Stargaze: stand on the ridge and look up at the galactic core |
| `H` | Back to the overview |
| `L` | Toggle labels |
| `R` | Toggle the automatic orbit (on at start) |

Click a label, or a name in the list on the left, to fly to that telescope.

Add flags to the URL to start in a given state, for example `index.html#day`, `#desert`, `#snow` or `#day-desert-fog-still`. The page opens at night on the glacier surface; the flags are `day`, `still` (start without the automatic orbit), `meadow`, `desert`, `glacier`, `clouds`, `rain`, `snow` and `fog`.

## What is real and what is not

- **Real:** the terrain (SRTM elevation data), the positions and footprints of the buildings, and the roads (OpenStreetMap). The sky is oriented for La Silla's latitude, and a handful of bright southern stars, the Magellanic Clouds and the galactic centre sit where they belong.
- **Stylised:** the telescope buildings are simplified shapes, not architectural replicas. The Milky Way and most stars are procedural.
- **Artistic licence:** the amber lighting (a working observatory is kept dark), the meadow and glacier surfaces, and the weather. The real mountain is desert and has clear skies most nights of the year.

## Files

| File | Contents |
|---|---|
| `index.html` | The whole application: markup, styles and one script |
| `data.js` | Generated elevation grid and map data; must stay next to `index.html` |
| `tools/build_data.py` | Regenerates `data.js` from elevation tiles and OpenStreetMap (needs numpy and Pillow); its inputs are cached in `tools/cache/` |
| `docs/` | README screenshot and `preview.jpg`, the 1200×630 image used for link previews |
| `CLAUDE.md` | Architecture notes for working on the code |

## Data credits

- Terrain: SRTM, via the Mapzen terrain tiles hosted on AWS.
- Buildings and roads: © OpenStreetMap contributors, ODbL.
