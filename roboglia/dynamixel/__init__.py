from ..utils import register_class

from .register import DynamixelAXBaudRateRegister
from .register import DynamixelAXComplianceSlopeRegister
from .register import DynamixelXLBaudRateRegister

from .device import DynamixelDevice

from .bus import DynamixelBus
from .bus import ShareableDynamixelBus
from .bus import MockDynamixelBus
from .bus import MockPacketHandler                  # noqa F401

from .sync import DynamixelSyncReadLoop
from .sync import DynamixelSyncWriteLoop
from .sync import DynamixelBulkReadLoop
from .sync import DynamixelBulkWriteLoop

register_class(DynamixelAXBaudRateRegister)
register_class(DynamixelAXComplianceSlopeRegister)
register_class(DynamixelXLBaudRateRegister)

register_class(DynamixelDevice)

register_class(DynamixelBus)
register_class(ShareableDynamixelBus)
register_class(MockDynamixelBus)

register_class(DynamixelSyncReadLoop)
register_class(DynamixelSyncWriteLoop)
register_class(DynamixelBulkReadLoop)
register_class(DynamixelBulkWriteLoop)
