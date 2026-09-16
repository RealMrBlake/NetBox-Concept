"""
Export a rack concept as a draw.io (diagrams.net) diagram.

Reuses the same Elevation/ElevationBlock geometry the on-page SVG and the SVG export
are built from, so all three always agree on where everything sits. The output is a
plain mxGraph XML file - drawio can open it directly (File > Open) or import it
(Extras > Edit Diagram accepts the same XML pasted in).
"""
import html as html_lib

from .elevation import get_elevations

__all__ = ('build_drawio',)

LABEL_HEIGHT = 30
FACE_GAP = 60


def _escape(text):
    """HTML-escape for use inside an html=1 cell value (which is itself XML-escaped
    again by the caller) - two layers, same as any HTML embedded in an XML attribute."""
    return html_lib.escape(text or '', quote=False)


def _quote_attr(value):
    """XML-attribute-escape a string, matching xml.sax.saxutils.quoteattr but always
    using double quotes so it's safe to splice straight into our hand-built XML."""
    return '"' + (
        value.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;').replace('"', '&quot;')
    ) + '"'


class _CellBuilder:
    """Accumulates mxCell XML fragments and hands out fresh ids."""

    def __init__(self):
        self._next_id = 1
        self.cells = []

    def _id(self):
        self._next_id += 1
        return f'c{self._next_id}'

    def add(self, value, style, x, y, width, height):
        cell_id = self._id()
        self.cells.append(
            f'        <mxCell id="{cell_id}" value={_quote_attr(value)} style={_quote_attr(style)} '
            f'vertex="1" parent="1">\n'
            f'          <mxGeometry x="{x:.2f}" y="{y:.2f}" width="{width:.2f}" height="{height:.2f}" '
            f'as="geometry"/>\n'
            f'        </mxCell>'
        )
        return cell_id


def _device_style(block):
    style = (
        f'rounded=1;whiteSpace=wrap;html=1;arcSize=8;'
        f'fillColor=#{block.color};fontColor=#{block.text_color};fontSize=11;'
    )
    if block.opposite:
        style += 'dashed=1;opacity=45;'
    return style


def build_drawio(concept):
    front, rear = get_elevations(concept)
    builder = _CellBuilder()

    offset_x = 0.0
    for elevation in (front, rear):
        builder.add(
            _escape(elevation.face_label.title()),
            'text;html=1;align=center;verticalAlign=middle;fontStyle=1;fontSize=14;',
            offset_x, 0, elevation.width, LABEL_HEIGHT - 4
        )
        builder.add(
            '', 'rounded=0;whiteSpace=wrap;html=1;fillColor=none;strokeColor=#35404A;strokeWidth=2;',
            offset_x + elevation.rack_x, LABEL_HEIGHT + 6, elevation.rack_width, elevation.height - 12
        )
        for unit in elevation.units:
            builder.add(
                str(unit.number),
                'text;html=1;align=right;verticalAlign=middle;fontSize=10;fontColor=#808F9C;spacingRight=4;',
                offset_x, LABEL_HEIGHT + unit.y, elevation.rack_x - 4, unit.height
            )
        for block in elevation.blocks:
            label = _escape(block.label)
            if block.sublabel:
                label += '<br>' + _escape(block.sublabel)
            builder.add(
                label, _device_style(block),
                offset_x + block.x, LABEL_HEIGHT + block.y, block.width, block.height
            )
        offset_x += elevation.width + FACE_GAP

    body = '\n'.join(builder.cells)

    return (
        '<mxfile host="netbox-rack-concept">\n'
        f'  <diagram id="concept-{concept.pk}" name={_quote_attr(concept.name)}>\n'
        '    <mxGraphModel dx="800" dy="600" grid="1" gridSize="10" guides="1" tooltips="1" connect="1" '
        'arrows="1" fold="1" page="1" pageScale="1" pageWidth="850" pageHeight="1100" math="0" shadow="0">\n'
        '      <root>\n'
        '        <mxCell id="0"/>\n'
        '        <mxCell id="1" parent="0"/>\n'
        f'{body}\n'
        '      </root>\n'
        '    </mxGraphModel>\n'
        '  </diagram>\n'
        '</mxfile>\n'
    )
