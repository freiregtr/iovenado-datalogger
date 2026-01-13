"""
IOVENADO DataLogger - GPS View

LCD-style numeric display for GPS data.
Shows latitude, longitude, speed, and fix status.
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QFrame, QGroupBox
)
from PySide6.QtCore import Qt, Slot
from PySide6.QtGui import QFont

from config.settings import COLOR_GPS, COLOR_CONNECTED, COLOR_DISCONNECTED


class LCDLabel(QLabel):
    """Large LCD-style label for numeric display"""

    def __init__(self, text: str = "--", parent=None):
        super().__init__(text, parent)
        font = QFont("Consolas", 32, QFont.Weight.Bold)
        self.setFont(font)
        self.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        self.setStyleSheet(f"""
            QLabel {{
                color: {COLOR_GPS};
                background-color: #1a1a2e;
                border: 2px solid #16213e;
                border-radius: 5px;
                padding: 10px 15px;
                min-width: 200px;
            }}
        """)


class GPSView(QWidget):
    """
    GPS data display widget.
    Shows coordinates, speed, and connection status in LCD-style format.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(15)

        # Header with status
        header = QHBoxLayout()
        title = QLabel("GPS - Ublox NEO-6M v2")
        title.setStyleSheet("font-size: 18px; font-weight: bold; color: #ecf0f1;")
        header.addWidget(title)
        header.addStretch()

        self.status_label = QLabel("DISCONNECTED")
        self.status_label.setStyleSheet(f"""
            font-size: 14px;
            font-weight: bold;
            color: {COLOR_DISCONNECTED};
            padding: 5px 10px;
            border-radius: 3px;
            background-color: rgba(231, 76, 60, 0.2);
        """)
        header.addWidget(self.status_label)

        self.fix_label = QLabel("NO FIX")
        self.fix_label.setStyleSheet(f"""
            font-size: 14px;
            font-weight: bold;
            color: {COLOR_DISCONNECTED};
            padding: 5px 10px;
            border-radius: 3px;
            background-color: rgba(231, 76, 60, 0.2);
        """)
        header.addWidget(self.fix_label)

        layout.addLayout(header)

        # Main display area
        display_frame = QFrame()
        display_frame.setStyleSheet("""
            QFrame {
                background-color: #0f0f23;
                border: 1px solid #2c3e50;
                border-radius: 10px;
            }
        """)
        display_layout = QVBoxLayout(display_frame)
        display_layout.setSpacing(20)
        display_layout.setContentsMargins(20, 20, 20, 20)

        # Coordinates section
        coord_group = QGroupBox("Coordinates")
        coord_group.setStyleSheet("""
            QGroupBox {
                font-size: 14px;
                font-weight: bold;
                color: #bdc3c7;
                border: 1px solid #34495e;
                border-radius: 5px;
                margin-top: 10px;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
            }
        """)
        coord_layout = QGridLayout(coord_group)
        coord_layout.setSpacing(15)

        # Latitude
        lat_label = QLabel("LAT")
        lat_label.setStyleSheet("color: #7f8c8d; font-size: 12px;")
        coord_layout.addWidget(lat_label, 0, 0)

        self.lat_value = LCDLabel("---.------")
        coord_layout.addWidget(self.lat_value, 0, 1)

        lat_unit = QLabel("°")
        lat_unit.setStyleSheet("color: #7f8c8d; font-size: 18px;")
        coord_layout.addWidget(lat_unit, 0, 2)

        self.lat_dir = QLabel("--")
        self.lat_dir.setStyleSheet(f"color: {COLOR_GPS}; font-size: 24px; font-weight: bold;")
        coord_layout.addWidget(self.lat_dir, 0, 3)

        # Longitude
        lon_label = QLabel("LON")
        lon_label.setStyleSheet("color: #7f8c8d; font-size: 12px;")
        coord_layout.addWidget(lon_label, 1, 0)

        self.lon_value = LCDLabel("---.------")
        coord_layout.addWidget(self.lon_value, 1, 1)

        lon_unit = QLabel("°")
        lon_unit.setStyleSheet("color: #7f8c8d; font-size: 18px;")
        coord_layout.addWidget(lon_unit, 1, 2)

        self.lon_dir = QLabel("--")
        self.lon_dir.setStyleSheet(f"color: {COLOR_GPS}; font-size: 24px; font-weight: bold;")
        coord_layout.addWidget(self.lon_dir, 1, 3)

        display_layout.addWidget(coord_group)

        # Speed section
        speed_group = QGroupBox("Speed")
        speed_group.setStyleSheet("""
            QGroupBox {
                font-size: 14px;
                font-weight: bold;
                color: #bdc3c7;
                border: 1px solid #34495e;
                border-radius: 5px;
                margin-top: 10px;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
            }
        """)
        speed_layout = QHBoxLayout(speed_group)
        speed_layout.setSpacing(30)

        # Knots
        knots_container = QVBoxLayout()
        self.speed_knots = LCDLabel("--.-")
        knots_container.addWidget(self.speed_knots)
        knots_unit = QLabel("knots")
        knots_unit.setStyleSheet("color: #7f8c8d; font-size: 12px;")
        knots_unit.setAlignment(Qt.AlignmentFlag.AlignCenter)
        knots_container.addWidget(knots_unit)
        speed_layout.addLayout(knots_container)

        # km/h
        kmh_container = QVBoxLayout()
        self.speed_kmh = LCDLabel("--.-")
        kmh_container.addWidget(self.speed_kmh)
        kmh_unit = QLabel("km/h")
        kmh_unit.setStyleSheet("color: #7f8c8d; font-size: 12px;")
        kmh_unit.setAlignment(Qt.AlignmentFlag.AlignCenter)
        kmh_container.addWidget(kmh_unit)
        speed_layout.addLayout(kmh_container)

        # mph
        mph_container = QVBoxLayout()
        self.speed_mph = LCDLabel("--.-")
        mph_container.addWidget(self.speed_mph)
        mph_unit = QLabel("mph")
        mph_unit.setStyleSheet("color: #7f8c8d; font-size: 12px;")
        mph_unit.setAlignment(Qt.AlignmentFlag.AlignCenter)
        mph_container.addWidget(mph_unit)
        speed_layout.addLayout(mph_container)

        display_layout.addWidget(speed_group)

        layout.addWidget(display_frame)
        layout.addStretch()

    @Slot(float, float, float, bool, bool)
    def update_data(self, latitude: float, longitude: float, speed_knots: float,
                    gps_fix: bool, gps_connected: bool):
        """Update GPS display with new data"""
        # Update connection status
        if gps_connected:
            self.status_label.setText("CONNECTED")
            self.status_label.setStyleSheet(f"""
                font-size: 14px;
                font-weight: bold;
                color: {COLOR_CONNECTED};
                padding: 5px 10px;
                border-radius: 3px;
                background-color: rgba(46, 204, 113, 0.2);
            """)
        else:
            self.status_label.setText("DISCONNECTED")
            self.status_label.setStyleSheet(f"""
                font-size: 14px;
                font-weight: bold;
                color: {COLOR_DISCONNECTED};
                padding: 5px 10px;
                border-radius: 3px;
                background-color: rgba(231, 76, 60, 0.2);
            """)

        # Update fix status
        if gps_fix:
            self.fix_label.setText("FIX OK")
            self.fix_label.setStyleSheet(f"""
                font-size: 14px;
                font-weight: bold;
                color: {COLOR_CONNECTED};
                padding: 5px 10px;
                border-radius: 3px;
                background-color: rgba(46, 204, 113, 0.2);
            """)
        else:
            self.fix_label.setText("NO FIX")
            self.fix_label.setStyleSheet(f"""
                font-size: 14px;
                font-weight: bold;
                color: {COLOR_DISCONNECTED};
                padding: 5px 10px;
                border-radius: 3px;
                background-color: rgba(231, 76, 60, 0.2);
            """)

        # Update coordinates (show even without fix for debugging)
        if gps_connected:
            # Latitude
            lat_dir = "N" if latitude >= 0 else "S"
            self.lat_value.setText(f"{abs(latitude):011.6f}")
            self.lat_dir.setText(lat_dir)

            # Longitude
            lon_dir = "E" if longitude >= 0 else "W"
            self.lon_value.setText(f"{abs(longitude):011.6f}")
            self.lon_dir.setText(lon_dir)

            # Speed
            self.speed_knots.setText(f"{speed_knots:05.1f}")
            self.speed_kmh.setText(f"{speed_knots * 1.852:05.1f}")
            self.speed_mph.setText(f"{speed_knots * 1.15078:05.1f}")
        else:
            # No connection - show placeholder
            self.lat_value.setText("---.------")
            self.lat_dir.setText("--")
            self.lon_value.setText("---.------")
            self.lon_dir.setText("--")
            self.speed_knots.setText("--.-")
            self.speed_kmh.setText("--.-")
            self.speed_mph.setText("--.-")

    def reset(self):
        """Reset display to initial state"""
        self.update_data(0.0, 0.0, 0.0, False, False)
