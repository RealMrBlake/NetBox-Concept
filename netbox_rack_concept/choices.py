from utilities.choices import ChoiceSet


class ConceptStatusChoices(ChoiceSet):
    """Lifecycle of a rack blueprint."""
    key = 'RackConcept.status'

    STATUS_DRAFT = 'draft'
    STATUS_REVIEW = 'review'
    STATUS_APPROVED = 'approved'
    STATUS_ARCHIVED = 'archived'

    CHOICES = [
        (STATUS_DRAFT, 'Draft', 'gray'),
        (STATUS_REVIEW, 'In review', 'orange'),
        (STATUS_APPROVED, 'Approved', 'green'),
        (STATUS_ARCHIVED, 'Archived', 'red'),
    ]


class ConceptDeviceStatusChoices(ChoiceSet):
    """
    What a planned device means. This is deliberately *not* dcim's device status:
    a blueprint describes intent, not operational state.
    """
    key = 'ConceptDevice.status'

    STATUS_PLANNED = 'planned'
    STATUS_EXISTING = 'existing'
    STATUS_OPTIONAL = 'optional'
    STATUS_RESERVED = 'reserved'

    CHOICES = [
        (STATUS_PLANNED, 'Planned', 'blue'),
        (STATUS_EXISTING, 'Existing', 'green'),
        (STATUS_OPTIONAL, 'Optional', 'cyan'),
        (STATUS_RESERVED, 'Reserved space', 'gray'),
    ]


class WidthFractionChoices(ChoiceSet):
    """
    Horizontal subdivision of a rack unit, mirroring the partial-width feature of
    netbox_utilities. The value is the denominator: 1 = full width, 2 = half, ...
    """
    FRACTION_FULL = 1
    FRACTION_HALF = 2
    FRACTION_THIRD = 3
    FRACTION_QUARTER = 4

    CHOICES = (
        (FRACTION_FULL, 'Full width'),
        (FRACTION_HALF, '1/2'),
        (FRACTION_THIRD, '1/3'),
        (FRACTION_QUARTER, '1/4'),
    )


# Least common multiple of all supported denominators. The elevation is laid out
# on this many lanes so that every fraction lands on an integer lane boundary.
LANE_COUNT = 12


class ConceptComponentTypeChoices(ChoiceSet):
    """
    The kinds of pluggable component a planned device can carry. One shared model
    covers all of them (see ConceptComponent) rather than mirroring dcim's seven
    separate component models - a blueprint only needs enough detail to say what a
    cable plugs into, not full per-type validation.
    """
    TYPE_INTERFACE = 'interface'
    TYPE_FRONT_PORT = 'front-port'
    TYPE_REAR_PORT = 'rear-port'
    TYPE_CONSOLE_PORT = 'console-port'
    TYPE_CONSOLE_SERVER_PORT = 'console-server-port'
    TYPE_POWER_PORT = 'power-port'
    TYPE_POWER_OUTLET = 'power-outlet'

    CHOICES = [
        (TYPE_INTERFACE, 'Interface', 'blue'),
        (TYPE_FRONT_PORT, 'Front port', 'orange'),
        (TYPE_REAR_PORT, 'Rear port', 'yellow'),
        (TYPE_CONSOLE_PORT, 'Console port', 'teal'),
        (TYPE_CONSOLE_SERVER_PORT, 'Console server port', 'cyan'),
        (TYPE_POWER_PORT, 'Power port', 'red'),
        (TYPE_POWER_OUTLET, 'Power outlet', 'pink'),
    ]

    #: Component types that are pass-through ports and can appear in a ConceptPortMapping.
    PATCH_TYPES = (TYPE_FRONT_PORT, TYPE_REAR_PORT)
