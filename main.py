#!/usr/bin/env python3
"""
IOVENADO DataLogger - Main Entry Point

Sensor data visualization for IOVENADO project.
Receives data from ESP32 sensor hub via UART and displays
real-time information for GPS, Lidar, CO2, and CAN bus sensors.

Usage:
    python main.py          # Normal mode (connects to /dev/ttyAMA0)
    python main.py --mock   # Mock mode (simulated data for testing)
"""

import sys
import argparse

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt

from views.main_window import MainWindow


def parse_args():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(
        description="IOVENADO DataLogger - Sensor Data Visualization"
    )
    parser.add_argument(
        '--mock',
        action='store_true',
        help='Run in mock mode with simulated data'
    )
    parser.add_argument(
        '--port',
        type=str,
        default=None,
        help='Serial port to use (default: /dev/ttyAMA0)'
    )
    parser.add_argument(
        '--headless',
        action='store_true',
        help='Run in headless mode (no GUI)'
    )
    parser.add_argument(
        '--record',
        action='store_true',
        help='Start recording immediately (requires --headless)'
    )
    parser.add_argument(
        '--duration',
        type=int,
        default=0,
        help='Recording duration in seconds (0 = unlimited, requires --headless)'
    )
    return parser.parse_args()


def run_gui(args):
    """Run in GUI mode"""
    # Create application
    app = QApplication(sys.argv)

    # Set application info
    app.setApplicationName("IOVENADO DataLogger")
    app.setApplicationVersion("1.0-alpha")
    app.setOrganizationName("IOVENADO")

    # Enable high DPI scaling
    app.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )

    # Create and show main window
    window = MainWindow(use_mock=args.mock)
    window.show()

    # Run application
    sys.exit(app.exec())


def run_headless(args):
    """Run in headless mode (no GUI)"""
    from core.headless_datalogger import HeadlessDataLogger

    print(f"[IOVENADO] Starting headless mode...")
    print(f"  Mock: {args.mock}")
    print(f"  Record: {args.record}")
    print(f"  Duration: {args.duration}s" if args.duration else "  Duration: unlimited")

    # Create headless datalogger
    datalogger = HeadlessDataLogger(use_mock=args.mock, port=args.port)

    try:
        # Start datalogger
        datalogger.start(record=args.record)

        # Run for specified duration or until Ctrl+C
        datalogger.run(duration=args.duration)

    except KeyboardInterrupt:
        print("\n[IOVENADO] Interrupted by user")

    finally:
        # Clean shutdown
        datalogger.stop()
        print("[IOVENADO] Shutdown complete")


def main():
    """Main entry point"""
    args = parse_args()

    # Update settings if port specified
    if args.port:
        from config import settings
        settings.SERIAL_PORT = args.port

    # Validate arguments
    if args.record and not args.headless:
        print("Error: --record requires --headless")
        sys.exit(1)

    if args.duration and not args.headless:
        print("Error: --duration requires --headless")
        sys.exit(1)

    # Run in appropriate mode
    if args.headless:
        run_headless(args)
    else:
        run_gui(args)


if __name__ == "__main__":
    main()
