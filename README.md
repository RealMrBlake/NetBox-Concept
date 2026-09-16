# netbox-rack-concept

Rack-Blaupausen für NetBox 4.6. Ein „Rack Konzept" ist ein vollständig geplantes Rack
samt Einbauten — aber **kein** echtes Rack und **keine** echten Geräte. Konzepte tauchen
deshalb weder in der Rack-Liste noch in der Geräte-Liste auf, verfälschen keine
Auslastungs-Auswertungen und belegen keine Seriennummern oder IP-Adressen.

Wenn die Planung steht, wird das Konzept per Knopfdruck in echte NetBox-Objekte
überführt — ein Mal oder gleich zwanzig Mal.

## Was das Plugin kann

| Weg | Wo |
|---|---|
| Echtes Rack → Konzept | Button **„Copy to concept"** auf der Rack-Detailseite. Größe des Konzept-Racks (Breite, Höhe, Startunit) ist dabei frei wählbar; Geräte, die in der gewählten Größe keinen Platz mehr finden, werden ausgelassen und als Warnung gemeldet |
| Konzept → Konzept (Variante) | Button **„Clone concept"** auf der Konzept-Detailseite |
| 2 Konzepte → 1 größeres Konzept | Button **„Merge"** im Menü bzw. **„Merge with another"** auf der Konzept-Detailseite — stapelt z.B. zwei halbhohe Racks zu einem vollen; das obere Konzept wird um die Höhe des unteren nach oben verschoben, beide Quellen bleiben unverändert |
| Konzept → echte Racks (n-fach) | Button **„Deploy to NetBox"**, mit Namensschema `DC1-R{n:02d}` |
| Konzept von Hand anlegen | Menü **Rack Concepts → Rack Concepts → +** |

Dazu:

* **Elevation mit Drag & Drop** – Geräte per Maus verschieben, serverseitig validiert.
  Ein ungültiger Zug wird abgelehnt und ändert nichts.
* **Geräte mit Bild und Text** – ist am Gerätetyp ein Front-/Rear-Bild hinterlegt, wird
  es im Elevation-Block angezeigt, mit halbtransparentem Label darüber; ohne Bild bleibt
  es bei der reinen Farbfläche mit Text.
* **Teilbreiten** (1/1, 1/2, 1/3, 1/4 plus horizontale Slot-Position), passend zum
  Teilbreiten-Feature von `netbox_utilities`.
* **Mandant und Mandantengruppe** an Konzept und an jedem geplanten Gerät.
* **Platzhalter ohne Gerätetyp** – reservierter Bauraum, nur mit Höhenangabe.
* Vollständige REST-API, Filter, CSV-Import/-Export, Bulk-Edit, Changelog, Journal,
  Tags, Custom Fields und globale Suche — wie bei jedem Core-Objekt.

## Zusammenspiel mit den anderen Plugins

**netbox-reorder-rack (rackorder)** arbeitet auf `dcim.Device`-Querysets. Ein Konzept hat
per Definition keine, also bringt dieses Plugin eine eigene Drag-&-Drop-Elevation mit
(`static/netbox_rack_concept/elevation.js`). Sobald ein Konzept ausgerollt ist, ist das
Ergebnis ein ganz normales Rack — ab da greift reorder-rack wie gewohnt.

> Hinweis zur Version: `netbox-reorder-rack` **v1.1.5 setzt NetBox 4.7 voraus**. Für
> NetBox 4.6.8 die letzte 4.6-taugliche Version pinnen (`netbox-reorder-rack<1.1.5`).

**netbox_utilities** liefert die Teilbreiten für echte Geräte. Beim Ausrollen schreibt
dieses Plugin die Werte `width_fraction` und `horizontal_position` dorthin zurück; beim
Kopieren eines echten Racks liest es sie von dort. Da die Feldnamen von `netbox_utilities`
nicht öffentlich dokumentiert sind, stehen sie in `PLUGINS_CONFIG` (siehe unten) und
lassen sich ohne Code-Änderung anpassen. Ist `netbox_utilities` nicht installiert oder
passt das Mapping nicht, werden Teilbreiten schlicht nicht geschrieben — alles andere
funktioniert weiter, und es landet eine Warnung im NetBox-Log.

## Installation

### Per pip direkt aus Git

```bash
source /opt/netbox/venv/bin/activate
pip install git+https://git.mrblake.cc/MrBlake/NetBox-Concept.git
```

Für eine bestimmte Version oder einen Branch/Commit `@<ref>` anhängen, z.B.:

```bash
pip install git+https://git.mrblake.cc/MrBlake/NetBox-Concept.git@v0.1.0
```

Damit die Installation auch nach einem `upgrade.sh`/`python3 -m pip install -r
requirements.txt`-Lauf erhalten bleibt, den Eintrag zusätzlich in
`/opt/netbox/local_requirements.txt` aufnehmen:

```
git+https://git.mrblake.cc/MrBlake/NetBox-Concept.git
```

### Aus lokalem Checkout

```bash
source /opt/netbox/venv/bin/activate
pip install /pfad/zu/netbox-rack-concept
```

### Aktivieren

In `configuration.py`:

```python
PLUGINS = [
    'netbox_rack_concept',
    # optional, in beliebiger Reihenfolge:
    'netbox_utilities',
    'netbox_reorder_rack',
]
```

Dann:

```bash
cd /opt/netbox/netbox
python manage.py migrate
python manage.py collectstatic --no-input
sudo systemctl restart netbox netbox-rq
```

## Update

```bash
source /opt/netbox/venv/bin/activate
pip install --upgrade --force-reinstall --no-deps git+https://git.mrblake.cc/MrBlake/NetBox-Concept.git
cd /opt/netbox/netbox
python manage.py migrate
python manage.py collectstatic --no-input
sudo systemctl restart netbox netbox-rq
```

`--force-reinstall --no-deps` ist nötig, weil pip bei einer git-URL ohne Versionsänderung
sonst annimmt, es sei nichts Neues zu holen. Wer stattdessen mit `local_requirements.txt`
und `upgrade.sh` arbeitet, bekommt Updates darüber automatisch mit, sobald sich der
referenzierte Branch/Tag ändert.

> Sollte `migrate` die mitgelieferte Migration nicht anwenden können, weil sich in eurer
> NetBox-Installation Basisfelder unterscheiden: `netbox_rack_concept/migrations/0001_initial.py`
> löschen und `python manage.py makemigrations netbox_rack_concept` laufen lassen.
> Die Migration ist von Hand geschrieben und gegen NetBox 4.6.8 erstellt, aber nicht in
> eurer Umgebung getestet.

## Konfiguration

Alle Werte sind optional; gezeigt sind die Defaults.

```python
PLUGINS_CONFIG = {
    'netbox_rack_concept': {
        # Vorbelegung beim Anlegen eines neuen Konzepts
        'default_u_height': 42,
        'default_width': 19,

        # "Copy to concept"-Button auf der Rack-Seite anzeigen
        'enable_rack_tab': True,

        # Status der Objekte, die beim Ausrollen entstehen
        'deployed_rack_status': 'planned',
        'deployed_device_status': 'planned',

        # Anbindung an die Teilbreiten von netbox_utilities.
        # 'model' leer lassen, wenn netbox_utilities die Felder direkt an dcim.Device hängt.
        'partial_width': {
            'enabled': True,
            'model': 'netbox_utilities.RackDevicePosition',
            'device_field': 'device',
            'fraction_field': 'width_fraction',
            'position_field': 'horizontal_position',
        },
    }
}
```

## REST-API

Basis-Pfad: `/api/plugins/rack-concepts/`

| Methode | Endpunkt | Zweck |
|---|---|---|
| `GET/POST` | `concepts/` | Konzepte auflisten und anlegen |
| `GET/PATCH/DELETE` | `concepts/{id}/` | Einzelnes Konzept |
| `POST` | `concepts/copy-from-rack/` | Echtes Rack in ein Konzept kopieren (mit `override_width`/`override_u_height`/`override_starting_unit`) |
| `POST` | `concepts/{id}/clone/` | Konzept duplizieren |
| `POST` | `concepts/merge/` | Zwei Konzepte zu einem größeren stapeln (`concept_bottom`, `concept_top`) |
| `POST` | `concepts/{id}/deploy/` | Konzept ausrollen (`dry_run` möglich) |
| `GET` | `concepts/{id}/elevation/` | Berechnete Elevation als JSON |
| `GET/POST` | `devices/` | Geplante Geräte |

Beispiel — zehn Racks aus einem Konzept, erst als Trockenlauf:

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

Antwort:

```json
{
  "dry_run": true,
  "racks": ["DC1-R01", "…", "DC1-R10"],
  "devices_per_rack": 7,
  "total_devices": 70,
  "warnings": ["Blindplatte 3 has no role. NetBox requires one, so it will not be created."]
}
```

`dry_run` auf `false` setzen, um es tatsächlich anzulegen. Das Ausrollen läuft in **einer**
Transaktion: schlägt ein Rack oder ein Gerät fehl, wird gar nichts angelegt.

## Was beim Ausrollen nicht mitkommt

Ein Konzept beschreibt Bauraum, keine Betriebsdaten. Bewusst **nicht** erzeugt werden:
Kabel, Interfaces jenseits der Device-Type-Templates, IP-Adressen, Seriennummern-Zwang,
Asset-Tags. Geplante Geräte ohne Rolle, ohne Gerätetyp oder ohne Position werden
übersprungen — welche das sind, zeigt die Bestätigungsseite vor dem Ausrollen an.

## Berechtigungen

Es gelten die normalen NetBox-Objektberechtigungen:
`netbox_rack_concept.view_rackconcept`, `add_`, `change_`, `delete_` — analog für
`conceptdevice`. Für das Ausrollen wird zusätzlich `dcim.add_rack` geprüft.

## Lizenz

MIT
