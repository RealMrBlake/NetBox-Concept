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
| 2 echte Racks → 1 neues Konzept | Button **„Merge into concept"** über der echten Rack-Liste. Zwei Racks per Checkbox auswählen (wie bei jeder anderen Bulk-Aktion) und auf den Button klicken — vorausgefüllt landet man auf derselben Merge-Maske wie oben, diesmal direkt mit den zwei echten Racks als Quelle |
| Konzept → echte Racks (n-fach) | Button **„Deploy to NetBox"**, mit Namensschema `DC1-R{n:02d}` |
| Konzept von Hand anlegen | Menü **Rack Concepts → Rack Concepts → +** |

Dazu:

* **Elevation mit Drag & Drop** – Geräte per Maus verschieben, serverseitig validiert.
  Ein ungültiger Zug wird abgelehnt und ändert nichts.
* **Geräte mit Bild und Text** – ist am Gerätetyp ein Front-/Rear-Bild hinterlegt, wird
  es im Elevation-Block angezeigt; darüber liegt der Gerätename als weiße, schwarz
  konturierte Schrift (kein dunkler Balken). Ein Dropdown über der Elevation schaltet
  zwischen „Images and labels", „Images only" und „Labels only" um — genau wie bei
  echten Racks in NetBox, inklusive Merken der Wahl im Browser.
* **Teilbreiten** (1/1, 1/2, 1/3, 1/4 plus horizontale Slot-Position), passend zum
  Teilbreiten-Feature von `netbox_utilities`.
* **Mandant und Mandantengruppe** an Konzept und an jedem geplanten Gerät.
* **Platzhalter ohne Gerätetyp** – reservierter Bauraum, nur mit Höhenangabe.
* **Klick auf eine leere HE** öffnet direkt „Add planned device", vorausgefüllt mit
  Position und Seite — genau wie bei einer echten Rack-Elevation. Den separaten
  „Add planned device"-Knopf gibt es dafür nicht mehr.
* **Verkabelung von Konzept-Geräten, 1:1 wie bei echten Geräten** – auf der
  Geräte-Detailseite gibt es dieselben Tabs wie bei einem echten `dcim.Device`:
  Interfaces, Front Ports, Rear Ports, Console Ports, Console Server Ports, Power
  Ports, Power Outlets (gleiche Namen, gleiche Reihenfolge, Tab nur sichtbar wenn
  belegt). „Sync components" übernimmt sie 1:1 aus den Component-Templates des
  Gerätetyps, inkl. Front-↔Rear-Zuordnung von Patchpanels. Über „Connect" an jeder
  unverkabelten Komponente wird sie mit einem Concept Cable verbunden. Ein „Add
  Components"-Dropdown (genau wie am echten Gerät) legt neue Komponenten pro Typ an —
  nötig für Platzhalter ohne Gerätetyp, die nichts zum Syncen haben.
* **Export** – Button **„Export"** über der Elevation: Front bzw. Rear jeweils als
  eigenständige **SVG**-Datei, als **PNG** (einzeln oder beide Seiten zusammen), sowie
  das ganze Konzept als **Draw.io**-Diagramm (`.drawio`, per Datei > Öffnen oder Extras
  > Diagramm bearbeiten in diagrams.net einlesbar). PNG wird direkt im Browser auf ein
  `<canvas>` gezeichnet (derselbe Ansatz wie bei netbox-topology-views) statt ein SVG zu
  rastern — Gerätetyp-Bilder werden dafür einzeln per `fetch()` als Blob geladen; scheitert
  eines davon (z.B. Netzwerkfehler), fehlt nur dieses eine Bild im Export, der Rest bleibt
  unversehrt. Für PNG ist keine zusätzliche Bildbibliothek auf dem Server nötig.
* Vollständige REST-API, Filter, CSV-Import/-Export, Bulk-Edit, Changelog, Journal,
  Tags, Custom Fields und globale Suche — wie bei jedem Core-Objekt.

## Verkabelung

Konzept-Geräte lassen sich verkabeln, aber **nicht** über NetBox' echtes `dcim.Cable` —
das kann nur echte `dcim`-Komponenten verbinden. Stattdessen bringt das Plugin ein
eigenes, schlankes Modellpaar mit:

* **ConceptComponent** — ein Interface, Front-/Rear-Port, Power-Port/-Outlet oder
  Console-Port an einem geplanten Gerät. Über **„Sync components"** auf der
  Geräte-Seite werden sie 1:1 aus den Component-Templates des Gerätetyps erzeugt
  (Name, Label, Typ, Positionen) — wiederholbar, ohne Duplikate oder Datenverlust an
  bereits verkabelten Komponenten. Ein Gerät ohne Gerätetyp (Platzhalter) hat keine
  Templates zum Syncen; seine Komponenten legt man über **„Add component"** von Hand an.
* **ConceptCable** — verbindet zwei `ConceptComponent`s. Beide Enden müssen zu Geräten
  im selben Rack-Konzept gehören; eine Komponente kann nur in einem Kabel gleichzeitig
  stecken. Erreichbar über **„Connect"** an jeder unverkabelten Komponente.

**Patchpanels funktionieren genauso wie bei echten Geräten**, weil das Plugin exakt
dieselbe Front-↔Rear-Zuordnung ausliest, die NetBox selbst am Gerätetyp pflegt (über
`PortTemplateMapping`, dieselbe Tabelle, die auch echte `FrontPort`/`RearPort`-Objekte
verknüpft). Das hängt also nicht an der Rollenbezeichnung „Patchpanel", sondern schlicht
daran, ob der Gerätetyp Front-/Rear-Ports mit Zuordnung definiert — Kabel an der
Vorderseite eines synchronisierten Patchpanel-Gerätetyps zeigen auf der Detailseite der
Komponente sofort den passenden Rear-Port samt Position an.

**Beim Kopieren eines echten Racks in ein Konzept** (und beim Zusammenführen zweier
echter Racks, siehe unten) werden die Komponenten aller übernommenen Geräte automatisch
synchronisiert, und jedes echte Kabel, dessen **beide** Enden innerhalb der kopierten
Rack(s) liegen, wird als `ConceptCable` nachgebaut — Status, Typ, Farbe und Label
inklusive. Kabel, die den Rack verlassen (zum Beispiel zum Uplink-Switch in einem
anderen Rack), lassen sich naturgemäß nicht übernehmen, weil das Gegenstück nicht Teil
des Konzepts ist; ebenso ausgelassen werden Mehrfach-Trunk-Kabel (z.B. MPO), da
`ConceptCable` nur Punkt-zu-Punkt-Verbindungen kennt. Beides wird nach dem Kopieren als
Warnung mit Anzahl gemeldet. Das Nachbilden der Verkabelung gilt nur für den Import
**echter** Racks — beim Klonen oder Zusammenführen von Konzepten (die ja schon eigene
Kabel haben können) bleibt die Verkabelung unverändert, wie bisher.

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
| `GET/POST` | `components/` | Komponenten der geplanten Geräte |
| `GET/POST` | `cables/` | Concept Cables |

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

## Sprache

Das Plugin ist auf Englisch (Quelltext) und Deutsch übersetzt. Beide Sprachen sind in
NetBox bereits als Auswahl hinterlegt; die Anzeigesprache stellt man wie gewohnt über
das Benutzerprofil (Preferences → Language) um — keine zusätzliche Konfiguration nötig.
Die Übersetzung liegt unter `netbox_rack_concept/locale/de/LC_MESSAGES/`.

## Berechtigungen

Es gelten die normalen NetBox-Objektberechtigungen:
`netbox_rack_concept.view_rackconcept`, `add_`, `change_`, `delete_` — analog für
`conceptdevice`. Für das Ausrollen wird zusätzlich `dcim.add_rack` geprüft.

## Lizenz

MIT
