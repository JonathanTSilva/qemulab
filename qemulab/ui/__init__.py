"""QemuLab UI Package - Modern Glass Aesthetic"""

from qemulab.ui.app import QemuLabApp

# Import QemuLab as an alias for backward compatibility
QemuLab = QemuLabApp

__all__ = [
    "QemuLab",  # Backward compatibility
    "QemuLabApp",
]
