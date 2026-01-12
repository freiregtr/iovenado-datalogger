"""
IOVENADO DataLogger - Packet Data Structures

Binary packet format from ESP32:
- Header: 0xAA 0x55
- Length: 2 bytes (uint16 LE)
- Timestamp: 4 bytes (uint32 LE) - millis() from ESP32
- Status: 1 byte (bitmap)
- GPS: lat(4) + lon(4) + speed(4) = 12 bytes
- Lidar: distance(2) + strength(2) = 4 bytes
- CO2: ppm(2) = 2 bytes
- CAN count: 1 byte
- CAN messages: 13 bytes each (id:4 + dlc:1 + data:8)
- Checksum: 1 byte (XOR)
- Footer: 0x0D 0x0A
"""

from dataclasses import dataclass, field
from typing import List


@dataclass
class CANMessage:
    """Single CAN bus message"""
    id: int
    dlc: int
    data: bytes

    def __repr__(self):
        data_hex = ' '.join(f'{b:02X}' for b in self.data[:self.dlc])
        return f"CAN[0x{self.id:03X}] DLC={self.dlc}: {data_hex}"

    def to_hex_string(self) -> str:
        """Return data as hex string"""
        return ' '.join(f'{b:02X}' for b in self.data[:self.dlc])


@dataclass
class SensorPacket:
    """Complete sensor data packet from ESP32"""
    # Metadata
    timestamp: int = 0
    status: int = 0

    # GPS data
    gps_fix: bool = False
    gps_connected: bool = False
    latitude: float = 0.0
    longitude: float = 0.0
    speed_knots: float = 0.0

    # Lidar data
    lidar_connected: bool = False
    distance_cm: int = 0
    lidar_strength: int = 0

    # CO2 data
    co2_connected: bool = False
    co2_ppm: int = 0

    # CAN data
    can_active: bool = False
    can_messages: List[CANMessage] = field(default_factory=list)

    @property
    def speed_kmh(self) -> float:
        """Convert speed from knots to km/h"""
        return self.speed_knots * 1.852

    @property
    def speed_mph(self) -> float:
        """Convert speed from knots to mph"""
        return self.speed_knots * 1.15078

    @property
    def distance_m(self) -> float:
        """Convert distance from cm to meters"""
        return self.distance_cm / 100.0

    def get_status_string(self) -> str:
        """Return human-readable status string"""
        parts = []
        if self.gps_connected:
            parts.append(f"GPS:{'FIX' if self.gps_fix else 'NO_FIX'}")
        else:
            parts.append("GPS:OFF")

        parts.append(f"LIDAR:{'OK' if self.lidar_connected else 'OFF'}")
        parts.append(f"CO2:{'OK' if self.co2_connected else 'OFF'}")
        parts.append(f"CAN:{'OK' if self.can_active else 'OFF'}")

        return f"[{'] ['.join(parts)}]"

    def __repr__(self):
        return (
            f"SensorPacket(ts={self.timestamp}, status=0x{self.status:02X}, "
            f"GPS=({self.latitude:.6f}, {self.longitude:.6f}), "
            f"Lidar={self.distance_cm}cm, CO2={self.co2_ppm}ppm, "
            f"CAN={len(self.can_messages)} msgs)"
        )
