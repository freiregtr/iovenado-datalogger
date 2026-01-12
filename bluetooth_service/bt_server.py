#!/usr/bin/env python3
"""
IOVENADO Bluetooth Datalogger Service

Bluetooth Classic server that allows remote control of the datalogger
via Android app or any Bluetooth terminal.

Commands:
  START_DATALOGGER  - Start recording
  STOP_DATALOGGER   - Stop recording
  GET_STATUS        - Get current status (RUNNING/STOPPED)
  LIST_CSV          - List available CSV files (JSON)
  GET_CSV <name>    - Download CSV file (as ZIP)
"""

import os
import sys
import json
import subprocess
import time
import socket
import signal
from datetime import datetime
from zipfile import ZipFile
from pathlib import Path

# Add parent directory to path to import datalogger modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    import bluetooth
except ImportError:
    print("ERROR: PyBluez not installed")
    print("Install with: pip install pybluez")
    print("On Raspberry Pi, also run: sudo apt-get install bluetooth libbluetooth-dev")
    sys.exit(1)

from config.settings import DATA_OUTPUT_DIR


class BluetoothDataloggerServer:
    """
    Bluetooth server for remote datalogger control.
    Uses Bluetooth Classic (RFCOMM/SPP).
    """

    # Bluetooth UUID for Serial Port Profile
    SPP_UUID = "00001101-0000-1000-8000-00805F9B34FB"
    SERVICE_NAME = "iOvenadoDatalogger"

    def __init__(self, data_dir: str = None):
        """
        Initialize Bluetooth server.

        Args:
            data_dir: Directory where CSV files are stored
        """
        self.data_dir = data_dir or DATA_OUTPUT_DIR
        self.server_sock = None
        self.client_sock = None
        self.client_info = None
        self.datalogger_process = None
        self.running = False

        # Ensure data directory exists
        os.makedirs(self.data_dir, exist_ok=True)

        print(f"[BTServer] Data directory: {self.data_dir}")

    def start_server(self):
        """Start Bluetooth server and listen for connections"""
        print("[BTServer] Initializing Bluetooth server...")

        try:
            # Create Bluetooth socket
            self.server_sock = bluetooth.BluetoothSocket(bluetooth.RFCOMM)

            # Set socket options for better compatibility
            self.server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

            # Set socket timeout to allow checking self.running periodically
            self.server_sock.settimeout(1.0)

            # Bind to channel 2 specifically (channel 1 is occupied by BlueZ Serial Port)
            try:
                self.server_sock.bind(("", 2))
                port = 2
                print(f"[BTServer] Bound to channel 2 (fixed)")
            except:
                # If channel 2 is not available, use any available port
                self.server_sock.bind(("", bluetooth.PORT_ANY))
                port = self.server_sock.getsockname()[1]
                print(f"[BTServer] Channel 2 not available, using channel {port}")

            # Listen for incoming connections (backlog of 5)
            self.server_sock.listen(5)

            # Advertise service
            bluetooth.advertise_service(
                self.server_sock,
                self.SERVICE_NAME,
                service_id=self.SPP_UUID,
                service_classes=[self.SPP_UUID, bluetooth.SERIAL_PORT_CLASS],
                profiles=[bluetooth.SERIAL_PORT_PROFILE]
            )

            print(f"[BTServer] Server started on RFCOMM channel {port}")
            print(f"[BTServer] Waiting for connections...")
            print(f"[BTServer] Service Name: {self.SERVICE_NAME}")
            print(f"[BTServer] UUID: {self.SPP_UUID}")
            print(f"[BTServer] Socket timeout: 1.0s (allows graceful shutdown)")

            self.running = True

            # Main server loop
            while self.running:
                try:
                    # Accept incoming connection (with timeout)
                    self.client_sock, self.client_info = self.server_sock.accept()
                    print(f"[BTServer] *** CLIENT CONNECTED *** : {self.client_info}")

                    # Handle client commands
                    self._handle_client()

                except socket.timeout:
                    # Timeout is normal - allows checking self.running
                    continue

                except bluetooth.BluetoothError as e:
                    if self.running:
                        print(f"[BTServer] Bluetooth error: {e}")
                        import traceback
                        traceback.print_exc()
                        time.sleep(1)

                except Exception as e:
                    if self.running:
                        print(f"[BTServer] Error: {e}")
                        import traceback
                        traceback.print_exc()
                        time.sleep(1)

        except KeyboardInterrupt:
            print("\n[BTServer] Interrupted by user")

        finally:
            self.stop_server()

    def stop_server(self):
        """Stop Bluetooth server"""
        print("[BTServer] Stopping server...")

        self.running = False

        # Stop datalogger if running
        if self.datalogger_process:
            self._stop_datalogger()

        # Close client connection
        if self.client_sock:
            try:
                self.client_sock.close()
            except:
                pass

        # Close server socket
        if self.server_sock:
            try:
                self.server_sock.close()
            except:
                pass

        print("[BTServer] Server stopped")

    def _handle_client(self):
        """Handle commands from connected client"""
        try:
            while True:
                # Receive command (max 1024 bytes)
                data = self.client_sock.recv(1024)

                if not data:
                    break

                # Decode command
                command = data.decode('utf-8').strip()
                print(f"[BTServer] Received command: {command}")

                # Process command
                response = self._process_command(command)

                # Send response
                if response:
                    self.client_sock.send((response + "\n").encode('utf-8'))

        except bluetooth.BluetoothError as e:
            print(f"[BTServer] Client disconnected: {e}")

        except Exception as e:
            print(f"[BTServer] Error handling client: {e}")

        finally:
            # Close client connection
            if self.client_sock:
                try:
                    self.client_sock.close()
                except:
                    pass
            self.client_sock = None
            print(f"[BTServer] Client disconnected: {self.client_info}")

    def _process_command(self, command: str) -> str:
        """
        Process received command and return response.

        Args:
            command: Command string

        Returns:
            Response string
        """
        command = command.upper().strip()

        if command == "START_DATALOGGER":
            return self._start_datalogger()

        elif command == "STOP_DATALOGGER":
            return self._stop_datalogger()

        elif command == "GET_STATUS":
            return self._get_status()

        elif command == "LIST_CSV":
            return self._list_csv_files()

        elif command.startswith("GET_CSV"):
            # Extract filename
            parts = command.split(" ", 1)
            if len(parts) < 2:
                return "ERROR: Missing filename"
            filename = parts[1].strip()
            return self._send_csv_file(filename)

        else:
            return f"ERROR: Unknown command '{command}'"

    def _start_datalogger(self) -> str:
        """Start datalogger process"""
        # Check if already running
        if self.datalogger_process and self.datalogger_process.poll() is None:
            return "ERROR: Datalogger already running"

        try:
            # Get path to main.py (parent directory)
            script_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            main_py = os.path.join(script_dir, "main.py")

            # Start datalogger in headless mode with recording
            self.datalogger_process = subprocess.Popen(
                [sys.executable, main_py, "--headless", "--record"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                cwd=script_dir
            )

            print(f"[BTServer] Started datalogger (PID: {self.datalogger_process.pid})")
            return "OK"

        except Exception as e:
            print(f"[BTServer] Failed to start datalogger: {e}")
            return f"ERROR: {str(e)}"

    def _stop_datalogger(self) -> str:
        """Stop datalogger process"""
        if not self.datalogger_process:
            return "ERROR: Datalogger not running"

        try:
            # Send SIGTERM
            self.datalogger_process.terminate()

            # Wait up to 5 seconds
            try:
                self.datalogger_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                # Force kill if doesn't terminate
                self.datalogger_process.kill()
                self.datalogger_process.wait()

            print(f"[BTServer] Stopped datalogger (PID: {self.datalogger_process.pid})")
            self.datalogger_process = None
            return "OK"

        except Exception as e:
            print(f"[BTServer] Failed to stop datalogger: {e}")
            return f"ERROR: {str(e)}"

    def _get_status(self) -> str:
        """Get current datalogger status"""
        if self.datalogger_process and self.datalogger_process.poll() is None:
            return "RUNNING"
        else:
            return "STOPPED"

    def _list_csv_files(self) -> str:
        """List available CSV files (ZIP archives)"""
        try:
            files = []

            # Look for ZIP files in data directory
            data_path = Path(self.data_dir)
            for filepath in data_path.glob("*.zip"):
                stat = filepath.stat()
                files.append({
                    'filename': filepath.name,
                    'size_bytes': stat.st_size,
                    'date': datetime.fromtimestamp(stat.st_mtime).isoformat()
                })

            # Sort by date (newest first)
            files.sort(key=lambda x: x['date'], reverse=True)

            # Return JSON
            return json.dumps(files)

        except Exception as e:
            print(f"[BTServer] Failed to list CSV files: {e}")
            return json.dumps({'error': str(e)})

    def _send_csv_file(self, filename: str) -> str:
        """
        Send CSV file (as ZIP) to client.

        Args:
            filename: Filename or session ID

        Returns:
            Status message (actual file is sent separately)
        """
        try:
            # Build file path
            # If filename doesn't end with .zip, assume it's a session ID
            if not filename.endswith('.zip'):
                filename = f"session_{filename}.zip"

            filepath = os.path.join(self.data_dir, filename)

            # Check if file exists
            if not os.path.exists(filepath):
                return f"ERROR: File not found: {filename}"

            # Get file size
            file_size = os.path.getsize(filepath)

            # Send size header
            size_msg = f"SIZE:{file_size}\n"
            self.client_sock.send(size_msg.encode('utf-8'))

            # Wait for ACK
            ack = self.client_sock.recv(4)
            if ack.decode('utf-8').strip() != "ACK":
                return "ERROR: Client did not acknowledge"

            # Send file in chunks
            with open(filepath, 'rb') as f:
                bytes_sent = 0
                while True:
                    chunk = f.read(4096)
                    if not chunk:
                        break
                    self.client_sock.send(chunk)
                    bytes_sent += len(chunk)

            print(f"[BTServer] Sent {filename} ({bytes_sent} bytes)")
            return "OK"

        except Exception as e:
            print(f"[BTServer] Failed to send file: {e}")
            return f"ERROR: {str(e)}"


def main():
    """Main entry point for Bluetooth service"""
    print("="*60)
    print("IOVENADO Bluetooth Datalogger Service")
    print("="*60)
    print()

    # Check if running on Linux (Raspberry Pi)
    if sys.platform != "linux":
        print("WARNING: This service is designed for Linux (Raspberry Pi)")
        print("Bluetooth functionality may not work on other platforms")
        print()

    # Create and start server
    server = BluetoothDataloggerServer()

    # Set up signal handlers for graceful shutdown
    def signal_handler(signum, frame):
        print(f"\n[BTServer] Received signal {signum}, shutting down gracefully...")
        server.running = False

    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)

    try:
        server.start_server()
    except KeyboardInterrupt:
        print("\nShutting down...")
    finally:
        server.stop_server()


if __name__ == "__main__":
    main()
