"""
IOVENADO DataLogger - Headless Mode

Runs datalogger without GUI, suitable for remote control
and background operation on Raspberry Pi.
Reads from dual ESP32 sensor hubs simultaneously.
"""

import time
import signal
import sys
from threading import Event
from typing import Optional

from PySide6.QtCore import QCoreApplication

from .serial_reader import DualPacketSynchronizer
from .data_logger import CSVDataLogger
from .packet import SensorPacket
from config.settings import DATA_OUTPUT_DIR


class HeadlessDataLogger:
    """
    Headless datalogger - runs without GUI.
    Reads from dual ESP32 sensor hubs (GPS+CAN, Lidar+CO2).
    Suitable for remote control via Bluetooth or command line.
    """

    def __init__(self):
        """Initialize headless datalogger."""
        self.synchronizer: Optional[DualPacketSynchronizer] = None
        self.data_logger = CSVDataLogger(DATA_OUTPUT_DIR)
        self.running = False
        self.stop_event = Event()
        self.packet_count = 0
        self.start_time = 0

        # ESP32 connection states
        self._esp32_1_connected = False
        self._esp32_2_connected = False

        # Qt event loop for signals
        self.app = QCoreApplication.instance()
        if self.app is None:
            self.app = QCoreApplication(sys.argv)

        # Setup signal handlers for clean shutdown
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)

    def start(self, record: bool = False):
        """
        Start the headless datalogger.

        Args:
            record: Start recording immediately
        """
        print("[HeadlessDataLogger] Starting dual ESP32 mode...")

        # Create synchronizer for dual ESP32
        self.synchronizer = DualPacketSynchronizer()

        # Connect signals
        self.synchronizer.packet_received.connect(self._on_packet_received)
        self.synchronizer.esp32_1_connected.connect(self._on_esp32_1_connection)
        self.synchronizer.esp32_2_connected.connect(self._on_esp32_2_connection)
        self.synchronizer.error_occurred.connect(self._on_error)

        # Start serial readers
        self.synchronizer.start()

        # Start recording if requested
        if record:
            session_id = self.data_logger.start_session()
            print(f"[HeadlessDataLogger] Recording started: {session_id}")

        self.running = True
        self.start_time = time.time()

    def stop(self):
        """Stop the headless datalogger"""
        if not self.running:
            return

        print("[HeadlessDataLogger] Stopping...")

        # Stop recording if active
        if self.data_logger.is_recording:
            session_id = self.data_logger.session_id
            packet_count = self.data_logger.packet_count
            self.data_logger.stop_session()
            print(f"[HeadlessDataLogger] Recording stopped: {session_id} ({packet_count} packets)")

        # Stop synchronizer
        if self.synchronizer:
            self.synchronizer.stop()

        self.running = False
        self.stop_event.set()

    def run(self, duration: int = 0):
        """
        Run the main loop.

        Args:
            duration: Duration in seconds (0 = run until stopped)
        """
        print(f"[HeadlessDataLogger] Running...")

        if duration > 0:
            print(f"[HeadlessDataLogger] Will stop after {duration} seconds")
            end_time = time.time() + duration

            while self.running and time.time() < end_time:
                # Process Qt events
                self.app.processEvents()

                # Print status every 10 seconds
                elapsed = int(time.time() - self.start_time)
                if elapsed > 0 and elapsed % 10 == 0:
                    self._print_status()

                time.sleep(0.1)

            # Duration elapsed
            print(f"[HeadlessDataLogger] Duration {duration}s elapsed")
            self.stop()

        else:
            # Run until stopped externally (Ctrl+C or signal)
            print("[HeadlessDataLogger] Running indefinitely (Ctrl+C to stop)")
            last_status = 0

            while self.running:
                # Process Qt events
                self.app.processEvents()

                # Print status every 10 seconds
                current_time = int(time.time() - self.start_time)
                if current_time > 0 and current_time % 10 == 0 and current_time != last_status:
                    self._print_status()
                    last_status = current_time

                time.sleep(0.1)

    def _on_packet_received(self, packet: SensorPacket):
        """Handle received packet"""
        self.packet_count += 1

        # Write to CSV if recording
        if self.data_logger.is_recording:
            self.data_logger.write_packet(packet)

    def _on_esp32_1_connection(self, connected: bool):
        """Handle ESP32 #1 connection state change"""
        self._esp32_1_connected = connected
        status = "CONNECTED" if connected else "DISCONNECTED"
        print(f"[HeadlessDataLogger] ESP32-1 (GPS+CAN): {status}")

    def _on_esp32_2_connection(self, connected: bool):
        """Handle ESP32 #2 connection state change"""
        self._esp32_2_connected = connected
        status = "CONNECTED" if connected else "DISCONNECTED"
        print(f"[HeadlessDataLogger] ESP32-2 (Lidar+CO2): {status}")

    def _on_error(self, error_msg: str):
        """Handle error"""
        print(f"[HeadlessDataLogger] ERROR: {error_msg}", file=sys.stderr)

    def _print_status(self):
        """Print current status"""
        uptime = int(time.time() - self.start_time)
        status = "RECORDING" if self.data_logger.is_recording else "NOT RECORDING"
        recorded = self.data_logger.packet_count if self.data_logger.is_recording else 0

        esp1 = "OK" if self._esp32_1_connected else "--"
        esp2 = "OK" if self._esp32_2_connected else "--"

        print(f"[Status] Uptime: {uptime}s | ESP32-1: {esp1} | ESP32-2: {esp2} | "
              f"{status} | Packets: {self.packet_count} | Recorded: {recorded}")

    def _signal_handler(self, signum, frame):
        """Handle termination signals"""
        print(f"\n[HeadlessDataLogger] Received signal {signum}")
        self.stop()
