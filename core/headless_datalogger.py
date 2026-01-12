"""
IOVENADO DataLogger - Headless Mode

Runs datalogger without GUI, suitable for remote control
and background operation on Raspberry Pi.
"""

import time
import signal
import sys
from threading import Event
from typing import Optional

from .serial_reader import SerialPacketReader, MockSerialReader
from .data_logger import CSVDataLogger
from .packet import SensorPacket
from config.settings import DATA_OUTPUT_DIR, SERIAL_PORT


class HeadlessDataLogger:
    """
    Headless datalogger - runs without GUI.
    Suitable for remote control via Bluetooth or command line.
    """

    def __init__(self, use_mock: bool = False, port: Optional[str] = None):
        """
        Initialize headless datalogger.

        Args:
            use_mock: Use mock serial reader (simulated data)
            port: Serial port to use (overrides settings)
        """
        self.use_mock = use_mock
        self.port = port
        self.serial_reader: Optional[SerialPacketReader] = None
        self.data_logger = CSVDataLogger(DATA_OUTPUT_DIR)
        self.running = False
        self.stop_event = Event()
        self.packet_count = 0
        self.start_time = 0

        # Setup signal handlers for clean shutdown
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)

    def start(self, record: bool = False):
        """
        Start the headless datalogger.

        Args:
            record: Start recording immediately
        """
        print("[HeadlessDataLogger] Starting...")

        # Create serial reader
        if self.use_mock:
            print("[HeadlessDataLogger] Using MOCK serial reader")
            self.serial_reader = MockSerialReader()
        else:
            port = self.port or SERIAL_PORT
            print(f"[HeadlessDataLogger] Using serial port: {port}")
            self.serial_reader = SerialPacketReader()

        # Connect signals (using direct function call instead of Qt signals)
        # Note: In headless mode, we'll use a polling approach
        self.serial_reader.packet_received.connect(self._on_packet_received)
        self.serial_reader.connection_changed.connect(self._on_connection_changed)
        self.serial_reader.error_occurred.connect(self._on_error)

        # Start serial reader
        self.serial_reader.start()

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

        # Stop serial reader
        if self.serial_reader:
            self.serial_reader.stop()

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
                # Print status every 10 seconds
                if int(time.time() - self.start_time) % 10 == 0:
                    self._print_status()
                time.sleep(1)

            # Duration elapsed
            print(f"[HeadlessDataLogger] Duration {duration}s elapsed")
            self.stop()

        else:
            # Run until stopped externally (Ctrl+C or signal)
            print("[HeadlessDataLogger] Running indefinitely (Ctrl+C to stop)")
            last_status = 0

            while self.running:
                # Print status every 10 seconds
                current_time = int(time.time() - self.start_time)
                if current_time > 0 and current_time % 10 == 0 and current_time != last_status:
                    self._print_status()
                    last_status = current_time

                time.sleep(1)

    def _on_packet_received(self, packet: SensorPacket):
        """Handle received packet"""
        self.packet_count += 1

        # Write to CSV if recording
        if self.data_logger.is_recording:
            self.data_logger.write_packet(packet)

    def _on_connection_changed(self, connected: bool):
        """Handle connection state change"""
        if connected:
            print("[HeadlessDataLogger] Serial connection established")
        else:
            print("[HeadlessDataLogger] Serial connection lost")

    def _on_error(self, error_msg: str):
        """Handle error"""
        print(f"[HeadlessDataLogger] ERROR: {error_msg}", file=sys.stderr)

    def _print_status(self):
        """Print current status"""
        uptime = int(time.time() - self.start_time)
        status = "RECORDING" if self.data_logger.is_recording else "NOT RECORDING"
        recorded = self.data_logger.packet_count if self.data_logger.is_recording else 0

        print(f"[Status] Uptime: {uptime}s | {status} | "
              f"Packets received: {self.packet_count} | Packets recorded: {recorded}")

    def _signal_handler(self, signum, frame):
        """Handle termination signals"""
        print(f"\n[HeadlessDataLogger] Received signal {signum}")
        self.stop()
