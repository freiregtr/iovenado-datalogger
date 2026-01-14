"""
IOVENADO DataLogger - Dual ESP32 Serial Readers

Reads binary packets from two ESP32 devices via UART and synchronizes them.

ESP32 #1 (ttyAMA0): GPS + CAN - Variable length packets (25+ bytes)
ESP32 #2 (ttyAMA2): Lidar + CO2 - Fixed 18 byte packets

Both ESP32s send packets at 1Hz with their own timestamps.
DualPacketSynchronizer fuses data from both into a single SensorPacket.
"""

import struct
import time
from typing import Optional, Dict, Any

from PySide6.QtCore import QObject, QThread, Signal

from .packet import SensorPacket, CANMessage
from config.settings import (
    ESP32_1_PORT, ESP32_1_BAUDRATE,
    ESP32_2_PORT, ESP32_2_BAUDRATE,
    SERIAL_TIMEOUT,
    PACKET_HEADER, PACKET_FOOTER,
    STATUS_GPS_FIX, STATUS_GPS_CONN, STATUS_CAN_ACTIVE,
    STATUS_LIDAR_CONN, STATUS_CO2_CONN,
    SYNC_WINDOW_MS, BUFFER_TIMEOUT_MS
)

try:
    import serial
    SERIAL_AVAILABLE = True
except ImportError:
    SERIAL_AVAILABLE = False


class ESP32_1_Reader(QObject):
    """
    Reads GPS + CAN packets from ESP32 #1 via /dev/ttyAMA0.

    Packet format (25+ bytes, variable due to CAN messages):
    - Header: 0xAA 0x55
    - Length: 2 bytes (uint16 LE)
    - Timestamp: 4 bytes (uint32 LE)
    - Status: 1 byte
    - GPS: lat(4) + lon(4) + speed(4) = 12 bytes (float LE)
    - CAN count: 1 byte
    - CAN messages: N * 13 bytes each
    - Checksum: 1 byte (XOR)
    - Footer: 0x0D 0x0A
    """

    packet_received = Signal(object)  # dict with GPS+CAN data
    connection_changed = Signal(bool)
    error_occurred = Signal(str)

    def __init__(self, port: str = None, baudrate: int = None, parent=None):
        super().__init__(parent)
        self.port = port or ESP32_1_PORT
        self.baudrate = baudrate or ESP32_1_BAUDRATE
        self.serial: Optional['serial.Serial'] = None
        self.running = False
        self._thread: Optional[QThread] = None

    def start(self):
        """Start reading in a separate thread"""
        if not SERIAL_AVAILABLE:
            self.error_occurred.emit("pyserial not installed")
            return

        self.running = True
        self._thread = QThread()
        self.moveToThread(self._thread)
        self._thread.started.connect(self._read_loop)
        self._thread.start()

    def stop(self):
        """Stop reading and cleanup"""
        self.running = False
        if self._thread:
            self._thread.quit()
            self._thread.wait(2000)
            self._thread = None

    def _read_loop(self):
        """Main reading loop - runs in thread"""
        try:
            self.serial = serial.Serial(
                self.port,
                self.baudrate,
                timeout=SERIAL_TIMEOUT
            )
            self.serial.reset_input_buffer()
            self.connection_changed.emit(True)

            while self.running:
                data = self._read_packet()
                if data:
                    self.packet_received.emit(data)

        except serial.SerialException as e:
            self.error_occurred.emit(f"ESP32 #1 Serial error: {e}")
        except Exception as e:
            self.error_occurred.emit(f"ESP32 #1 Error: {e}")
        finally:
            if self.serial and self.serial.is_open:
                self.serial.close()
            self.connection_changed.emit(False)

    def _read_packet(self) -> Optional[Dict[str, Any]]:
        """Read and decode a single packet"""
        if not self.serial or not self.serial.is_open:
            return None

        # Synchronize to header 0xAA 0x55
        while self.running:
            byte = self.serial.read(1)
            if not byte:
                continue
            if byte == b'\xAA':
                next_byte = self.serial.read(1)
                if next_byte == b'\x55':
                    break

        if not self.running:
            return None

        # Read length (2 bytes, little-endian)
        length_bytes = self.serial.read(2)
        if len(length_bytes) < 2:
            return None
        length = struct.unpack('<H', length_bytes)[0]

        # Validate length (min 25 bytes, max ~1400 bytes for 100 CAN msgs)
        if length < 25 or length > 1500:
            return None

        # Read remaining bytes
        bytes_to_read = length - 4  # Already read header + length
        remaining = self.serial.read(bytes_to_read)
        if len(remaining) < bytes_to_read:
            return None

        # Reconstruct full packet
        raw = PACKET_HEADER + length_bytes + remaining

        return self._decode_packet(raw)

    def _decode_packet(self, raw: bytes) -> Optional[Dict[str, Any]]:
        """Decode binary packet into dict"""
        try:
            # Verify footer
            if raw[-2:] != PACKET_FOOTER:
                return None

            # Verify checksum (XOR of bytes from offset 4 to before checksum)
            checksum_data = raw[4:-3]
            calculated_checksum = 0
            for b in checksum_data:
                calculated_checksum ^= b
            if calculated_checksum != raw[-3]:
                return None

            # Extract fields
            timestamp = struct.unpack('<I', raw[4:8])[0]
            status = raw[8]

            # GPS data
            latitude = struct.unpack('<f', raw[9:13])[0]
            longitude = struct.unpack('<f', raw[13:17])[0]
            speed_knots = struct.unpack('<f', raw[17:21])[0]

            # CAN data
            can_count = raw[21]
            can_messages = []
            offset = 22

            for _ in range(can_count):
                if offset + 13 > len(raw) - 3:
                    break
                can_id = struct.unpack('<I', raw[offset:offset+4])[0]
                dlc = raw[offset+4]
                data = bytes(raw[offset+5:offset+13])
                can_messages.append(CANMessage(can_id, dlc, data))
                offset += 13

            return {
                'timestamp': timestamp,
                'gps_fix': bool(status & STATUS_GPS_FIX),
                'gps_connected': bool(status & STATUS_GPS_CONN),
                'latitude': latitude,
                'longitude': longitude,
                'speed_knots': speed_knots,
                'can_active': bool(status & STATUS_CAN_ACTIVE),
                'can_messages': can_messages
            }

        except Exception:
            return None


class ESP32_2_Reader(QObject):
    """
    Reads Lidar + CO2 packets from ESP32 #2 via /dev/ttyAMA2.

    Packet format (18 bytes fixed):
    - Header: 0xAA 0x55
    - Length: 2 bytes (always 18)
    - Timestamp: 4 bytes (uint32 LE)
    - Status: 1 byte
    - Lidar distance: 2 bytes (uint16 LE, cm)
    - Lidar strength: 2 bytes (uint16 LE)
    - CO2: 2 bytes (uint16 LE, ppm)
    - Checksum: 1 byte (XOR)
    - Footer: 0x0D 0x0A
    """

    packet_received = Signal(object)  # dict with Lidar+CO2 data
    connection_changed = Signal(bool)
    error_occurred = Signal(str)

    PACKET_SIZE = 18

    def __init__(self, port: str = None, baudrate: int = None, parent=None):
        super().__init__(parent)
        self.port = port or ESP32_2_PORT
        self.baudrate = baudrate or ESP32_2_BAUDRATE
        self.serial: Optional['serial.Serial'] = None
        self.running = False
        self._thread: Optional[QThread] = None

    def start(self):
        """Start reading in a separate thread"""
        if not SERIAL_AVAILABLE:
            self.error_occurred.emit("pyserial not installed")
            return

        self.running = True
        self._thread = QThread()
        self.moveToThread(self._thread)
        self._thread.started.connect(self._read_loop)
        self._thread.start()

    def stop(self):
        """Stop reading and cleanup"""
        self.running = False
        if self._thread:
            self._thread.quit()
            self._thread.wait(2000)
            self._thread = None

    def _read_loop(self):
        """Main reading loop - runs in thread"""
        try:
            self.serial = serial.Serial(
                self.port,
                self.baudrate,
                timeout=SERIAL_TIMEOUT
            )
            self.serial.reset_input_buffer()
            self.connection_changed.emit(True)

            while self.running:
                data = self._read_packet()
                if data:
                    self.packet_received.emit(data)

        except serial.SerialException as e:
            self.error_occurred.emit(f"ESP32 #2 Serial error: {e}")
        except Exception as e:
            self.error_occurred.emit(f"ESP32 #2 Error: {e}")
        finally:
            if self.serial and self.serial.is_open:
                self.serial.close()
            self.connection_changed.emit(False)

    def _read_packet(self) -> Optional[Dict[str, Any]]:
        """Read and decode a single packet"""
        if not self.serial or not self.serial.is_open:
            return None

        # Synchronize to header 0xAA 0x55
        while self.running:
            byte = self.serial.read(1)
            if not byte:
                continue
            if byte == b'\xAA':
                next_byte = self.serial.read(1)
                if next_byte == b'\x55':
                    break

        if not self.running:
            return None

        # Read length (2 bytes, little-endian)
        length_bytes = self.serial.read(2)
        if len(length_bytes) < 2:
            return None
        length = struct.unpack('<H', length_bytes)[0]

        # Validate length (must be exactly 18 for ESP32 #2)
        if length != self.PACKET_SIZE:
            return None

        # Read remaining bytes
        bytes_to_read = length - 4  # Already read header + length
        remaining = self.serial.read(bytes_to_read)
        if len(remaining) < bytes_to_read:
            return None

        # Reconstruct full packet
        raw = PACKET_HEADER + length_bytes + remaining

        return self._decode_packet(raw)

    def _decode_packet(self, raw: bytes) -> Optional[Dict[str, Any]]:
        """Decode binary packet into dict"""
        try:
            # Verify footer
            if raw[-2:] != PACKET_FOOTER:
                return None

            # Verify checksum (XOR of bytes from offset 4 to before checksum)
            checksum_data = raw[4:-3]
            calculated_checksum = 0
            for b in checksum_data:
                calculated_checksum ^= b
            if calculated_checksum != raw[-3]:
                return None

            # Extract fields
            timestamp = struct.unpack('<I', raw[4:8])[0]
            status = raw[8]

            # Lidar data
            distance_cm = struct.unpack('<H', raw[9:11])[0]
            strength = struct.unpack('<H', raw[11:13])[0]

            # CO2 data
            co2_ppm = struct.unpack('<H', raw[13:15])[0]

            return {
                'timestamp': timestamp,
                'lidar_connected': bool(status & STATUS_LIDAR_CONN),
                'distance_cm': distance_cm,
                'lidar_strength': strength,
                'co2_connected': bool(status & STATUS_CO2_CONN),
                'co2_ppm': co2_ppm
            }

        except Exception:
            return None


class DualPacketSynchronizer(QObject):
    """
    Synchronizes packets from both ESP32 devices and emits unified SensorPacket.

    Strategy:
    - Maintains buffer with latest data from each ESP32
    - When data arrives from either ESP32:
      1. Updates corresponding buffer with timestamp
      2. If both buffers have recent data (< SYNC_WINDOW_MS apart)
         -> Fuses into SensorPacket and emits
      3. If one buffer has data but other timed out
         -> Emits partial SensorPacket with connected=False for missing sensor
    """

    packet_received = Signal(object)  # SensorPacket
    esp32_1_connected = Signal(bool)
    esp32_2_connected = Signal(bool)
    error_occurred = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)

        # Readers
        self._reader_1 = ESP32_1_Reader()
        self._reader_2 = ESP32_2_Reader()

        # Buffers for latest data
        self._buffer_esp32_1: Optional[Dict[str, Any]] = None
        self._buffer_esp32_2: Optional[Dict[str, Any]] = None

        # Timestamps (Pi system time when data was received)
        self._last_time_esp32_1: float = 0
        self._last_time_esp32_2: float = 0

        # Connection state
        self._esp32_1_connected = False
        self._esp32_2_connected = False

        # Connect reader signals
        self._reader_1.packet_received.connect(self._on_esp32_1_packet)
        self._reader_1.connection_changed.connect(self._on_esp32_1_connection)
        self._reader_1.error_occurred.connect(self._on_error)

        self._reader_2.packet_received.connect(self._on_esp32_2_packet)
        self._reader_2.connection_changed.connect(self._on_esp32_2_connection)
        self._reader_2.error_occurred.connect(self._on_error)

    def start(self):
        """Start both readers"""
        self._reader_1.start()
        self._reader_2.start()

    def stop(self):
        """Stop both readers"""
        self._reader_1.stop()
        self._reader_2.stop()

    def _on_esp32_1_packet(self, data: Dict[str, Any]):
        """Handle packet from ESP32 #1 (GPS + CAN)"""
        self._buffer_esp32_1 = data
        self._last_time_esp32_1 = time.time() * 1000  # ms
        self._try_emit_packet()

    def _on_esp32_2_packet(self, data: Dict[str, Any]):
        """Handle packet from ESP32 #2 (Lidar + CO2)"""
        self._buffer_esp32_2 = data
        self._last_time_esp32_2 = time.time() * 1000  # ms
        self._try_emit_packet()

    def _on_esp32_1_connection(self, connected: bool):
        """Handle ESP32 #1 connection state change"""
        self._esp32_1_connected = connected
        self.esp32_1_connected.emit(connected)
        if not connected:
            self._buffer_esp32_1 = None

    def _on_esp32_2_connection(self, connected: bool):
        """Handle ESP32 #2 connection state change"""
        self._esp32_2_connected = connected
        self.esp32_2_connected.emit(connected)
        if not connected:
            self._buffer_esp32_2 = None

    def _on_error(self, error_msg: str):
        """Forward error from readers"""
        self.error_occurred.emit(error_msg)

    def _try_emit_packet(self):
        """
        Try to emit a synchronized SensorPacket.

        Emits when:
        - Both buffers have recent data (within SYNC_WINDOW_MS)
        - OR one buffer has data and the other timed out (> BUFFER_TIMEOUT_MS)
        """
        now = time.time() * 1000  # ms

        # Check if we have data from ESP32 #1
        esp32_1_age = now - self._last_time_esp32_1 if self._last_time_esp32_1 > 0 else float('inf')
        esp32_1_valid = esp32_1_age < BUFFER_TIMEOUT_MS and self._buffer_esp32_1 is not None

        # Check if we have data from ESP32 #2
        esp32_2_age = now - self._last_time_esp32_2 if self._last_time_esp32_2 > 0 else float('inf')
        esp32_2_valid = esp32_2_age < BUFFER_TIMEOUT_MS and self._buffer_esp32_2 is not None

        # Need at least one valid buffer to emit
        if not esp32_1_valid and not esp32_2_valid:
            return

        # Check synchronization window
        if esp32_1_valid and esp32_2_valid:
            time_diff = abs(self._last_time_esp32_1 - self._last_time_esp32_2)
            if time_diff > SYNC_WINDOW_MS:
                # Data too far apart, wait for sync
                return

        # Build SensorPacket
        packet = self._build_sensor_packet(esp32_1_valid, esp32_2_valid)
        self.packet_received.emit(packet)

    def _build_sensor_packet(self, esp32_1_valid: bool, esp32_2_valid: bool) -> SensorPacket:
        """Build unified SensorPacket from buffers"""

        # GPS + CAN data from ESP32 #1
        if esp32_1_valid and self._buffer_esp32_1:
            gps_fix = self._buffer_esp32_1.get('gps_fix', False)
            gps_connected = self._buffer_esp32_1.get('gps_connected', False)
            latitude = self._buffer_esp32_1.get('latitude', 0.0)
            longitude = self._buffer_esp32_1.get('longitude', 0.0)
            speed_knots = self._buffer_esp32_1.get('speed_knots', 0.0)
            can_active = self._buffer_esp32_1.get('can_active', False)
            can_messages = self._buffer_esp32_1.get('can_messages', [])
            timestamp_1 = self._buffer_esp32_1.get('timestamp', 0)
        else:
            gps_fix = False
            gps_connected = False
            latitude = 0.0
            longitude = 0.0
            speed_knots = 0.0
            can_active = False
            can_messages = []
            timestamp_1 = 0

        # Lidar + CO2 data from ESP32 #2
        if esp32_2_valid and self._buffer_esp32_2:
            lidar_connected = self._buffer_esp32_2.get('lidar_connected', False)
            distance_cm = self._buffer_esp32_2.get('distance_cm', 0)
            lidar_strength = self._buffer_esp32_2.get('lidar_strength', 0)
            co2_connected = self._buffer_esp32_2.get('co2_connected', False)
            co2_ppm = self._buffer_esp32_2.get('co2_ppm', 0)
            timestamp_2 = self._buffer_esp32_2.get('timestamp', 0)
        else:
            lidar_connected = False
            distance_cm = 0
            lidar_strength = 0
            co2_connected = False
            co2_ppm = 0
            timestamp_2 = 0

        # Use most recent timestamp
        timestamp = max(timestamp_1, timestamp_2)

        # Build combined status byte for UI display
        status = 0
        if gps_fix:
            status |= 0x01
        if gps_connected:
            status |= 0x02
        if can_active:
            status |= 0x04
        if lidar_connected:
            status |= 0x08
        if co2_connected:
            status |= 0x10

        return SensorPacket(
            timestamp=timestamp,
            status=status,
            # GPS
            gps_fix=gps_fix,
            gps_connected=gps_connected,
            latitude=latitude,
            longitude=longitude,
            speed_knots=speed_knots,
            # Lidar
            lidar_connected=lidar_connected,
            distance_cm=distance_cm,
            lidar_strength=lidar_strength,
            # CO2
            co2_connected=co2_connected,
            co2_ppm=co2_ppm,
            # CAN
            can_active=can_active,
            can_messages=can_messages
        )
