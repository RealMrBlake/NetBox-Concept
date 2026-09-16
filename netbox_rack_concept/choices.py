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
