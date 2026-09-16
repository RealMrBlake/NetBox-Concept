/*
 * "Export as PNG" - fetches the same standalone SVG the SVG download link points to
 * and rasterizes it client-side via <canvas>. Deliberately no server-side image
 * library involved: a NetBox plugin shouldn't need one just for this, and every
 * browser can already turn an SVG into a PNG on its own.
 */
(function () {
    'use strict';

    const SCALE = 2; // render at 2x so the PNG stays crisp

    document.querySelectorAll('.concept-export-png').forEach(function (link) {
        link.addEventListener('click', function (event) {
            event.preventDefault();
            exportPng(link.dataset.svgUrl, link.dataset.filename || 'export.png');
        });
    });

    function exportPng(svgUrl, filename) {
        fetch(svgUrl, { credentials: 'same-origin' })
            .then(function (response) {
                if (!response.ok) {
                    throw new Error('Could not load the SVG (' + response.status + ').');
                }
                return response.text();
            })
            .then(function (svgText) {
                rasterize(svgText, filename);
            })
            .catch(function () {
                window.alert('The PNG could not be generated.');
            });
    }

    function rasterize(svgText, filename) {
        const sizeMatch = svgText.match(/<svg[^>]*\swidth="([\d.]+)"[^>]*\sheight="([\d.]+)"/);
        const width = sizeMatch ? parseFloat(sizeMatch[1]) : 800;
        const height = sizeMatch ? parseFloat(sizeMatch[2]) : 600;

        const svgBlob = new Blob([svgText], { type: 'image/svg+xml;charset=utf-8' });
        const svgUrl = URL.createObjectURL(svgBlob);
        const img = new Image();

        img.onload = function () {
            URL.revokeObjectURL(svgUrl);

            const canvas = document.createElement('canvas');
            canvas.width = width * SCALE;
            canvas.height = height * SCALE;
            const ctx = canvas.getContext('2d');
            // The SVG itself has a white background, but that's inside a <style> block,
            // which some rasterizers (older WebKit) ignore when drawing to canvas.
            ctx.fillStyle = '#ffffff';
            ctx.fillRect(0, 0, canvas.width, canvas.height);
            ctx.drawImage(img, 0, 0, canvas.width, canvas.height);

            canvas.toBlob(function (blob) {
                if (!blob) {
                    window.alert('The PNG could not be generated.');
                    return;
                }
                const downloadUrl = URL.createObjectURL(blob);
                const link = document.createElement('a');
                link.href = downloadUrl;
                link.download = filename;
                document.body.appendChild(link);
                link.click();
                link.remove();
                URL.revokeObjectURL(downloadUrl);
            }, 'image/png');
        };

        img.onerror = function () {
            URL.revokeObjectURL(svgUrl);
            // Most likely a device type image from a different origin without
            // permissive CORS headers, which taints the canvas and blocks toBlob().
            window.alert('The PNG could not be generated. This can happen when a device '
                + 'type image is hosted on a different domain without CORS enabled.');
        };

        img.src = svgUrl;
    }
})();
