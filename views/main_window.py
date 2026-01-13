"""
IOVENADO DataLogger - Main Window

Main application window with tabbed interface for sensor views.
Manages serial connection and data distribution to views.
"""

from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QTabWidget, QPushButton, QLabel, QStatusBar, QMessageBox
)
from PySide6.QtCore import Slot
from PySide6.QtGui import QAction

from config.settings import (
    APP_NAME, APP_VERSION,
    WINDOW_MIN_WIDTH, WINDOW_MIN_HEIGHT,
    COLOR_CONNECTED, COLOR_DISCONNECTED,
    DATA_OUTPUT_DIR
)
from core.packet import SensorPacket
from core.serial_reader import SerialPacketReader, MockSerialReader
from core.data_logger import CSVDataLogger
from .gps_view import GPSView
from .lidar_view import LidarView
from .co2_view import CO2View
from .can_view import CANView
from .dashboard_view import DashboardView


class MainWindow(QMainWindow):
    """
    Main application window.
    Contains tabbed views for each sensor and overall dashboard.
    """

    def __init__(self, use_mock: bool = False):
        super().__init__()
        self.use_mock = use_mock
        self.serial_reader = None
        self.views = {}
        self.data_logger = CSVDataLogger(DATA_OUTPUT_DIR)
        self.is_recording = False

        self.setWindowTitle(f"{APP_NAME} v{APP_VERSION}")
        self.setMinimumSize(WINDOW_MIN_WIDTH, WINDOW_MIN_HEIGHT)

        self._init_ui()
        self._init_serial()

    def _init_ui(self):
        """Initialize user interface"""
        # Central widget
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setSpacing(10)
        layout.setContentsMargins(10, 10, 10, 10)

        # Apply dark theme
        self.setStyleSheet("""
            QMainWindow {
                background-color: #0f0f23;
            }
            QWidget {
                background-color: #0f0f23;
                color: #ecf0f1;
            }
            QTabWidget::pane {
                border: 1px solid #34495e;
                border-radius: 5px;
                background-color: #0f0f23;
            }
            QTabBar::tab {
                background-color: #1a1a2e;
                color: #bdc3c7;
                padding: 10px 20px;
                margin-right: 2px;
                border-top-left-radius: 5px;
                border-top-right-radius: 5px;
            }
            QTabBar::tab:selected {
                background-color: #2c3e50;
                color: #ecf0f1;
            }
            QTabBar::tab:hover {
                background-color: #34495e;
            }
        """)

        # Top status bar
        status_bar = QHBoxLayout()

        self.connection_status = QLabel("DISCONNECTED")
        self.connection_status.setStyleSheet(f"""
            color: {COLOR_DISCONNECTED};
            font-weight: bold;
            font-size: 14px;
            padding: 5px 15px;
            background-color: rgba(231, 76, 60, 0.2);
            border-radius: 5px;
        """)
        status_bar.addWidget(self.connection_status)

        status_bar.addStretch()

        self.sensor_status = QLabel("Sensors: --")
        self.sensor_status.setStyleSheet("color: #7f8c8d; font-size: 12px;")
        status_bar.addWidget(self.sensor_status)

        layout.addLayout(status_bar)

        # Tab widget for views
        self.tabs = QTabWidget()

        # Dashboard (first tab)
        self.views['dashboard'] = DashboardView()
        self.tabs.addTab(self.views['dashboard'], "Dashboard")

        # GPS View
        self.views['gps'] = GPSView()
        self.tabs.addTab(self.views['gps'], "GPS")

        # Lidar View
        self.views['lidar'] = LidarView()
        self.tabs.addTab(self.views['lidar'], "Lidar")

        # CO2 View
        self.views['co2'] = CO2View()
        self.tabs.addTab(self.views['co2'], "CO2")

        # CAN View
        self.views['can'] = CANView()
        self.tabs.addTab(self.views['can'], "CAN Bus")

        layout.addWidget(self.tabs)

        # Bottom controls
        controls = QHBoxLayout()

        # Mock mode indicator
        if self.use_mock:
            mock_label = QLabel("MOCK MODE")
            mock_label.setStyleSheet("""
                color: #f39c12;
                font-weight: bold;
                padding: 5px 10px;
                background-color: rgba(243, 156, 18, 0.2);
                border-radius: 3px;
            """)
            controls.addWidget(mock_label)

        controls.addStretch()

        # Recording status label
        self.recording_status = QLabel("")
        self.recording_status.setStyleSheet("color: #7f8c8d; font-size: 12px;")
        controls.addWidget(self.recording_status)

        # Record/Stop button
        self.btn_record = QPushButton("Start Recording")
        self.btn_record.setStyleSheet("""
            QPushButton {
                background-color: #e74c3c;
                color: #ecf0f1;
                border: none;
                padding: 8px 20px;
                border-radius: 5px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #c0392b;
            }
            QPushButton:pressed {
                background-color: #a93226;
            }
        """)
        self.btn_record.clicked.connect(self._toggle_recording)
        controls.addWidget(self.btn_record)

        # Reset button
        self.btn_reset = QPushButton("Reset Views")
        self.btn_reset.setStyleSheet("""
            QPushButton {
                background-color: #34495e;
                color: #ecf0f1;
                border: none;
                padding: 8px 20px;
                border-radius: 5px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #4a6785;
            }
            QPushButton:pressed {
                background-color: #2c3e50;
            }
        """)
        self.btn_reset.clicked.connect(self._reset_views)
        controls.addWidget(self.btn_reset)

        # Reconnect button
        self.btn_reconnect = QPushButton("Reconnect")
        self.btn_reconnect.setStyleSheet("""
            QPushButton {
                background-color: #27ae60;
                color: #ecf0f1;
                border: none;
                padding: 8px 20px;
                border-radius: 5px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #2ecc71;
            }
            QPushButton:pressed {
                background-color: #1e8449;
            }
        """)
        self.btn_reconnect.clicked.connect(self._reconnect)
        controls.addWidget(self.btn_reconnect)

        layout.addLayout(controls)

        # Status bar at bottom
        self.statusBar().showMessage("Ready")
        self.statusBar().setStyleSheet("""
            QStatusBar {
                background-color: #1a1a2e;
                color: #7f8c8d;
                border-top: 1px solid #34495e;
            }
        """)

    def _init_serial(self):
        """Initialize serial reader"""
        if self.use_mock:
            self.serial_reader = MockSerialReader()
        else:
            self.serial_reader = SerialPacketReader()

        # Connect signals
        self.serial_reader.packet_received.connect(self._on_packet_received)
        self.serial_reader.connection_changed.connect(self._on_connection_changed)
        self.serial_reader.error_occurred.connect(self._on_error)

        # Start reading
        self.serial_reader.start()

    @Slot(object)
    def _on_packet_received(self, packet: SensorPacket):
        """Handle received sensor packet"""
        # DEBUG: Print packet info
        print(f"[GUI] Packet: lat={packet.latitude:.6f}, lon={packet.longitude:.6f}, "
              f"fix={packet.gps_fix}, conn={packet.gps_connected}, status=0x{packet.status:02X}")

        # Write to CSV if recording
        if self.is_recording:
            self.data_logger.write_packet(packet)
            # Update recording status
            self.recording_status.setText(
                f"Recording: {self.data_logger.packet_count} packets"
            )

        # Update dashboard
        self.views['dashboard'].update_data(packet)

        # Update GPS view
        self.views['gps'].update_data(
            packet.latitude,
            packet.longitude,
            packet.speed_knots,
            packet.gps_fix,
            packet.gps_connected
        )

        # Update Lidar view
        self.views['lidar'].update_data(
            packet.distance_cm,
            packet.lidar_strength,
            packet.lidar_connected
        )

        # Update CO2 view
        self.views['co2'].update_data(
            packet.co2_ppm,
            packet.co2_connected
        )

        # Update CAN view
        self.views['can'].update_data(
            packet.can_messages,
            packet.can_active
        )

        # Update sensor status in header
        self._update_sensor_status(packet.status)

        # Update status bar
        self.statusBar().showMessage(
            f"Received packet | Timestamp: {packet.timestamp}ms | "
            f"Status: 0x{packet.status:02X}"
        )

    @Slot(bool)
    def _on_connection_changed(self, connected: bool):
        """Handle connection state change"""
        if connected:
            self.connection_status.setText("CONNECTED")
            self.connection_status.setStyleSheet(f"""
                color: {COLOR_CONNECTED};
                font-weight: bold;
                font-size: 14px;
                padding: 5px 15px;
                background-color: rgba(46, 204, 113, 0.2);
                border-radius: 5px;
            """)
            self.statusBar().showMessage("Connected to ESP32")
        else:
            self.connection_status.setText("DISCONNECTED")
            self.connection_status.setStyleSheet(f"""
                color: {COLOR_DISCONNECTED};
                font-weight: bold;
                font-size: 14px;
                padding: 5px 15px;
                background-color: rgba(231, 76, 60, 0.2);
                border-radius: 5px;
            """)
            self.statusBar().showMessage("Disconnected")

    @Slot(str)
    def _on_error(self, error_msg: str):
        """Handle error from serial reader"""
        self.statusBar().showMessage(f"Error: {error_msg}")

    def _update_sensor_status(self, status: int):
        """Update sensor status display (v2.0 protocol from ESP32)"""
        sensors = []

        # ESP32 v2.0 status bits: bit0=GPS_FIX, bit1=GPS_CONN, bit2=CAN_ACTIVE
        if status & 0x02:  # GPS_CONN
            if status & 0x01:  # GPS_FIX
                sensors.append("GPS*")
            else:
                sensors.append("GPS")

        if status & 0x04:  # CAN_ACTIVE
            sensors.append("CAN")

        # Note: Lidar and CO2 now connect directly to Pi, not via ESP32
        # When Pi sensors are implemented, add their status here

        if sensors:
            self.sensor_status.setText(f"Sensors: {', '.join(sensors)}")
        else:
            self.sensor_status.setText("Sensors: None")

    def _reset_views(self):
        """Reset all views to initial state"""
        for view in self.views.values():
            view.reset()
        self.statusBar().showMessage("Views reset")

    def _reconnect(self):
        """Reconnect to serial port"""
        if self.serial_reader:
            self.serial_reader.stop()

        self._reset_views()
        self._init_serial()
        self.statusBar().showMessage("Reconnecting...")

    def _toggle_recording(self):
        """Toggle recording on/off"""
        if self.is_recording:
            self._stop_recording()
        else:
            self._start_recording()

    def _start_recording(self):
        """Start recording data to CSV"""
        try:
            session_id = self.data_logger.start_session()
            self.is_recording = True

            # Update button appearance
            self.btn_record.setText("Stop Recording")
            self.btn_record.setStyleSheet("""
                QPushButton {
                    background-color: #27ae60;
                    color: #ecf0f1;
                    border: none;
                    padding: 8px 20px;
                    border-radius: 5px;
                    font-weight: bold;
                }
                QPushButton:hover {
                    background-color: #2ecc71;
                }
                QPushButton:pressed {
                    background-color: #1e8449;
                }
            """)

            self.recording_status.setText(f"Recording: 0 packets")
            self.statusBar().showMessage(f"Started recording session: {session_id}")

        except Exception as e:
            QMessageBox.critical(self, "Recording Error", f"Failed to start recording: {str(e)}")

    def _stop_recording(self):
        """Stop recording and optionally export"""
        if not self.is_recording:
            return

        session_id = self.data_logger.session_id
        packet_count = self.data_logger.packet_count

        # Stop the data logger
        self.data_logger.stop_session()
        self.is_recording = False

        # Update button appearance
        self.btn_record.setText("Start Recording")
        self.btn_record.setStyleSheet("""
            QPushButton {
                background-color: #e74c3c;
                color: #ecf0f1;
                border: none;
                padding: 8px 20px;
                border-radius: 5px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #c0392b;
            }
            QPushButton:pressed {
                background-color: #a93226;
            }
        """)

        self.recording_status.setText("")
        self.statusBar().showMessage(f"Stopped recording ({packet_count} packets)")

        # Ask user if they want to export to ZIP
        reply = QMessageBox.question(
            self,
            "Export Session",
            f"Recording stopped.\nExport session '{session_id}' to ZIP?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            self._export_session(session_id)

    def _export_session(self, session_id: str):
        """Export session to ZIP file"""
        try:
            zip_path = self.data_logger.export_session_zip(session_id)
            QMessageBox.information(
                self,
                "Export Complete",
                f"Session exported to:\n{zip_path}"
            )
            self.statusBar().showMessage(f"Exported to {zip_path}")
        except Exception as e:
            QMessageBox.critical(
                self,
                "Export Error",
                f"Failed to export session: {str(e)}"
            )

    def closeEvent(self, event):
        """Handle window close"""
        # Stop recording if active
        if self.is_recording:
            self.data_logger.stop_session()

        # Stop serial reader
        if self.serial_reader:
            self.serial_reader.stop()

        event.accept()
