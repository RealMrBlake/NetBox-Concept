# Changelog

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
