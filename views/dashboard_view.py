"""
IOVENADO DataLogger - Dashboard View

Grid 2x2 showing summary widgets for all sensors.
Provides at-a-glance view of system status.
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QFrame, QGroupBox
)
from PySide6.QtCore import Qt, Slot
from PySide6.QtGui import QFont

from config.settings import (
    COLOR_GPS, COLOR_LIDAR, COLOR_CO2, COLOR_CAN,
    COLOR_CONNECTED, COLOR_DISCONNECTED,
    CO2_LEVEL_EXCELLENT, CO2_LEVEL_GOOD, CO2_LEVEL_MODERATE
)
from core.packet import SensorPacket


class SensorCard(QFrame):
    """
    Individual sensor summary card.
    Shows sensor name, value, and status.
    """

    def __init__(self, title: str, color: str, parent=None):
        super().__init__(parent)
        self.color = color
        self.setStyleSheet(f"""
            QFrame {{
                background-color: #1a1a2e;
                border: 2px solid {color};
                border-radius: 10px;
            }}
        """)
        self._init_ui(title)

    def _init_ui(self, title: str):
        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        layout.setContentsMargins(15, 15, 15, 15)

        # Header
        header = QHBoxLayout()

        title_label = QLabel(title)
        title_label.setStyleSheet(f"color: {self.color}; font-size: 14px; font-weight: bold;")
        header.addWidget(title_label)

        header.addStretch()

        self.status_dot = QLabel()
        self.status_dot.setFixedSize(12, 12)
        self.status_dot.setStyleSheet(f"""
            background-color: {COLOR_DISCONNECTED};
            border-radius: 6px;
        """)
        header.addWidget(self.status_dot)

        layout.addLayout(header)

        # Main value
        self.value_label = QLabel("---")
        self.value_label.setStyleSheet(f"""
            color: {self.color};
            font-size: 36px;
            font-weight: bold;
        """)
        self.value_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.value_label)

        # Secondary info
        self.info_label = QLabel("")
        self.info_label.setStyleSheet("color: #7f8c8d; font-size: 11px;")
        self.info_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.info_label)

    def set_connected(self, connected: bool):
        """Update connection status indicator"""
        color = COLOR_CONNECTED if connected else COLOR_DISCONNECTED
        self.status_dot.setStyleSheet(f"""
            background-color: {color};
            border-radius: 6px;
        """)

    def set_value(self, value: str, info: str = ""):
        """Update displayed value and info"""
        self.value_label.setText(value)
        self.info_label.setText(info)


class DashboardView(QWidget):
    """
    Dashboard view showing all sensors in a 2x2 grid.
    Each sensor has a summary card with current value and status.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(15)

        # Header
        header = QHBoxLayout()

        title = QLabel("DASHBOARD")
        title.setStyleSheet("font-size: 20px; font-weight: bold; color: #ecf0f1;")
        header.addWidget(title)

        header.addStretch()

        # Overall status
        self.overall_status = QLabel("Initializing...")
        self.overall_status.setStyleSheet("""
            color: #f39c12;
            font-size: 14px;
            padding: 5px 15px;
            background-color: rgba(243, 156, 18, 0.2);
            border-radius: 5px;
        """)
        header.addWidget(self.overall_status)

        layout.addLayout(header)

        # Grid of sensor cards
        grid = QGridLayout()
        grid.setSpacing(15)

        # GPS Card (top-left)
        self.gps_card = SensorCard("GPS", COLOR_GPS)
        grid.addWidget(self.gps_card, 0, 0)

        # Lidar Card (top-right)
        self.lidar_card = SensorCard("LIDAR", COLOR_LIDAR)
        grid.addWidget(self.lidar_card, 0, 1)

        # CO2 Card (bottom-left)
        self.co2_card = SensorCard("CO2", COLOR_CO2)
        grid.addWidget(self.co2_card, 1, 0)

        # CAN Card (bottom-right)
        self.can_card = SensorCard("CAN BUS", COLOR_CAN)
        grid.addWidget(self.can_card, 1, 1)

        layout.addLayout(grid)

        # System info footer
        footer = QFrame()
        footer.setStyleSheet("""
            QFrame {
                background-color: #0f0f23;
                border: 1px solid #34495e;
                border-radius: 5px;
                padding: 10px;
            }
        """)
        footer_layout = QHBoxLayout(footer)

        # Timestamp
        self.timestamp_label = QLabel("Last update: --:--:--")
        self.timestamp_label.setStyleSheet("color: #7f8c8d; font-size: 11px;")
        footer_layout.addWidget(self.timestamp_label)

        footer_layout.addStretch()

        # Status byte
        self.status_byte_label = QLabel("Status: 0x00")
        self.status_byte_label.setStyleSheet("color: #7f8c8d; font-size: 11px; font-family: Consolas;")
        footer_layout.addWidget(self.status_byte_label)

        footer_layout.addStretch()

        # Packet count
        self.packet_count_label = QLabel("Packets: 0")
        self.packet_count_label.setStyleSheet("color: #7f8c8d; font-size: 11px;")
        footer_layout.addWidget(self.packet_count_label)

        layout.addWidget(footer)

        # Initialize packet counter
        self._packet_count = 0

    @Slot(object)
    def update_data(self, packet: SensorPacket):
        """Update all dashboard cards with packet data"""
        self._packet_count += 1

        # Update GPS card
        self.gps_card.set_connected(packet.gps_connected)
        if packet.gps_connected and packet.gps_fix:
            self.gps_card.set_value(
                f"{packet.latitude:.4f}°",
                f"Lon: {packet.longitude:.4f}° | {packet.speed_knots:.1f} kn"
            )
        elif packet.gps_connected:
            self.gps_card.set_value("No Fix", "Searching satellites...")
        else:
            self.gps_card.set_value("---", "Disconnected")

        # Update Lidar card
        self.lidar_card.set_connected(packet.lidar_connected)
        if packet.lidar_connected:
            # Color based on distance
            if packet.distance_cm < 100:
                self.lidar_card.value_label.setStyleSheet(
                    "color: #e74c3c; font-size: 36px; font-weight: bold;"
                )
            elif packet.distance_cm < 300:
                self.lidar_card.value_label.setStyleSheet(
                    "color: #f39c12; font-size: 36px; font-weight: bold;"
                )
            else:
                self.lidar_card.value_label.setStyleSheet(
                    f"color: {COLOR_LIDAR}; font-size: 36px; font-weight: bold;"
                )
            self.lidar_card.set_value(
                f"{packet.distance_cm} cm",
                f"Signal: {packet.lidar_strength}"
            )
        else:
            self.lidar_card.set_value("---", "Disconnected")

        # Update CO2 card
        self.co2_card.set_connected(packet.co2_connected)
        if packet.co2_connected:
            # Determine air quality
            if packet.co2_ppm < CO2_LEVEL_EXCELLENT:
                quality = "Excellent"
                color = "#27ae60"
            elif packet.co2_ppm < CO2_LEVEL_GOOD:
                quality = "Good"
                color = "#2ecc71"
            elif packet.co2_ppm < CO2_LEVEL_MODERATE:
                quality = "Moderate"
                color = "#f39c12"
            else:
                quality = "Poor"
                color = "#e74c3c"

            self.co2_card.value_label.setStyleSheet(
                f"color: {color}; font-size: 36px; font-weight: bold;"
            )
            self.co2_card.set_value(f"{packet.co2_ppm} ppm", quality)
        else:
            self.co2_card.set_value("---", "Disconnected")

        # Update CAN card
        self.can_card.set_connected(packet.can_active)
        msg_count = len(packet.can_messages)
        if packet.can_active:
            self.can_card.set_value(
                f"{msg_count} msg",
                "Active" if msg_count > 0 else "No traffic"
            )
        else:
            self.can_card.set_value("---", "Inactive")

        # Update overall status
        active_count = sum([
            packet.gps_connected,
            packet.lidar_connected,
            packet.co2_connected,
            packet.can_active
        ])

        if active_count == 4:
            self.overall_status.setText("All Systems OK")
            self.overall_status.setStyleSheet(f"""
                color: {COLOR_CONNECTED};
                font-size: 14px;
                padding: 5px 15px;
                background-color: rgba(46, 204, 113, 0.2);
                border-radius: 5px;
            """)
        elif active_count > 0:
            self.overall_status.setText(f"{active_count}/4 Active")
            self.overall_status.setStyleSheet("""
                color: #f39c12;
                font-size: 14px;
                padding: 5px 15px;
                background-color: rgba(243, 156, 18, 0.2);
                border-radius: 5px;
            """)
        else:
            self.overall_status.setText("No Sensors")
            self.overall_status.setStyleSheet(f"""
                color: {COLOR_DISCONNECTED};
                font-size: 14px;
                padding: 5px 15px;
                background-color: rgba(231, 76, 60, 0.2);
                border-radius: 5px;
            """)

        # Update footer
        from datetime import datetime
        self.timestamp_label.setText(f"Last update: {datetime.now().strftime('%H:%M:%S')}")
        self.status_byte_label.setText(f"Status: 0x{packet.status:02X}")
        self.packet_count_label.setText(f"Packets: {self._packet_count}")

    def reset(self):
        """Reset dashboard to initial state"""
        self._packet_count = 0
        self.gps_card.set_value("---", "")
        self.gps_card.set_connected(False)
        self.lidar_card.set_value("---", "")
        self.lidar_card.set_connected(False)
        self.co2_card.set_value("---", "")
        self.co2_card.set_connected(False)
        self.can_card.set_value("---", "")
        self.can_card.set_connected(False)
        self.overall_status.setText("Initializing...")
        self.timestamp_label.setText("Last update: --:--:--")
        self.status_byte_label.setText("Status: 0x00")
        self.packet_count_label.setText("Packets: 0")
