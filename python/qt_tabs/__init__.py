"""Qt integration tabs backed by the calculator's existing math core."""

from qt_tabs.advanced import AdvancedIntegrationTab
from qt_tabs.basic import BasicIntegrationTab
from qt_tabs.improper import ImproperIntegralTab

__all__ = [
    "BasicIntegrationTab",
    "AdvancedIntegrationTab",
    "ImproperIntegralTab",
]
