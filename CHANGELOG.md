# Changelog

## 0.2.3

- Fix: dragging a device from front to rear (or back) made it invisible mid-drag - it
  stayed structurally inside its own source `<svg>`, so it rendered underneath the
  other panel once it overlapped it instead of over it. Replaced the in-SVG transform
  with a free-floating HTML "ghost" fixed to `<body>` that tracks the pointer; the
  original block just dims in place while dragging, exactly like before.
- Fix: the rear elevation only ever showed a device type's `rear_image`, leaving
  shallow devices without one (e.g. PDUs) blank on the rear view even when a perfectly
  usable `front_image` exists. Full-depth devices are unaffected (their rear view still
  only shows their own rear image, or nothing - showing the front picture there would
  be wrong); only non-full-depth devices now fall back to the front image on the rear
  view.
- Shorten the drag-hint badge text above the elevation (the German translation in
  particular had gotten too long for the badge).

## 0.2.2

- Drag-and-drop now supports dragging a device from the front elevation onto the rear
  one (and back), reassigning its face. Front and rear share one coordinate system
  (same unit height, rack offset, ...), just placed side by side on screen, so the
  existing delta-based drag math is already valid for a cross-panel drop - only the
  target face needed detecting (via `elementFromPoint` at drop time) and sending along.
  Fixed a related bug along the way: without `pointer-events: none` on the dragged
  block during the drag, `elementFromPoint` would always hit the dragged block itself
  rather than the panel underneath, so the cross-face drop would never have been
  detected; pointer capture keeps delivering move/up events to it regardless.

## 0.2.1

- Rework PNG export: instead of rasterizing the SVG export via `<img>`/`<canvas>`
  (fragile - any malformed SVG or cross-origin image reference could fail the whole
  export with an opaque error), draw the elevation directly onto a `<canvas>` from
  plain pixel geometry (`export/data/`), the same approach netbox-topology-views uses.
  Device type images are fetched individually as same-origin blobs; a single image
  failing to load only drops that picture instead of aborting the export. Added a
  combined front+rear PNG option to the Export menu.

## 0.2.0

- Fix: several multi-line `{# ... #}` template comments rendered as literal text on
  the page instead of being stripped, because Django's comment-tag regex doesn't match
  across newlines. All comments are now single-line. (This was also the most likely
  cause of a reported "PNG export failed" error: the leaked text made the exported SVG
  invalid, so the browser couldn't decode it as an image.)
- Add German translation (`locale/de/`). English remains the source language and needs
  no catalog; both are already listed in NetBox's own language selector.
- Center the "+ Add device" hint on empty rack units instead of right-aligning it.
- Add SVG/PNG/draw.io export for rack concepts.
- Fix drag-and-drop reorder: NetBox sets `CSRF_COOKIE_HTTPONLY`, so the reorder POST's
  CSRF token now comes from a rendered `{% csrf_token %}` input instead of the
  (JS-invisible) cookie.
- Add per-type component tabs (Interfaces, Front/Rear Ports, Console (Server) Ports,
  Power Ports/Outlets) on the concept device page, mirroring real `dcim.Device` pages.
- Copying a real rack (or merging two real racks) into a concept now also copies
  internal cabling as ConceptCables.
- Show the peer device/port in component connection columns.
- Fix `IntegrityError` when merging two real racks: `airflow`/`face` can be `NULL` on
  a real `Rack`/`Device` but not on the corresponding concept fields.
- Add rack cabling: `ConceptComponent`, `ConceptCable`, device-type component sync,
  patch panel front/rear pass-through mapping.
- Add click-to-add on empty rack units, dropping the separate "Add planned device"
  button.
- Add images/labels view toggle and clean up device label styling on the elevation.
- Fix rack elevation overlap; add device images to elevation blocks.
- Add rack/concept merge (2 racks or 2 concepts → 1), and a size override when copying
  a real rack into a concept.

## 0.1.0

Initial release: rack concept planning, copy/clone/merge/deploy flows, drag-and-drop
elevation, partial-width devices, REST API.
