/*
 * "Export as PNG" - draws the elevation straight onto a <canvas> using the plain
 * pixel geometry from the export/data/ endpoint, the same approach
 * netbox-topology-views uses for its own PNG export (native canvas drawing rather
 * than rasterizing an SVG image). A device type image only ever reaches the canvas
 * via a same-origin fetch() -> blob() -> Image, never via <img src="blob:<svg>">,
 * so there's no SVG document whose validity (and thus whether it even decodes at
 * all) the export depends on, and one broken/cross-origin image only drops that one
 * picture instead of failing the whole export.
 */
(function () {
    'use strict';

    const SCALE = 2; // render at 2x so the PNG stays crisp
    const TITLE_HEIGHT = 26;
    const FACE_GAP = 40;
    const MARGIN = 10;

    document.querySelectorAll('.concept-export-png').forEach(function (link) {
        link.addEventListener('click', function (event) {
            event.preventDefault();
            exportPng(link.dataset.dataUrl, link.dataset.filename || 'export.png', link.dataset.faces || 'both');
        });
    });

    function exportPng(dataUrl, filename, faces) {
        fetch(dataUrl, { credentials: 'same-origin' })
            .then(function (response) {
                if (!response.ok) {
                    throw new Error('Could not load the elevation data (' + response.status + ').');
                }
                return response.json();
            })
            .then(function (data) {
                const elevations = faces === 'both' ? [data.front, data.rear] : [
                    faces === 'front' ? data.front : data.rear
                ];
                return renderCanvas(elevations).then(function (canvas) {
                    downloadCanvas(canvas, filename);
                });
            })
            .catch(function (error) {
                window.alert('The PNG could not be generated: ' + error.message);
            });
    }

    function collectImageUrls(elevations) {
        const urls = new Set();
        elevations.forEach(function (elevation) {
            elevation.blocks.forEach(function (block) {
                if (block.image_url) urls.add(block.image_url);
            });
        });
        return Array.from(urls);
    }

    function loadImage(url) {
        return fetch(url, { credentials: 'same-origin' })
            .then(function (response) {
                if (!response.ok) throw new Error('fetch failed');
                return response.blob();
            })
            .then(function (blob) {
                return new Promise(function (resolve, reject) {
                    const objectUrl = URL.createObjectURL(blob);
                    const img = new Image();
                    img.onload = function () {
                        URL.revokeObjectURL(objectUrl);
                        resolve(img);
                    };
                    img.onerror = function () {
                        URL.revokeObjectURL(objectUrl);
                        reject(new Error('decode failed'));
                    };
                    img.src = objectUrl;
                });
            });
    }

    function renderCanvas(elevations) {
        const totalWidth = elevations.reduce(function (sum, e) { return sum + e.width; }, 0)
            + FACE_GAP * (elevations.length - 1) + MARGIN * 2;
        const totalHeight = TITLE_HEIGHT + Math.max.apply(null, elevations.map(function (e) { return e.height; }))
            + MARGIN * 2;

        const canvas = document.createElement('canvas');
        canvas.width = totalWidth * SCALE;
        canvas.height = totalHeight * SCALE;
        const ctx = canvas.getContext('2d');
        ctx.scale(SCALE, SCALE);
        ctx.fillStyle = '#ffffff';
        ctx.fillRect(0, 0, totalWidth, totalHeight);

        const imageUrls = collectImageUrls(elevations);
        return Promise.allSettled(imageUrls.map(loadImage)).then(function (results) {
            const images = {};
            results.forEach(function (result, index) {
                if (result.status === 'fulfilled') {
                    images[imageUrls[index]] = result.value;
                }
            });

            let offsetX = MARGIN;
            elevations.forEach(function (elevation) {
                drawElevation(ctx, elevation, offsetX, MARGIN + TITLE_HEIGHT, images);
                offsetX += elevation.width + FACE_GAP;
            });

            return canvas;
        });
    }

    function roundRect(ctx, x, y, width, height, radius) {
        ctx.beginPath();
        ctx.moveTo(x + radius, y);
        ctx.arcTo(x + width, y, x + width, y + height, radius);
        ctx.arcTo(x + width, y + height, x, y + height, radius);
        ctx.arcTo(x, y + height, x, y, radius);
        ctx.arcTo(x, y, x + width, y, radius);
        ctx.closePath();
    }

    function drawImageCover(ctx, img, x, y, width, height) {
        const scale = Math.max(width / img.width, height / img.height);
        const drawWidth = img.width * scale;
        const drawHeight = img.height * scale;
        ctx.drawImage(img, x + (width - drawWidth) / 2, y + (height - drawHeight) / 2, drawWidth, drawHeight);
    }

    function drawElevation(ctx, elevation, offsetX, offsetY, images) {
        ctx.fillStyle = '#35404a';
        ctx.font = 'bold 14px -apple-system, "Segoe UI", Roboto, Arial, sans-serif';
        ctx.textAlign = 'center';
        ctx.textBaseline = 'alphabetic';
        ctx.fillText(elevation.face_label, offsetX + elevation.width / 2, offsetY - 8);

        // Unit rows and numbers
        elevation.units.forEach(function (unit) {
            const y = offsetY + unit.y;
            ctx.fillStyle = '#f6f8fa';
            ctx.fillRect(offsetX + elevation.rack_x, y, elevation.rack_width, unit.height);
            ctx.strokeStyle = '#dadfe5';
            ctx.lineWidth = 1;
            ctx.strokeRect(offsetX + elevation.rack_x, y, elevation.rack_width, unit.height);

            ctx.fillStyle = '#808f9c';
            ctx.font = '10px -apple-system, "Segoe UI", Roboto, Arial, sans-serif';
            ctx.textAlign = 'right';
            ctx.textBaseline = 'middle';
            ctx.fillText(String(unit.number), offsetX + elevation.rack_x - 4, y + unit.height / 2);
        });

        // Devices
        elevation.blocks.forEach(function (block) {
            const x = offsetX + block.x;
            const y = offsetY + block.y;
            const image = block.image_url ? images[block.image_url] : null;

            ctx.save();
            ctx.globalAlpha = block.opposite ? 0.35 : 1;
            roundRect(ctx, x, y, block.width, block.height, 2);
            ctx.fillStyle = '#' + block.color;
            ctx.fill();

            if (image) {
                ctx.save();
                roundRect(ctx, x, y, block.width, block.height, 2);
                ctx.clip();
                drawImageCover(ctx, image, x, y, block.width, block.height);
                ctx.restore();
            }
            ctx.restore();

            if (block.show_text) {
                ctx.font = '11px -apple-system, "Segoe UI", Roboto, Arial, sans-serif';
                ctx.textAlign = 'left';
                ctx.textBaseline = 'middle';
                const textX = x + 6;
                const textY = y + block.height / 2;

                if (image) {
                    // Black stroke behind a white fill, same trick as the on-page SVG,
                    // so the label reads over any picture without a solid backing box.
                    ctx.lineWidth = 3;
                    ctx.lineJoin = 'round';
                    ctx.strokeStyle = '#000000';
                    ctx.strokeText(block.label, textX, textY);
                    ctx.fillStyle = '#ffffff';
                    ctx.fillText(block.label, textX, textY);
                } else {
                    ctx.fillStyle = '#' + block.text_color;
                    ctx.fillText(block.label, textX, textY);
                }
            }
        });

        // Rack frame
        ctx.strokeStyle = '#35404a';
        ctx.lineWidth = 2;
        ctx.strokeRect(offsetX + elevation.rack_x, offsetY + 6, elevation.rack_width, elevation.height - 12);
    }

    function downloadCanvas(canvas, filename) {
        canvas.toBlob(function (blob) {
            if (!blob) {
                window.alert('The PNG could not be generated.');
                return;
            }
            const url = URL.createObjectURL(blob);
            const link = document.createElement('a');
            link.href = url;
            link.download = filename;
            document.body.appendChild(link);
            link.click();
            link.remove();
            URL.revokeObjectURL(url);
        }, 'image/png');
    }
})();
