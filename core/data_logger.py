"""
IOVENADO DataLogger - CSV Data Logger

Handles recording sensor data to CSV files.
Creates separate CSV files for each sensor type.
"""

import os
import csv
from datetime import datetime
from typing import List, Dict, Optional
from zipfile import ZipFile

from .packet import SensorPacket, CANMessage


class CSVDataLogger:
    """
    Manages recording of sensor data to CSV files.
    Creates one CSV file per sensor type (GPS, Lidar, CO2, CAN).
    """

    def __init__(self, output_dir: str = "./data"):
        """
        Initialize CSV data logger.

        Args:
            output_dir: Directory where CSV files will be saved
        """
        self.output_dir = output_dir
        self.session_id: Optional[str] = None
        self.is_recording = False
        self.csv_files: Dict[str, any] = {}
        self.csv_writers: Dict[str, csv.DictWriter] = {}
        self.packet_count = 0

        # Create output directory if it doesn't exist
        os.makedirs(self.output_dir, exist_ok=True)

    def start_session(self) -> str:
        """
        Start a new recording session.
        Creates CSV files with headers.

        Returns:
            session_id (timestamp string)
        """
        if self.is_recording:
            raise RuntimeError("Session already in progress")

        # Generate session ID from current timestamp
        self.session_id = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        self.packet_count = 0

        # Open CSV files
        self._open_csv_files()

        self.is_recording = True
        print(f"[DataLogger] Started session: {self.session_id}")

        return self.session_id

    def stop_session(self):
        """
        Stop the current recording session.
        Closes all CSV files.
        """
        if not self.is_recording:
            return

        # Close all CSV files
        self._close_csv_files()

        print(f"[DataLogger] Stopped session: {self.session_id} ({self.packet_count} packets)")

        self.is_recording = False

    def write_packet(self, packet: SensorPacket):
        """
        Write a sensor packet to CSV files.

        Args:
            packet: SensorPacket to write
        """
        if not self.is_recording:
            return

        # Write GPS data
        self.csv_writers['gps'].writerow({
            'timestamp_ms': packet.timestamp,
            'latitude': packet.latitude,
            'longitude': packet.longitude,
            'speed_knots': packet.speed_knots,
            'speed_kmh': packet.speed_kmh,
            'gps_fix': packet.gps_fix,
            'gps_connected': packet.gps_connected
        })

        # Write Lidar data
        self.csv_writers['lidar'].writerow({
            'timestamp_ms': packet.timestamp,
            'distance_cm': packet.distance_cm,
            'distance_m': packet.distance_m,
            'lidar_strength': packet.lidar_strength,
            'lidar_connected': packet.lidar_connected
        })

        # Write CO2 data
        self.csv_writers['co2'].writerow({
            'timestamp_ms': packet.timestamp,
            'co2_ppm': packet.co2_ppm,
            'co2_connected': packet.co2_connected
        })

        # Write CAN bus data (multiple messages per packet)
        for can_msg in packet.can_messages:
            self.csv_writers['canbus'].writerow({
                'timestamp_ms': packet.timestamp,
                'can_id': f'0x{can_msg.id:03X}',
                'dlc': can_msg.dlc,
                'data_hex': can_msg.to_hex_string(),
                'decoded': self._decode_can_message(can_msg)
            })

        # Flush files every 10 packets to avoid data loss
        self.packet_count += 1
        if self.packet_count % 10 == 0:
            for f in self.csv_files.values():
                f.flush()

    def get_session_files(self) -> List[str]:
        """
        Get list of CSV file paths for current session.

        Returns:
            List of absolute file paths
        """
        if not self.session_id:
            return []

        files = []
        for sensor in ['gps', 'lidar', 'co2', 'canbus']:
            filename = f"{sensor}_{self.session_id}.csv"
            filepath = os.path.join(self.output_dir, filename)
            if os.path.exists(filepath):
                files.append(filepath)

        return files

    def export_session_zip(self, session_id: Optional[str] = None,
                          output_path: Optional[str] = None) -> str:
        """
        Export session CSV files to a ZIP archive.

        Args:
            session_id: Session ID to export (default: current session)
            output_path: Output ZIP file path (default: auto-generated)

        Returns:
            Path to created ZIP file
        """
        if session_id is None:
            session_id = self.session_id

        if not session_id:
            raise ValueError("No session to export")

        # Find all CSV files for this session
        csv_files = []
        for sensor in ['gps', 'lidar', 'co2', 'canbus']:
            filename = f"{sensor}_{session_id}.csv"
            filepath = os.path.join(self.output_dir, filename)
            if os.path.exists(filepath):
                csv_files.append(filepath)

        if not csv_files:
            raise FileNotFoundError(f"No CSV files found for session {session_id}")

        # Generate ZIP file path
        if output_path is None:
            output_path = os.path.join(self.output_dir, f"session_{session_id}.zip")

        # Create ZIP archive
        with ZipFile(output_path, 'w') as zipf:
            for filepath in csv_files:
                # Add file to ZIP with just the filename (no path)
                zipf.write(filepath, os.path.basename(filepath))

        print(f"[DataLogger] Exported session to: {output_path}")
        return output_path

    def _open_csv_files(self):
        """Open CSV files and write headers"""
        # GPS CSV
        gps_filename = f"gps_{self.session_id}.csv"
        gps_path = os.path.join(self.output_dir, gps_filename)
        self.csv_files['gps'] = open(gps_path, 'w', newline='')
        self.csv_writers['gps'] = csv.DictWriter(
            self.csv_files['gps'],
            fieldnames=['timestamp_ms', 'latitude', 'longitude', 'speed_knots',
                       'speed_kmh', 'gps_fix', 'gps_connected']
        )
        self.csv_writers['gps'].writeheader()

        # Lidar CSV
        lidar_filename = f"lidar_{self.session_id}.csv"
        lidar_path = os.path.join(self.output_dir, lidar_filename)
        self.csv_files['lidar'] = open(lidar_path, 'w', newline='')
        self.csv_writers['lidar'] = csv.DictWriter(
            self.csv_files['lidar'],
            fieldnames=['timestamp_ms', 'distance_cm', 'distance_m',
                       'lidar_strength', 'lidar_connected']
        )
        self.csv_writers['lidar'].writeheader()

        # CO2 CSV
        co2_filename = f"co2_{self.session_id}.csv"
        co2_path = os.path.join(self.output_dir, co2_filename)
        self.csv_files['co2'] = open(co2_path, 'w', newline='')
        self.csv_writers['co2'] = csv.DictWriter(
            self.csv_files['co2'],
            fieldnames=['timestamp_ms', 'co2_ppm', 'co2_connected']
        )
        self.csv_writers['co2'].writeheader()

        # CAN bus CSV
        canbus_filename = f"canbus_{self.session_id}.csv"
        canbus_path = os.path.join(self.output_dir, canbus_filename)
        self.csv_files['canbus'] = open(canbus_path, 'w', newline='')
        self.csv_writers['canbus'] = csv.DictWriter(
            self.csv_files['canbus'],
            fieldnames=['timestamp_ms', 'can_id', 'dlc', 'data_hex', 'decoded']
        )
        self.csv_writers['canbus'].writeheader()

    def _close_csv_files(self):
        """Close all CSV files"""
        for f in self.csv_files.values():
            f.close()

        self.csv_files.clear()
        self.csv_writers.clear()

    def _decode_can_message(self, msg: CANMessage) -> str:
        """
        Decode common OBD-II CAN messages.

        Args:
            msg: CANMessage to decode

        Returns:
            Decoded string or empty if unknown
        """
        # Check if this is an OBD-II response (mode 01, 41 response)
        if msg.dlc >= 3 and msg.data[0] == 0x41:
            pid = msg.data[1]

            # RPM (PID 0x0C)
            if pid == 0x0C and msg.dlc >= 4:
                rpm = ((msg.data[2] << 8) | msg.data[3]) / 4.0
                return f"RPM: {int(rpm)}"

            # Vehicle Speed (PID 0x0D)
            elif pid == 0x0D and msg.dlc >= 3:
                speed = msg.data[2]
                return f"Speed: {speed} km/h"

            # Coolant Temperature (PID 0x05)
            elif pid == 0x05 and msg.dlc >= 3:
                temp = msg.data[2] - 40
                return f"Coolant: {temp}C"

            # Intake Air Temperature (PID 0x0F)
            elif pid == 0x0F and msg.dlc >= 3:
                temp = msg.data[2] - 40
                return f"Intake Air: {temp}C"

            # Throttle Position (PID 0x11)
            elif pid == 0x11 and msg.dlc >= 3:
                throttle = (msg.data[2] * 100) / 255.0
                return f"Throttle: {throttle:.1f}%"

            # Fuel Level (PID 0x2F)
            elif pid == 0x2F and msg.dlc >= 3:
                fuel = (msg.data[2] * 100) / 255.0
                return f"Fuel: {fuel:.1f}%"

        return ""
