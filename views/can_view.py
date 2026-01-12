"""
IOVENADO DataLogger - CAN View

Terminal-style display for incoming CAN bus messages.
Shows real-time message feed with timestamp, ID, DLC, and data.
"""

from datetime import datetime
from typing import List

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPlainTextEdit, QPushButton, QCheckBox
)
from PySide6.QtGui import QFont, QTextCursor, QColor
from PySide6.QtCore import Qt, Slot

from config.settings import CAN_MAX_MESSAGES, COLOR_CAN, COLOR_CONNECTED, COLOR_DISCONNECTED
from core.packet import CANMessage


class CANView(QWidget):
    """
    CAN bus message display widget.
    Shows incoming messages in a terminal-style scrolling view.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self._message_count = 0
        self._total_messages = 0
        self._paused = False
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(10)

        # Header
        header = QHBoxLayout()

        title = QLabel("CAN BUS - SN65HVD230")
        title.setStyleSheet("font-size: 18px; font-weight: bold; color: #ecf0f1;")
        header.addWidget(title)

        header.addStretch()

        # Message counter
        self.count_label = QLabel("Messages: 0")
        self.count_label.setStyleSheet(f"color: {COLOR_CAN}; font-size: 14px;")
        header.addWidget(self.count_label)

        # Rate
        self.rate_label = QLabel("0 msg/s")
        self.rate_label.setStyleSheet("color: #7f8c8d; font-size: 12px; margin-left: 10px;")
        header.addWidget(self.rate_label)

        # Status
        self.status_label = QLabel("INACTIVE")
        self.status_label.setStyleSheet(f"""
            font-size: 12px;
            font-weight: bold;
            color: #7f8c8d;
            padding: 5px 10px;
            border-radius: 3px;
            background-color: rgba(127, 140, 141, 0.2);
        """)
        header.addWidget(self.status_label)

        layout.addLayout(header)

        # Controls
        controls = QHBoxLayout()

        self.auto_scroll_cb = QCheckBox("Auto-scroll")
        self.auto_scroll_cb.setChecked(True)
        self.auto_scroll_cb.setStyleSheet("color: #bdc3c7;")
        controls.addWidget(self.auto_scroll_cb)

        self.hex_mode_cb = QCheckBox("Hex mode")
        self.hex_mode_cb.setChecked(True)
        self.hex_mode_cb.setStyleSheet("color: #bdc3c7;")
        controls.addWidget(self.hex_mode_cb)

        controls.addStretch()

        self.pause_btn = QPushButton("Pause")
        self.pause_btn.setStyleSheet("""
            QPushButton {
                background-color: #34495e;
                color: #ecf0f1;
                border: none;
                padding: 5px 15px;
                border-radius: 3px;
            }
            QPushButton:hover {
                background-color: #4a6785;
            }
            QPushButton:pressed {
                background-color: #2c3e50;
            }
        """)
        self.pause_btn.clicked.connect(self._toggle_pause)
        controls.addWidget(self.pause_btn)

        self.clear_btn = QPushButton("Clear")
        self.clear_btn.setStyleSheet("""
            QPushButton {
                background-color: #c0392b;
                color: #ecf0f1;
                border: none;
                padding: 5px 15px;
                border-radius: 3px;
            }
            QPushButton:hover {
                background-color: #e74c3c;
            }
            QPushButton:pressed {
                background-color: #a93226;
            }
        """)
        self.clear_btn.clicked.connect(self.clear)
        controls.addWidget(self.clear_btn)

        layout.addLayout(controls)

        # Terminal display
        self.terminal = QPlainTextEdit()
        self.terminal.setReadOnly(True)
        self.terminal.setFont(QFont("Consolas", 10))
        self.terminal.setStyleSheet("""
            QPlainTextEdit {
                background-color: #0a0a0a;
                color: #00ff00;
                border: 1px solid #34495e;
                border-radius: 5px;
                padding: 10px;
            }
        """)
        self.terminal.setMaximumBlockCount(CAN_MAX_MESSAGES)

        # Add header line
        self._add_header()

        layout.addWidget(self.terminal)

    def _add_header(self):
        """Add column headers to terminal"""
        header = "TIME       | ID     | DLC | DATA                      | DECODED"
        separator = "-" * 75
        self.terminal.appendPlainText(header)
        self.terminal.appendPlainText(separator)

    def _toggle_pause(self):
        """Toggle pause state"""
        self._paused = not self._paused
        if self._paused:
            self.pause_btn.setText("Resume")
            self.pause_btn.setStyleSheet("""
                QPushButton {
                    background-color: #27ae60;
                    color: #ecf0f1;
                    border: none;
                    padding: 5px 15px;
                    border-radius: 3px;
                }
                QPushButton:hover {
                    background-color: #2ecc71;
                }
            """)
        else:
            self.pause_btn.setText("Pause")
            self.pause_btn.setStyleSheet("""
                QPushButton {
                    background-color: #34495e;
                    color: #ecf0f1;
                    border: none;
                    padding: 5px 15px;
                    border-radius: 3px;
                }
                QPushButton:hover {
                    background-color: #4a6785;
                }
            """)

    @Slot(list, bool)
    def update_data(self, messages: List[CANMessage], active: bool):
        """Update terminal with new CAN messages"""
        # Update status
        if active:
            self.status_label.setText("ACTIVE")
            self.status_label.setStyleSheet(f"""
                font-size: 12px;
                font-weight: bold;
                color: {COLOR_CONNECTED};
                padding: 5px 10px;
                border-radius: 3px;
                background-color: rgba(46, 204, 113, 0.2);
            """)
        else:
            self.status_label.setText("INACTIVE")
            self.status_label.setStyleSheet(f"""
                font-size: 12px;
                font-weight: bold;
                color: #7f8c8d;
                padding: 5px 10px;
                border-radius: 3px;
                background-color: rgba(127, 140, 141, 0.2);
            """)

        if self._paused or not messages:
            return

        # Add messages to terminal
        timestamp = datetime.now().strftime("%H:%M:%S")

        for msg in messages:
            self._message_count += 1
            self._total_messages += 1

            # Format data
            if self.hex_mode_cb.isChecked():
                data_str = ' '.join(f'{b:02X}' for b in msg.data[:msg.dlc])
            else:
                data_str = ' '.join(f'{b:3d}' for b in msg.data[:msg.dlc])

            # Try to decode common OBD-II PIDs
            decoded = self._decode_obd_message(msg)

            # Format line
            line = f"{timestamp} | 0x{msg.id:03X} | {msg.dlc}   | {data_str:<24} | {decoded}"
            self.terminal.appendPlainText(line)

        # Update counters
        self.count_label.setText(f"Messages: {self._total_messages}")
        self.rate_label.setText(f"{len(messages)} msg/s")

        # Auto-scroll
        if self.auto_scroll_cb.isChecked():
            self.terminal.moveCursor(QTextCursor.MoveOperation.End)

    def _decode_obd_message(self, msg: CANMessage) -> str:
        """Try to decode common OBD-II PIDs"""
        if msg.dlc < 3:
            return ""

        data = msg.data

        # Check if it's an OBD-II response (mode 0x41)
        if data[0] != 0x41:
            return ""

        pid = data[1]

        # Common PIDs
        if pid == 0x0C and msg.dlc >= 4:  # RPM
            rpm = ((data[2] * 256) + data[3]) / 4
            return f"RPM: {rpm:.0f}"
        elif pid == 0x0D:  # Vehicle speed
            speed = data[2]
            return f"Speed: {speed} km/h"
        elif pid == 0x05:  # Coolant temp
            temp = data[2] - 40
            return f"Coolant: {temp}C"
        elif pid == 0x0F:  # Intake air temp
            temp = data[2] - 40
            return f"IAT: {temp}C"
        elif pid == 0x11 and msg.dlc >= 3:  # Throttle position
            throttle = (data[2] * 100) / 255
            return f"Throttle: {throttle:.1f}%"
        elif pid == 0x2F:  # Fuel level
            fuel = (data[2] * 100) / 255
            return f"Fuel: {fuel:.1f}%"
        elif pid == 0x46:  # Ambient temp
            temp = data[2] - 40
            return f"Ambient: {temp}C"

        return ""

    def clear(self):
        """Clear terminal display"""
        self.terminal.clear()
        self._add_header()
        self._total_messages = 0
        self.count_label.setText("Messages: 0")

    def reset(self):
        """Reset display"""
        self.clear()
        self._paused = False
        self.pause_btn.setText("Pause")
