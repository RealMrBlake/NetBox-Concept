"""
Geometry for concept rack elevations.

This does not reuse dcim's RackElevationSVG: that renderer walks dcim.Device
querysets and knows nothing about partial-width slots. Computing the geometry here
keeps the plugin independent of NetBox internals and lets the template render plain
inline SVG that follows the UI theme.
"""
from decimal import Decimal

from dcim.choices import DeviceFaceChoices

from .choices import LANE_COUNT

UNIT_HEIGHT = 22
RACK_WIDTH = 240
LEGEND_WIDTH = 32
MARGIN = 6
# x where the rack frame itself starts. Used by the frame, every unit slot and every
# device block alike, so none of them can drift out of alignment with the others.
RACK_X = MARGIN + LEGEND_WIDTH

DEFAULT_COLOR = 'c0c0c0'
RESERVED_COLOR = 'e9ecef'


def foreground_color(bg_color):
    """Return black or white, whichever reads better on the given hex colour."""
    bg_color = bg_color.strip('#')
    try:
        r, g, b = (int(bg_color[i:i + 2], 16) for i in (0, 2, 4))
    except ValueError:
        return '000000'
    # Perceived luminance (ITU-R BT.601)
    return '000000' if (r * 299 + g * 587 + b * 114) / 1000 > 128 else 'ffffff'


class ElevationUnit:
    """One labelled rack unit row."""

    def __init__(self, number, y, occupied=False):
        self.number = number
        self.y = y
        self.height = UNIT_HEIGHT
        # Whether *anything* renders over this unit on this face - including a
        # reduced-opacity "opposite" block for a full-depth device. A unit only counts
        # as free (and thus click-to-add) when nothing at all sits on it, which folds
        # back to plain occupied/free for full-width-only setups, same as core NetBox.
        self.occupied = occupied


class ElevationBlock:
    """One rendered device rectangle."""

    def __init__(self, device, face, x, y, width, height, opposite=False):
        self.device = device
        self.face = face
        self.x = x
        self.y = y
        self.width = width
        self.height = height
        # True when the device is physically mounted on the other face and only
        # shows up here because it is full depth.
        self.opposite = opposite

    @property
    def color(self):
        if self.device.role and self.device.role.color:
            return self.device.role.color
        if self.device.device_type is None:
            return RESERVED_COLOR
        return DEFAULT_COLOR

    @property
    def text_color(self):
        return foreground_color(self.color)

    @property
    def label(self):
        return self.device.display_label

    @property
    def sublabel(self):
        if self.device.device_type:
            return str(self.device.device_type)
        return ''

    @property
    def show_text(self):
        return self.height >= 14

    @property
    def image(self):
        """
        The device type's image for the face this block is drawn on, i.e. what's
        physically visible from that side of the rack - not the device's own mounting
        face, which only matters for half-depth devices occupying one face at a time.
        """
        device_type = self.device.device_type
        if device_type is None:
            return None
        image = device_type.front_image if self.face == DeviceFaceChoices.FACE_FRONT else device_type.rear_image
        return image if image else None


class Elevation:
    """Everything the template needs to draw one face of a concept rack."""

    def __init__(self, concept, face=DeviceFaceChoices.FACE_FRONT, devices=None):
        self.concept = concept
        self.face = face
        self.units = []
        self.blocks = []

        self.legend_width = LEGEND_WIDTH
        self.rack_width = RACK_WIDTH
        self.rack_x = RACK_X
        self.rack_right = RACK_X + RACK_WIDTH
        self.rack_center_x = RACK_X + RACK_WIDTH / 2
        self.width = RACK_X + RACK_WIDTH + MARGIN
        self.height = concept.u_height * UNIT_HEIGHT + MARGIN * 2

        # Blocks first: unit occupancy (used to decide which units are click-to-add)
        # depends on where they land.
        self._build_blocks(devices if devices is not None else concept.devices.all())
        self._build_units()

    @property
    def face_label(self):
        return dict(DeviceFaceChoices).get(self.face, self.face)

    def _y_for(self, top_unit):
        """Pixel offset of the top edge of a block whose highest unit boundary is `top_unit`."""
        concept = self.concept
        if concept.desc_units:
            # U1 at the top: the block's top edge is its lowest unit number.
            bottom = top_unit
            offset = Decimal(bottom) - Decimal(concept.starting_unit)
        else:
            offset = Decimal(concept.starting_unit + concept.u_height) - Decimal(top_unit)
        return float(offset) * UNIT_HEIGHT + MARGIN

    def _build_units(self):
        for number in self.concept.units:
            top = number if self.concept.desc_units else number + 1
            occupied = any(
                block.device.unit_span and block.device.unit_span[0] <= number < block.device.unit_span[1]
                for block in self.blocks
            )
            self.units.append(ElevationUnit(number, self._y_for(Decimal(top)), occupied))

    def _build_blocks(self, devices):
        for device in devices:
            span = device.unit_span
            if span is None:
                continue
            if not device.occupies_face(self.face):
                continue

            bottom, top = span
            lane_start, lane_end = device.lane_span
            x = RACK_X + (lane_start / LANE_COUNT) * RACK_WIDTH
            width = ((lane_end - lane_start) / LANE_COUNT) * RACK_WIDTH

            if self.concept.desc_units:
                y = self._y_for(bottom)
            else:
                y = self._y_for(top)

            self.blocks.append(ElevationBlock(
                device=device,
                face=self.face,
                x=x,
                y=y,
                width=width,
                height=float(top - bottom) * UNIT_HEIGHT,
                opposite=device.face != self.face,
            ))


def get_elevations(concept):
    """Front and rear elevation, sharing one prefetched device list."""
    devices = list(concept.devices.select_related('device_type', 'role', 'device_type__manufacturer'))
    return (
        Elevation(concept, DeviceFaceChoices.FACE_FRONT, devices),
        Elevation(concept, DeviceFaceChoices.FACE_REAR, devices),
    )


def available_units(concept, u_height=Decimal('1'), face=DeviceFaceChoices.FACE_FRONT, exclude=None):
    """
    Unit numbers where a device of the given height would fit on the given face at
    full width. Used by the position dropdown in the device form.
    """
    devices = [
        d for d in concept.devices.select_related('device_type')
        if d.position is not None and d.pk != exclude and d.occupies_face(face)
    ]
    low, high = concept.unit_range
    result = []
    unit = low
    while unit + u_height <= high:
        blocked = any(
            not (unit + u_height <= d.unit_span[0] or d.unit_span[1] <= unit)
            for d in devices
        )
        if not blocked:
            result.append(unit)
        unit += 1
    return result
