#!/usr/bin/env python3
"""
IOVENADO DataLogger - Main Entry Point

Sensor data visualization for IOVENADO project.
Receives data from dual ESP32 sensor hubs via UART and displays
real-time information for GPS, Lidar, CO2, and CAN bus sensors.

Usage:
    python main.py              # GUI mode
    python main.py --headless   # Headless mode (no GUI)
    python main.py --headless --record --duration 60
"""

import sys
import argparse

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt

from views.main_window import MainWindow
from config.settings import APP_NAME, APP_VERSION


def parse_args():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(
        description="IOVENADO DataLogger - Sensor Data Visualization"
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


def run_gui():
    """Run in GUI mode"""
    app = QApplication(sys.argv)

    app.setApplicationName(APP_NAME)
    app.setApplicationVersion(APP_VERSION)
    app.setOrganizationName("IOVENADO")

    app.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )

    window = MainWindow()
    window.show()

    sys.exit(app.exec())


def run_headless(args):
    """Run in headless mode (no GUI)"""
    from core.headless_datalogger import HeadlessDataLogger

    print(f"[IOVENADO] Starting headless mode...")
    print(f"  Record: {args.record}")
    print(f"  Duration: {args.duration}s" if args.duration else "  Duration: unlimited")

    datalogger = HeadlessDataLogger()

    try:
        datalogger.start(record=args.record)
        datalogger.run(duration=args.duration)

    except KeyboardInterrupt:
        print("\n[IOVENADO] Interrupted by user")

    finally:
        datalogger.stop()
        print("[IOVENADO] Shutdown complete")


def main():
    """Main entry point"""
    args = parse_args()

    if args.record and not args.headless:
        print("Error: --record requires --headless")
        sys.exit(1)

    if args.duration and not args.headless:
        print("Error: --duration requires --headless")
        sys.exit(1)

    if args.headless:
        run_headless(args)
    else:
        run_gui()


if __name__ == "__main__":
    main()
