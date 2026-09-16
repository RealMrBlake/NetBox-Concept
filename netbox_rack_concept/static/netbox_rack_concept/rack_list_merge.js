/*
 * "Merge into concept" button on the real dcim Rack list.
 *
 * The button lives outside NetBox's own bulk-action <form> (plugin list buttons render
 * in the page header, the row checkboxes further down in the table's form), so it
 * can't rely on a normal form submit to collect the selection. Instead it reads the
 * checked "pk" checkboxes straight out of the DOM - the same input name NetBox's own
 * bulk-edit/bulk-delete buttons use - and forwards up to two of them as query
 * parameters to the merge page, which pre-fills its two rack fields from that.
 */
(function () {
    'use strict';

    const button = document.getElementById('concept-merge-racks-button');
    if (!button) {
        return;
    }

    function checkedRackIds() {
        return Array.prototype.map.call(
            document.querySelectorAll('input[name="pk"]:checked'),
            function (el) { return el.value; }
        );
    }

    button.addEventListener('click', function (event) {
        const ids = checkedRackIds();
        if (ids.length === 0) {
            // Nothing selected: fall through to the plain link, let the user pick
            // both racks by hand on the merge page instead.
            return;
        }
        if (ids.length > 2) {
            event.preventDefault();
            window.alert(
                'Please select exactly two racks to merge (you selected ' + ids.length + ').'
            );
            return;
        }

        event.preventDefault();
        const url = new URL(button.dataset.mergeUrl, window.location.origin);
        url.searchParams.set('rack_bottom', ids[0]);
        if (ids.length === 2) {
            url.searchParams.set('rack_top', ids[1]);
        }
        window.location.href = url.toString();
    });
})();
