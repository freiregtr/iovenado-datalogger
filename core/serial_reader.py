"""
IOVENADO DataLogger - Serial Packet Reader

Reads binary packets from ESP32 via UART and emits Qt signals.
Runs in a separate QThread for non-blocking operation.
"""

import struct
from typing import Optional

from PySide6.QtCore import QObject, QThread, Signal

from .packet import SensorPacket, CANMessage
from config.settings import (
    SERIAL_PORT, SERIAL_BAUDRATE, SERIAL_TIMEOUT,
    PACKET_HEADER, PACKET_FOOTER,
    STATUS_GPS_FIX, STATUS_GPS_CONN,
    STATUS_LIDAR_CONN, STATUS_CO2_CONN, STATUS_CAN_ACTIVE
)

try:
    import serial
    SERIAL_AVAILABLE = True
except ImportError:
    SERIAL_AVAILABLE = False


class SerialPacketReader(QObject):
    """
    Reads binary packets from ESP32 sensor hub.

    Signals:
        packet_received: Emitted when a valid packet is decoded
        connection_changed: Emitted when serial connection state changes
        error_occurred: Emitted on errors
    """

    packet_received = Signal(object)  # SensorPacket
    connection_changed = Signal(bool)
    error_occurred = Signal(str)

    def __init__(self, port: str = None, baudrate: int = None, parent=None):
        super().__init__(parent)
        self.port = port or SERIAL_PORT
        self.baudrate = baudrate or SERIAL_BAUDRATE
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
            self.connection_changed.emit(True)

            while self.running:
                packet = self._read_packet()
                if packet:
                    self.packet_received.emit(packet)

        except serial.SerialException as e:
            self.error_occurred.emit(f"Serial error: {e}")
        except Exception as e:
            self.error_occurred.emit(f"Error: {e}")
        finally:
            if self.serial and self.serial.is_open:
                self.serial.close()
            self.connection_changed.emit(False)

    def _read_packet(self) -> Optional[SensorPacket]:
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

        # Validate length (min 31 bytes, max ~1300 bytes)
        if length < 31 or length > 1500:
            return None

        # Read remaining bytes (length - 4 already read: header + length)
        remaining = self.serial.read(length - 4)
        if len(remaining) < length - 4:
            return None

        # Reconstruct full packet
        raw = PACKET_HEADER + length_bytes + remaining

        return self._decode_packet(raw)

    def _decode_packet(self, raw: bytes) -> Optional[SensorPacket]:
        """Decode binary packet into SensorPacket"""
        try:
            # Verify footer
            if raw[-2:] != PACKET_FOOTER:
                return None

            # Verify checksum (XOR of bytes from length to before checksum)
            checksum_data = raw[2:-3]  # Skip header, checksum, and footer
            calculated_checksum = 0
            for b in checksum_data:
                calculated_checksum ^= b
            if calculated_checksum != raw[-3]:
                return None

            # Extract fixed fields
            timestamp = struct.unpack('<I', raw[4:8])[0]
            status = raw[8]

            # GPS data (offsets 9-20)
            latitude = struct.unpack('<f', raw[9:13])[0]
            longitude = struct.unpack('<f', raw[13:17])[0]
            speed_knots = struct.unpack('<f', raw[17:21])[0]

            # Lidar data (offsets 21-24)
            distance_cm = struct.unpack('<H', raw[21:23])[0]
            lidar_strength = struct.unpack('<H', raw[23:25])[0]

            # CO2 data (offsets 25-26)
            co2_ppm = struct.unpack('<H', raw[25:27])[0]

            # CAN data
            can_count = raw[27]
            can_messages = []
            offset = 28

            for _ in range(can_count):
                if offset + 13 > len(raw) - 3:  # Ensure enough bytes
                    break
                can_id = struct.unpack('<I', raw[offset:offset+4])[0]
                dlc = raw[offset+4]
                data = bytes(raw[offset+5:offset+13])
                can_messages.append(CANMessage(can_id, dlc, data))
                offset += 13

            return SensorPacket(
                timestamp=timestamp,
                status=status,
                gps_fix=bool(status & STATUS_GPS_FIX),
                gps_connected=bool(status & STATUS_GPS_CONN),
                latitude=latitude,
                longitude=longitude,
                speed_knots=speed_knots,
                lidar_connected=bool(status & STATUS_LIDAR_CONN),
                distance_cm=distance_cm,
                lidar_strength=lidar_strength,
                co2_connected=bool(status & STATUS_CO2_CONN),
                co2_ppm=co2_ppm,
                can_active=bool(status & STATUS_CAN_ACTIVE),
                can_messages=can_messages
            )

        except Exception:
            return None


class MockSerialReader(QObject):
    """
    Mock serial reader for testing without hardware.
    Generates simulated sensor data.
    """

    packet_received = Signal(object)
    connection_changed = Signal(bool)
    error_occurred = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.running = False
        self._thread: Optional[QThread] = None
        self._counter = 0

    def start(self):
        """Start generating mock data"""
        from PySide6.QtCore import QTimer
        self.running = True
        self.connection_changed.emit(True)

        self._timer = QTimer(self)
        self._timer.timeout.connect(self._generate_packet)
        self._timer.start(1000)  # 1 Hz

    def stop(self):
        """Stop generating"""
        self.running = False
        if hasattr(self, '_timer'):
            self._timer.stop()
        self.connection_changed.emit(False)

    def _generate_packet(self):
        """Generate a mock packet"""
        import math
        import random

        self._counter += 1

        # Simulate moving GPS position
        base_lat = 10.308617
        base_lon = -84.087334
        lat = base_lat + math.sin(self._counter / 10) * 0.001
        lon = base_lon + math.cos(self._counter / 10) * 0.001

        # Simulate varying sensor values
        distance = 300 + int(50 * math.sin(self._counter / 5))
        co2 = 500 + int(100 * math.sin(self._counter / 20))

        # Generate some mock CAN messages
        can_msgs = []
        if random.random() > 0.3:
            can_msgs.append(CANMessage(
                id=0x7E8,
                dlc=8,
                data=bytes([0x41, 0x0C, 0x1A, 0xF8, 0x00, 0x00, 0x00, 0x00])
            ))
        if random.random() > 0.5:
            can_msgs.append(CANMessage(
                id=0x7E8,
                dlc=8,
                data=bytes([0x41, 0x0D, random.randint(0, 120), 0x00, 0x00, 0x00, 0x00, 0x00])
            ))

        packet = SensorPacket(
            timestamp=self._counter * 1000,
            status=0x1F,  # All connected
            gps_fix=True,
            gps_connected=True,
            latitude=lat,
            longitude=lon,
            speed_knots=22.5 + random.uniform(-2, 2),
            lidar_connected=True,
            distance_cm=distance,
            lidar_strength=800 + random.randint(-50, 50),
            co2_connected=True,
            co2_ppm=co2,
            can_active=len(can_msgs) > 0,
            can_messages=can_msgs
        )

        self.packet_received.emit(packet)
