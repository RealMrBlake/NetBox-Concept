# NetBox Rack Concept

Rack blueprints for NetBox. A "rack concept" is a fully planned rack including
its equipment — but **not** a real rack and **no** real devices. Concepts
therefore appear neither in the rack list nor in the device list, do not skew
utilisation reports and do not consume serial numbers or IP addresses.

Once the plan is final, a concept is turned into real NetBox objects with one
click — once or twenty times.

| | |
|---|---|
| **Plugin name** | `netbox_rack_concept` |
| **Package** | `netbox-rack-concept` |
| **NetBox** | `4.6.0` – `4.7.x` |
| **Python** | `>=3.12` |
| **Repository** | <https://git.mrblake.cc/MrBlake/NetBox-Concept> |

## Features

| Workflow | Where |
|---|---|
| Real rack → concept | **Copy to concept** button on the rack detail page. Width, height and starting unit of the concept rack are freely selectable; devices that no longer fit are skipped and reported as warnings |
| Concept → concept (variant) | **Clone concept** button on the concept detail page |
| 2 concepts → 1 larger concept | **Merge** in the menu or **Merge with another** on the concept detail page — e.g. stacks two half-height racks into a full one; the top concept is shifted up by the height of the bottom one, both sources stay unchanged |
| 2 real racks → 1 new concept | **Merge into concept** above the real rack list. Select two racks via checkbox and click the button — you land on the same merge form, pre-filled with the two real racks as sources |
| Concept → real racks (n times) | **Deploy to NetBox** button, with naming scheme `DC1-R{n:02d}` |
| Create a concept manually | Menu **Rack Concepts → Rack Concepts → +** |

In addition:

- **Drag & drop elevation** – move devices with the mouse, including from the front to the rear view (and vice versa). Everything is validated server-side; an invalid move is rejected and changes nothing.
- **Devices with image and label** – device type front/rear images are shown in the elevation with the device name as white, black-outlined text. On the rear, a **full-depth** device only shows its own rear image; a **non-full-depth** device without a rear image (e.g. a power strip) shows its front image. A dropdown switches between "Images and labels", "Images only" and "Labels only" — just like real racks in NetBox, remembered in the browser.
- **Partial widths** (1/1, 1/2, 1/3, 1/4 plus horizontal slot position), matching the partial-width feature of `netbox_utilities`.
- **Tenant and tenant group** on the concept and on every planned device.
- **Placeholders without device type** – reserved space with only a height.
- **Click on an empty U** opens "Add planned device", pre-filled with position and face — just like a real rack elevation.
- **Cabling of concept devices, 1:1 like real devices** – the device detail page has the same tabs as a real `dcim.Device` (interfaces, front/rear ports, console ports, console server ports, power ports, power outlets; tabs only shown when populated). **Sync components** copies them 1:1 from the device type's component templates, including front ↔ rear mapping of patch panels. **Connect** on every uncabled component creates a concept cable. An **Add Components** dropdown creates new components per type — needed for placeholders without a device type.
- **Export** – **Export** button above the elevation: front or rear as standalone **SVG**, as **PNG** (single or both sides), and the whole concept as a **draw.io** diagram (`.drawio`). PNG is drawn directly on a `<canvas>` in the browser; device type images are fetched individually, so a failing image only affects that one image. No server-side image library is needed.
- Full REST API, filters, CSV import/export, bulk edit, changelog, journal, tags, custom fields and global search — like any core object.

## Compatibility

- NetBox `4.6.0` – `4.7.x`
- Python `>=3.12`
- Optional: [Netbox-Utilities](https://git.mrblake.cc/MrBlake/Netbox-Utilities) for partial widths
- Optional: `netbox-reorder-rack` — **v1.1.5 requires NetBox 4.7**; on NetBox 4.6 pin `netbox-reorder-rack<1.1.5`

## Installation

All paths assume a standard installation under `/opt/netbox`.

### 1. Install the package

```bash
/opt/netbox/venv/bin/pip install --upgrade --force-reinstall \
  "git+https://git.mrblake.cc/MrBlake/NetBox-Concept.git@main"
```

For reproducible production installs, replace `main` with a release tag or a
full commit ID.

### 2. Add the plugin to `local_requirements.txt`

This makes `upgrade.sh` reinstall the plugin automatically on every NetBox upgrade:

```bash
grep -qxF "git+https://git.mrblake.cc/MrBlake/NetBox-Concept.git@main" /opt/netbox/local_requirements.txt \
  || echo "git+https://git.mrblake.cc/MrBlake/NetBox-Concept.git@main" | sudo tee -a /opt/netbox/local_requirements.txt
```

If the repository is private, the NetBox server needs a read-only deploy token
or an SSH key. Do not store credentials in `local_requirements.txt`.

### 3. Enable the plugin

In `/opt/netbox/netbox/netbox/configuration.py`:

```python
PLUGINS = [
    "netbox_rack_concept",
    # optional, in any order:
    "netbox_utilities",
    "netbox_reorder_rack",
]
```

If other plugins are already configured, add `netbox_rack_concept` to the
existing list instead of replacing it. See [Configuration](#configuration) for
optional settings.

### 4. Apply migrations, collect static files, restart

```bash
cd /opt/netbox/netbox
/opt/netbox/venv/bin/python manage.py migrate netbox_rack_concept
/opt/netbox/venv/bin/python manage.py collectstatic --no-input
sudo systemctl restart netbox netbox-rq
```

> If `migrate` cannot apply the bundled migration because base fields differ in
> your NetBox installation: delete `netbox_rack_concept/migrations/0001_initial.py`
> and run `manage.py makemigrations netbox_rack_concept`. The migration was
> written by hand against NetBox 4.6.8.

## Update

```bash
/opt/netbox/venv/bin/pip install --upgrade --force-reinstall --no-deps \
  "git+https://git.mrblake.cc/MrBlake/NetBox-Concept.git@main"

cd /opt/netbox/netbox
/opt/netbox/venv/bin/python manage.py migrate netbox_rack_concept
/opt/netbox/venv/bin/python manage.py collectstatic --no-input
sudo systemctl restart netbox netbox-rq
```

`--force-reinstall` makes pip pick up branch changes even if the package
version has not been bumped.

When NetBox itself is upgraded, `upgrade.sh` reinstalls the plugin from
`local_requirements.txt` and runs migrations and `collectstatic`:

```bash
sudo /opt/netbox/upgrade.sh
sudo systemctl restart netbox netbox-rq
```

## Uninstall

1. Remove `"netbox_rack_concept"` from `PLUGINS` and `PLUGINS_CONFIG`.
2. Remove the line from `/opt/netbox/local_requirements.txt`.
3. Uninstall the package and restart NetBox:

```bash
/opt/netbox/venv/bin/pip uninstall netbox-rack-concept
sudo systemctl restart netbox netbox-rq
```

## Configuration

All values are optional; the defaults are shown.

```python
PLUGINS_CONFIG = {
    "netbox_rack_concept": {
        # Defaults when creating a new concept
        "default_u_height": 42,
        "default_width": 19,

        # Show the "Copy to concept" button on the rack page
        "enable_rack_tab": True,

        # Status of objects created on deployment
        "deployed_rack_status": "planned",
        "deployed_device_status": "planned",

        # Link to the partial widths of netbox_utilities (matches its DeviceRackPlacement model).
        "partial_width": {
            "enabled": True,
            "model": "netbox_utilities.DeviceRackPlacement",
            "device_field": "device",
            "fraction_field": "width",
            "position_field": "horizontal_position",
            # netbox_utilities counts positions from 1 (left); concepts count from 0.
            "position_base": 1,
        },
    },
}
```

## Usage

### Cabling

Concept devices can be cabled, but **not** via NetBox's real `dcim.Cable`,
which can only connect real `dcim` components. Instead the plugin ships its own
lightweight model pair:

- **ConceptComponent** — an interface, front/rear port, power port/outlet or
  console port on a planned device. **Sync components** creates them 1:1 from
  the device type's component templates (name, label, type, positions) —
  repeatable, without duplicates or data loss on already cabled components.
  Placeholders without a device type get components via **Add component**.
- **ConceptCable** — connects two `ConceptComponent`s. Both ends must belong to
  devices in the same rack concept; a component can only be in one cable at a time.

**Patch panels work exactly like real devices**, because the plugin reads the
same front ↔ rear mapping NetBox maintains on the device type
(`PortTemplateMapping`). It does not depend on the role name "Patchpanel" but on
whether the device type defines front/rear ports with a mapping.

**When copying a real rack into a concept** (and when merging two real racks),
components of all copied devices are synced automatically, and every real cable
whose **both** ends lie within the copied rack(s) is recreated as a
`ConceptCable` — including status, type, colour and label. Cables leaving the
rack and multi-trunk cables (e.g. MPO) cannot be taken over and are reported as
warnings with a count. Cloning or merging concepts leaves cabling unchanged.

### Interaction with other plugins

**netbox-reorder-rack** works on `dcim.Device` querysets. A concept has none by
definition, so this plugin ships its own drag & drop elevation
(`static/netbox_rack_concept/elevation.js`). Once deployed, the result is a
normal rack and reorder-rack applies as usual.

**netbox_utilities** provides partial widths for real devices. On deployment,
this plugin writes the width and position to `netbox_utilities.DeviceRackPlacement`
(staged before validation, so devices sharing a rack unit pass the collision check);
when copying a real rack it reads them. The field mapping is configurable in
`PLUGINS_CONFIG`; a configuration with the old, non-existent model name
`netbox_utilities.RackDevicePosition` is migrated automatically. If `netbox_utilities` is not installed or the mapping does not
match, partial widths are simply not written and a warning is logged.

### What is not deployed

A concept describes space, not operational data. Intentionally **not** created:
cables, interfaces beyond the device type templates, IP addresses, serial
numbers, asset tags. Planned devices without a role, device type or position are
skipped — the confirmation page lists them before deployment.

### REST API

Base path: `/api/plugins/rack-concepts/`

| Method | Endpoint | Purpose |
|---|---|---|
| `GET/POST` | `concepts/` | List and create concepts |
| `GET/PATCH/DELETE` | `concepts/{id}/` | Single concept |
| `POST` | `concepts/copy-from-rack/` | Copy a real rack into a concept (with `override_width`/`override_u_height`/`override_starting_unit`) |
| `POST` | `concepts/{id}/clone/` | Duplicate a concept |
| `POST` | `concepts/merge/` | Stack two concepts into a larger one (`concept_bottom`, `concept_top`) |
| `POST` | `concepts/{id}/deploy/` | Deploy a concept (`dry_run` supported) |
| `GET` | `concepts/{id}/elevation/` | Computed elevation as JSON |
| `GET/POST` | `devices/` | Planned devices |
| `GET/POST` | `components/` | Components of planned devices |
| `GET/POST` | `cables/` | Concept cables |

Example — ten racks from one concept, as a dry run first:

```bash
curl -s -X POST https://netbox.example/api/plugins/rack-concepts/concepts/3/deploy/ \
  -H "Authorization: Token $NETBOX_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
        "name_pattern": "DC1-R{n:02d}",
        "count": 10,
        "start_index": 1,
        "site": 4,
        "location": 12,
        "create_devices": true,
        "device_name_pattern": "{rack}-{name}",
        "dry_run": true
      }'
```

Response:

```json
{
  "dry_run": true,
  "racks": ["DC1-R01", "…", "DC1-R10"],
  "devices_per_rack": 7,
  "total_devices": 70,
  "warnings": ["Blanking panel 3 has no role. NetBox requires one, so it will not be created."]
}
```

Set `dry_run` to `false` to actually create the objects. Deployment runs in
**one** transaction: if a rack or device fails, nothing is created.

### Permissions

Standard NetBox object permissions apply:
`netbox_rack_concept.view_rackconcept`, `add_`, `change_`, `delete_` — and
analogously for `conceptdevice`. Deployment additionally checks `dcim.add_rack`.

### Language

The plugin is available in English (source) and German. Switch the display
language as usual in the user profile (**Preferences → Language**). Translations
live in `netbox_rack_concept/locale/de/LC_MESSAGES/`.

## License

MIT
