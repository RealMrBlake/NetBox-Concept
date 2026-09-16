/*
 * Drag & drop for concept rack elevations.
 *
 * netbox-reorder-rack cannot be reused here: it moves dcim.Device rows, and a concept
 * deliberately has none. The moves are collected client-side and applied server-side in
 * a single transaction, so an invalid drop leaves the concept exactly as it was.
 */
(function () {
    'use strict';

    const container = document.getElementById('concept-elevations');
    if (!container || container.dataset.editable !== 'true') {
        return;
    }

    const reorderUrl = container.dataset.reorderUrl;
    const startingUnit = parseInt(container.dataset.startingUnit, 10);
    const rackHeight = parseInt(container.dataset.uHeight, 10);
    const descUnits = container.dataset.descUnits === 'true';
    const statusEl = document.getElementById('concept-elevation-status');

    function csrfToken() {
        const match = document.cookie.match(/(^|;)\s*csrftoken\s*=\s*([^;]+)/);
        return match ? decodeURIComponent(match[2]) : '';
    }

    function setStatus(message, isError) {
        if (!statusEl) return;
        statusEl.textContent = message || '';
        statusEl.className = 'small mt-2 ' + (isError ? 'text-danger' : 'text-muted');
    }

    /* Geometry is read back out of the rendered SVG so the server stays the single
       source of truth for sizes. */
    function geometry(svg) {
        const slot = svg.querySelector('.unit-slot');
        if (!slot) return null;
        return {
            unitHeight: slot.height.baseVal.value,
            rackX: slot.x.baseVal.value,
            rackWidth: slot.width.baseVal.value
        };
    }

    function svgPoint(svg, event) {
        const rect = svg.getBoundingClientRect();
        const scale = svg.viewBox.baseVal.width / rect.width;
        return {
            x: (event.clientX - rect.left) * scale,
            y: (event.clientY - rect.top) * scale
        };
    }

    function clamp(value, min, max) {
        return Math.min(Math.max(value, min), max);
    }

    container.querySelectorAll('.concept-elevation').forEach(function (panel) {
        const svg = panel.querySelector('svg');
        const geo = geometry(svg);
        if (!geo) return;

        panel.querySelectorAll('.device-block:not(.opposite)').forEach(function (block) {
            block.addEventListener('pointerdown', onPointerDown);

            function onPointerDown(event) {
                // Let plain clicks through to the device link.
                if (event.button !== 0) return;
                event.preventDefault();

                const start = svgPoint(svg, event);
                const rect = block.querySelector('.device-rect');
                const originX = rect.x.baseVal.value;
                const deviceUnits = parseFloat(block.dataset.uHeight);
                const oldPosition = parseFloat(block.dataset.position);
                const fraction = parseInt(
                    block.dataset.widthFraction || rect.dataset.widthFraction || '1', 10
                );
                let moved = false;
                let dx = 0;
                let dy = 0;

                block.classList.add('dragging');
                block.setPointerCapture(event.pointerId);

                function onMove(moveEvent) {
                    const now = svgPoint(svg, moveEvent);
                    dx = now.x - start.x;
                    dy = now.y - start.y;
                    if (Math.abs(dx) > 3 || Math.abs(dy) > 3) {
                        moved = true;
                    }
                    const snappedY = Math.round(dy / geo.unitHeight) * geo.unitHeight;
                    block.setAttribute('transform', 'translate(' + dx + ' ' + snappedY + ')');
                }

                function onUp() {
                    block.removeEventListener('pointermove', onMove);
                    block.removeEventListener('pointerup', onUp);
                    block.removeEventListener('pointercancel', onUp);
                    block.classList.remove('dragging');

                    if (!moved) {
                        // Treat it as a click: follow the device link.
                        block.removeAttribute('transform');
                        const link = block.querySelector('a');
                        if (link) window.location = link.getAttribute('href');
                        return;
                    }

                    const unitDelta = Math.round(dy / geo.unitHeight) * (descUnits ? 1 : -1);
                    const lowest = startingUnit;
                    const highest = startingUnit + rackHeight - deviceUnits;
                    const newPosition = clamp(oldPosition + unitDelta, lowest, highest);

                    let horizontal = 0;
                    if (fraction > 1) {
                        const newX = originX + dx;
                        const slotWidth = geo.rackWidth / fraction;
                        horizontal = clamp(
                            Math.round((newX - geo.rackX) / slotWidth), 0, fraction - 1
                        );
                    }

                    submit(block, newPosition, fraction > 1 ? horizontal : null);
                }

                block.addEventListener('pointermove', onMove);
                block.addEventListener('pointerup', onUp);
                block.addEventListener('pointercancel', onUp);
            }
        });
    });

    function submit(block, position, horizontalPosition) {
        const move = {
            id: parseInt(block.dataset.deviceId, 10),
            position: position
        };
        if (horizontalPosition !== null) {
            move.horizontal_position = horizontalPosition;
        }

        setStatus('Saving…', false);

        fetch(reorderUrl, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': csrfToken()
            },
            credentials: 'same-origin',
            body: JSON.stringify({ devices: [move] })
        })
            .then(function (response) {
                return response.json().then(function (body) {
                    return { ok: response.ok, body: body };
                });
            })
            .then(function (result) {
                if (result.ok) {
                    window.location.reload();
                } else {
                    block.removeAttribute('transform');
                    setStatus(result.body.error || 'The move was rejected.', true);
                }
            })
            .catch(function () {
                block.removeAttribute('transform');
                setStatus('The move could not be saved.', true);
            });
    }
})();
