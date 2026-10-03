# Prompt: recreate the La Silla 3D model

Paste everything below the line into a coding agent that can run shell commands, fetch from the web and drive a browser. It is written to produce the app in this repository from an empty folder.

---

Build a navigable 3D model of ESO's La Silla Observatory in Chile as a static web page with three.js, and publish it on GitHub Pages. I want something I can fly around that looks impressive at night: the Milky Way overhead and the telescope domes glowing in soft amber light. The geography should be real, not invented; the telescope buildings may be stylised.

## Deliverables

- `index.html`: the whole app in one file (markup, CSS, one inline ES module). No build step, no package manager. Load three.js r170 and `OrbitControls` from jsDelivr through an import map.
- `sky.js`: generated star and galaxy catalogue data, loaded the same way as `data.js`, plus `tools/build_sky.py` that produces it.
- `data.js`: generated site data, loaded as a classic `<script>` that sets `window.LASILLA`, so the page needs no `fetch` and can also be opened from disk.
- `tools/build_data.py` plus `tools/cache/`: the script that generates `data.js` and the raw inputs it downloaded, so the data can be rebuilt byte for byte offline.
- `README.md` with a night screenshot, `docs/preview.jpg` (1200×630 social card), and Open Graph / Twitter meta tags that point at the published URL.
- A public GitHub repository with Pages serving `main` from the root. Ask me before creating the repository or pushing.

## Real data

Use real elevation and real map data; do not model the mountain by hand.

- **Origin:** latitude −29.2562, longitude −70.7362 (mid-ridge). Scene units are metres: x east, z south, y = elevation − 2300.
- **Elevation:** Terrarium PNG tiles from `https://s3.amazonaws.com/elevation-tiles-prod/terrarium/{z}/{x}/{y}.png` (height = R·256 + G + B/256 − 32768). Take a 400×400 window at zoom 13 (about 16.7 m per cell, 6.7 km across) and another at zoom 10 (about 133 m per cell, 53 km across), both centred on the origin. Store each as base64 little-endian uint16 decimetres, row 0 north, with the scene coordinates of cell (0,0) and the cell size.
- **Layout:** one Overpass query over the bounding box (−29.275, −70.755, −29.240, −70.715) for `man_made~telescope|observatory`, every `building`, and every `highway` way, with geometry. Keep building footprints (name, alt_name, building, man_made), road polylines with their highway type, and telescope nodes. Project with Web Mercator scaled by cos(latitude of the origin).
- Download with `curl`, cache every response on disk, and try a second Overpass mirror if the first refuses.
- Sanity check: the ESO 3.6 m telescope should land near (436, 532) at about 2403 m, and the hotel about 100 m lower at the north-west end of the ridge.

## Terrain

- One mesh on a non-uniform grid: 6 m cells within ±1 km of the origin, each cell 7 % larger than the last beyond that, out to 26 km. Sample the fine grid bicubically, blend into the coarse grid between 2.3 and 3.1 km, and add a few metres of procedural noise near the site for sub-SRTM detail.
- Cut the drivable roads into the slope: resample each road every 3 m, smooth its height along its length, and pull nearby terrain to that height so roads sit on a bench.
- Flatten a circular platform under every building, processing the largest footprints first so small neighbours adopt the level of the big one beside them.
- Keep a function that returns the height of the rendered mesh exactly (same triangle split), and use it for the camera's ground clamp and for viewpoints.
- Paint roads and gravel aprons into one large canvas texture covering about ±1 km and mix it into the terrain material in the shader. Roads are texture, not geometry, which avoids z-fighting.
- Three switchable ground surfaces, each with its own per-vertex colours (driven by slope and noise) and its own tileable detail texture drawn on a canvas: **meadow** (grass blades, wildflowers), **desert** (gravel, scrub; the real one), **glacier** (snow, blue ice, crevasse lines, dark rock on steep slopes).

## Buildings

- Walk the footprints. Named telescopes get a model; everything else is the footprint extruded to a plausible height with a flat roof.
- **Domes:** a beige drum with a white hemispherical dome on a short skirt, an observing-slit band running from the base over the zenith, and a balcony with railing on the larger ones. A round footprint becomes a drum of that radius; a rectangular one keeps its extruded building with the dome on top.
- **Specials:** the NTT is an octagonal metallic enclosure, not a dome. SEST is a 15 m dish on a pedestal with a subreflector on four struts. The Danish 1.54 m has a faceted silver dome. The CAT is a slim tower beside the 3.6 m.
- Telescopes to label, with a one-line fact each, all of which must be true: ESO 3.6-metre (since 1977, HARPS and NIRPS), CAT (1.4 m, retired 1998), NTT (3.58 m, 1989, active optics), Euler (Swiss 1.2 m, 1998, CORALIE), MPG/ESO 2.2-metre (1984; WFI, FEROS, GROND), Danish 1.54-metre (since 1979), ESO Schmidt (1 m, 1971), BlackGEM (three 0.65 m), ESO 1-metre (1966, first on the mountain), REM (0.6 m robotic), ESO 1.52-metre (1968, retired 2002), TRAPPIST-South (0.6 m, 2010), SEST (1987–2003), Hotel La Silla.
- Link a telescope to English Wikipedia only if it has its own article. Check each title with the MediaWiki API (`action=query&redirects=1`); several plausible titles only redirect to the general La Silla page and must not be linked.

## Sky and light

- **Day:** a very dark blue high-altitude sky, deep navy overhead with pale haze only in a narrow band at the horizon, a sun disc, exponential fog that matches the horizon colour, and sun shadows from the buildings.
- **Night sky:** a procedural Milky Way with a bright bulge, dust lanes and the Coalsack, the two Magellanic Clouds and the Carina nebula, all at their real positions. Define it in galactic coordinates and orient it properly for the site's latitude and a sidereal time that puts the galactic centre about 20° up in the east-south-east. Let the sky turn very slowly.
- **Stars and galaxies from catalogues, not random:** every star down to magnitude 7.5 from the HYG database (about 25,800; position, magnitude and B−V colour index, packed into 6 bytes each), drawn as twinkling points sized by magnitude and tinted by colour index; and every galaxy down to magnitude 12 from OpenNGC including its addendum (about 1,050), drawn as soft ellipses with the catalogue size, axis ratio and position angle. Skip the two Magellanic Clouds in the galaxy list since the Milky Way texture draws them. Check the coordinate conversion: Sirius must land at galactic l = 227.23°, b = −8.89°. Credit both catalogues (CC BY-SA 4.0).
- **Performance of the sky:** render the Milky Way once at start-up into a texture in galactic longitude and latitude and sample it from the dome shader. Computing the noise per pixel per frame is too slow for phones.
- **Moonlight:** at night a cool blue-white moon in the north lights the scene and casts shadows; draw its disc and glare in the sky. Use one shadow-casting directional light that is the sun by day and jumps to the moon's direction during the transition while its intensity is zero.
- **Amber domes:** every building glows amber from the base upward, fading toward the top, using emissive light driven by a per-vertex height attribute baked per building; and one amber point light per telescope throws a soft pool onto the ground. Slits turn dark at night as if open. Plain buildings glow only faintly.
- The day/night switch is a smooth transition of a couple of seconds with a brief orange twilight.

## Weather

Four independent toggles that fade in and can be combined:

- **Clouds:** drifting procedural clouds on a second sky dome, scattered when on their own.
- **Rain:** streaks falling around the camera.
- **Snow:** drifting flakes around the camera.
- **Fog:** visibility down to roughly a kilometre.

Rain and snow bring full overcast: they dim the light, grey the sky and hide the stars. Keep the particles in a fixed box that wraps around the camera in the vertex shader.

## Controls and interface

- Orbit, pan and zoom with the mouse or touch; `W A S D` and arrow keys fly; the camera never goes below the ground.
- Automatic slow orbit, on at start, about one turn in 30 seconds.
- Buttons with keyboard shortcuts: Labels (`L`), Rotate (`R`), Stargaze (`G`, stand on the ridge at eye level looking up at the galactic centre, and switch to night), Overview (`H`), weather toggles (`1`–`4`), ground surface (`T` cycles), Day/Night (`N`).
- A title panel with the site's coordinates and a "Source on GitHub" link; a list of the telescopes with their facts and Wikipedia links, where clicking an entry flies to it; HTML labels over the telescopes that are clickable and hide when they would overlap; a compass; a hint bar; data credits.
- **Defaults:** open at night, on the glacier surface, rotating. URL hash flags override: `day`, `still`, `meadow`, `desert`, `clouds`, `rain`, `snow`, `fog`, in any combination.
- **Phones:** below about 720 px wide, hide the hint and credits, shrink the title, and put the controls behind two corner buttons: the building list at the top left and a hamburger settings menu at the top right. Only one opens at a time; tapping the scene or picking a building closes it. Use a wider lens in portrait. On touch devices halve the big textures and the shadow map and cap the pixel ratio at 1.5.
- If start-up fails (CDN blocked, no WebGL, an exception), say so on the loading screen instead of hanging.
- Visual style: dark translucent panels with blur, a serif small-caps title, amber as the accent colour.

## Things that are easy to get wrong

- three.js caches shader programs by the source text of `onBeforeCompile`. If each material's glow strength is baked into the shader as a constant, every material silently gets the first one's value. Pass it as a uniform.
- Additive star points marked transparent are drawn after the scene and show through buildings. Keep them in the opaque queue (non-transparent, additive blending, depth test off, low render order) so they draw right after the sky dome. The cloud dome needs the same treatment with custom blending.
- Custom sky shaders must include the tone-mapping and colour-space chunks, or they will not match the fog colour at the horizon.
- `requestAnimationFrame` does not run in a hidden or occluded browser tab. Split the loop into a scheduler and a `tick(dt)` function and expose `tick` on a debug handle so automated checks can step the scene by hand. Test the phone layout by loading the page in a 390 px wide iframe.
- Do not hand-write telescope positions or facts from memory; take positions from the map data and verify every fact and link.

## How to work

Build it in this order and look at each stage in a real browser before moving on: data script, terrain, buildings, day sky and lighting, night sky and amber glow, weather, interface, phone layout, publishing. Take screenshots by day and by night, close up and from the overview, and fix what looks wrong. When you report back, tell me plainly what you checked in a browser and what you did not.
