"""
IOVENADO DataLogger - CSV Data Logger

Handles recording sensor data to CSV files.
Creates a single unified CSV file with all sensor data.
"""

import os
import csv
import json
from datetime import datetime
from typing import List, Dict, Optional
from zipfile import ZipFile

from .packet import SensorPacket, CANMessage


class CSVDataLogger:
    """
    Manages recording of sensor data to CSV files.
    Creates one unified CSV file with all sensor data.
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
        self.csv_file = None
        self.csv_writer: Optional[csv.DictWriter] = None
        self.packet_count = 0

        # Create output directory if it doesn't exist
        os.makedirs(self.output_dir, exist_ok=True)

    def start_session(self) -> str:
        """
        Start a new recording session.
        Creates CSV file with headers.

        Returns:
            session_id (timestamp string)
        """
        if self.is_recording:
            raise RuntimeError("Session already in progress")

        # Generate session ID from current timestamp
        self.session_id = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        self.packet_count = 0

        # Open CSV file
        self._open_csv_file()

        self.is_recording = True
        print(f"[DataLogger] Started session: {self.session_id}")

        return self.session_id

    def stop_session(self):
        """
        Stop the current recording session.
        Closes CSV file and automatically creates ZIP archive.
        """
        if not self.is_recording:
            return

        # Close CSV file
        self._close_csv_file()

        print(f"[DataLogger] Stopped session: {self.session_id} ({self.packet_count} packets)")

        # Automatically compress to ZIP
        try:
            zip_path = self._create_session_zip()
            print(f"[DataLogger] Created ZIP archive: {zip_path}")

            # Delete original CSV file after successful compression
            csv_path = os.path.join(self.output_dir, f"session_{self.session_id}.csv")
            if os.path.exists(csv_path):
                os.remove(csv_path)
                print(f"[DataLogger] Cleaned up CSV file")
        except Exception as e:
            print(f"[DataLogger] Warning: Failed to create ZIP archive: {e}")

        self.is_recording = False

    def write_packet(self, packet: SensorPacket):
        """
        Write a sensor packet to CSV file.

        Args:
            packet: SensorPacket to write
        """
        if not self.is_recording:
            return

        # Convert CAN messages to JSON string for compact storage
        can_messages_json = json.dumps([
            {
                'id': f'0x{msg.id:03X}',
                'dlc': msg.dlc,
                'data': msg.to_hex_string(),
                'decoded': self._decode_can_message(msg)
            }
            for msg in packet.can_messages
        ]) if packet.can_messages else "[]"

        # Write unified row with all sensor data
        self.csv_writer.writerow({
            'timestamp_ms': packet.timestamp,
            # GPS data
            'gps_latitude': packet.latitude,
            'gps_longitude': packet.longitude,
            'gps_speed_knots': packet.speed_knots,
            'gps_speed_kmh': packet.speed_kmh,
            'gps_fix': packet.gps_fix,
            'gps_connected': packet.gps_connected,
            # Lidar data
            'lidar_distance_cm': packet.distance_cm,
            'lidar_distance_m': packet.distance_m,
            'lidar_strength': packet.lidar_strength,
            'lidar_connected': packet.lidar_connected,
            # CO2 data
            'co2_ppm': packet.co2_ppm,
            'co2_connected': packet.co2_connected,
            # CAN bus data (as JSON array)
            'can_messages': can_messages_json
        })

        # Flush file every 10 packets to avoid data loss
        self.packet_count += 1
        if self.packet_count % 10 == 0:
            self.csv_file.flush()

    def get_session_files(self) -> List[str]:
        """
        Get list of CSV/ZIP file paths for current session.

        Returns:
            List of absolute file paths
        """
        if not self.session_id:
            return []

        files = []

        # Check for ZIP file (preferred)
        zip_path = os.path.join(self.output_dir, f"session_{self.session_id}.zip")
        if os.path.exists(zip_path):
            files.append(zip_path)

        # Check for CSV file (if ZIP doesn't exist)
        csv_path = os.path.join(self.output_dir, f"session_{self.session_id}.csv")
        if os.path.exists(csv_path):
            files.append(csv_path)

        return files

    def export_session_zip(self, session_id: Optional[str] = None,
                          output_path: Optional[str] = None) -> str:
        """
        Export session CSV file to a ZIP archive.
        (This is now automatically called by stop_session, but kept for manual use)

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

        # Find CSV file for this session
        csv_filename = f"session_{session_id}.csv"
        csv_path = os.path.join(self.output_dir, csv_filename)

        if not os.path.exists(csv_path):
            raise FileNotFoundError(f"No CSV file found for session {session_id}")

        # Generate ZIP file path
        if output_path is None:
            output_path = os.path.join(self.output_dir, f"session_{session_id}.zip")

        # Create ZIP archive
        with ZipFile(output_path, 'w') as zipf:
            zipf.write(csv_path, os.path.basename(csv_path))

        print(f"[DataLogger] Exported session to: {output_path}")
        return output_path

    def _open_csv_file(self):
        """Open CSV file and write header"""
        csv_filename = f"session_{self.session_id}.csv"
        csv_path = os.path.join(self.output_dir, csv_filename)

        self.csv_file = open(csv_path, 'w', newline='')

        # Define all columns for unified CSV
        fieldnames = [
            'timestamp_ms',
            # GPS columns
            'gps_latitude', 'gps_longitude', 'gps_speed_knots', 'gps_speed_kmh',
            'gps_fix', 'gps_connected',
            # Lidar columns
            'lidar_distance_cm', 'lidar_distance_m', 'lidar_strength', 'lidar_connected',
            # CO2 columns
            'co2_ppm', 'co2_connected',
            # CAN bus (JSON array of messages)
            'can_messages'
        ]

        self.csv_writer = csv.DictWriter(self.csv_file, fieldnames=fieldnames)
        self.csv_writer.writeheader()

    def _close_csv_file(self):
        """Close CSV file"""
        if self.csv_file:
            self.csv_file.close()
            self.csv_file = None
            self.csv_writer = None

    def _create_session_zip(self) -> str:
        """
        Create ZIP archive for current session.
        Internal method called automatically by stop_session.

        Returns:
            Path to created ZIP file
        """
        csv_filename = f"session_{self.session_id}.csv"
        csv_path = os.path.join(self.output_dir, csv_filename)

        if not os.path.exists(csv_path):
            raise FileNotFoundError(f"CSV file not found: {csv_path}")

        zip_path = os.path.join(self.output_dir, f"session_{self.session_id}.zip")

        with ZipFile(zip_path, 'w') as zipf:
            zipf.write(csv_path, os.path.basename(csv_path))

        return zip_path

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
