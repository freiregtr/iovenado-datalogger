#!/usr/bin/env python3
"""
IOVENADO - Test Serial Communication
Muestra datos parseados de ambos ESP32 con colores
"""

import serial
import threading
import struct
from datetime import datetime

# Colores ANSI
class Colors:
    RESET = '\033[0m'
    BOLD = '\033[1m'
    # ESP32 #1 - Azul
    BLUE = '\033[94m'
    # ESP32 #2 - Verde
    GREEN = '\033[92m'
    # Valores
    YELLOW = '\033[93m'
    RED = '\033[91m'
    CYAN = '\033[96m'
    MAGENTA = '\033[95m'

# Configuracion
PORTS = {
    '/dev/ttyAMA0': {
        'name': 'ESP32-1',
        'color': Colors.BLUE,
        'packet_size': 25,
        'type': 'gps_can'
    },
    '/dev/ttyAMA2': {
        'name': 'ESP32-2',
        'color': Colors.GREEN,
        'packet_size': 18,
        'type': 'lidar_co2'
    }
}

HEADER = b'\xAA\x55'

def parse_gps_can(data):
    """Parsea paquete de ESP32 #1 (GPS + CAN) - 25 bytes"""
    if len(data) < 25:
        return None

    try:
        # Header (2) + Length (2) + Timestamp (4) + Status (1) + GPS (8) + CAN (6) + Checksum (1) + Footer (2)
        timestamp = struct.unpack('<I', data[4:8])[0]
        status = data[8]

        # GPS data
        lat = struct.unpack('<i', data[9:13])[0] / 1e7
        lon = struct.unpack('<i', data[13:17])[0] / 1e7

        # CAN data
        rpm = struct.unpack('<H', data[17:19])[0]
        speed = struct.unpack('<H', data[19:21])[0]
        throttle = struct.unpack('<H', data[21:23])[0]

        gps_fix = bool(status & 0x01)
        gps_conn = bool(status & 0x02)
        can_active = bool(status & 0x04)

        return {
            'timestamp': timestamp,
            'gps_fix': gps_fix,
            'gps_conn': gps_conn,
            'can_active': can_active,
            'lat': lat,
            'lon': lon,
            'rpm': rpm,
            'speed': speed,
            'throttle': throttle
        }
    except Exception as e:
        return None

def parse_lidar_co2(data):
    """Parsea paquete de ESP32 #2 (Lidar + CO2) - 18 bytes"""
    if len(data) < 18:
        return None

    try:
        # Header (2) + Length (2) + Timestamp (4) + Status (1) + Lidar (4) + CO2 (2) + Checksum (1) + Footer (2)
        timestamp = struct.unpack('<I', data[4:8])[0]
        status = data[8]

        distance = struct.unpack('<H', data[9:11])[0]
        strength = struct.unpack('<H', data[11:13])[0]
        co2 = struct.unpack('<H', data[13:15])[0]

        lidar_conn = bool(status & 0x01)
        co2_conn = bool(status & 0x02)

        return {
            'timestamp': timestamp,
            'lidar_conn': lidar_conn,
            'co2_conn': co2_conn,
            'distance_cm': distance,
            'strength': strength,
            'co2_ppm': co2
        }
    except Exception as e:
        return None

def format_gps_can(parsed, color):
    """Formatea datos de GPS + CAN para mostrar"""
    c = Colors

    # Status icons
    gps_icon = f"{c.GREEN}●{c.RESET}" if parsed['gps_fix'] else f"{c.RED}○{c.RESET}"
    can_icon = f"{c.GREEN}●{c.RESET}" if parsed['can_active'] else f"{c.RED}○{c.RESET}"

    lines = [
        f"{color}{c.BOLD}━━━ ESP32-1 GPS+CAN ━━━{c.RESET}",
        f"  GPS: {gps_icon}  CAN: {can_icon}",
        f"  {c.CYAN}Lat:{c.RESET} {c.YELLOW}{parsed['lat']:.7f}{c.RESET}  {c.CYAN}Lon:{c.RESET} {c.YELLOW}{parsed['lon']:.7f}{c.RESET}",
        f"  {c.MAGENTA}RPM:{c.RESET} {parsed['rpm']}  {c.MAGENTA}Speed:{c.RESET} {parsed['speed']}  {c.MAGENTA}Throttle:{c.RESET} {parsed['throttle']}"
    ]
    return '\n'.join(lines)

def format_lidar_co2(parsed, color):
    """Formatea datos de Lidar + CO2 para mostrar"""
    c = Colors

    # Status icons
    lidar_icon = f"{c.GREEN}●{c.RESET}" if parsed['lidar_conn'] else f"{c.RED}○{c.RESET}"
    co2_icon = f"{c.GREEN}●{c.RESET}" if parsed['co2_conn'] else f"{c.RED}○{c.RESET}"

    # CO2 level color
    co2_val = parsed['co2_ppm']
    if co2_val < 600:
        co2_color = c.GREEN
    elif co2_val < 1000:
        co2_color = c.YELLOW
    else:
        co2_color = c.RED

    lines = [
        f"{color}{c.BOLD}━━━ ESP32-2 Lidar+CO2 ━━━{c.RESET}",
        f"  Lidar: {lidar_icon}  CO2: {co2_icon}",
        f"  {c.CYAN}Distance:{c.RESET} {c.YELLOW}{parsed['distance_cm']} cm{c.RESET}  {c.CYAN}Strength:{c.RESET} {parsed['strength']}",
        f"  {c.MAGENTA}CO2:{c.RESET} {co2_color}{co2_val} ppm{c.RESET}"
    ]
    return '\n'.join(lines)

def find_packet(ser, expected_size):
    """Busca y sincroniza con el header del paquete"""
    buffer = bytearray()

    while True:
        byte = ser.read(1)
        if not byte:
            return None

        buffer.append(byte[0])

        # Buscar header AA 55
        if len(buffer) >= 2:
            # Buscar header en el buffer
            try:
                idx = bytes(buffer).find(HEADER)
                if idx >= 0:
                    # Descartar bytes antes del header
                    buffer = buffer[idx:]

                    # Leer el resto del paquete
                    remaining = expected_size - len(buffer)
                    if remaining > 0:
                        more = ser.read(remaining)
                        if more:
                            buffer.extend(more)

                    if len(buffer) >= expected_size:
                        packet = bytes(buffer[:expected_size])
                        return packet
            except:
                pass

        # Evitar buffer infinito
        if len(buffer) > 100:
            buffer = buffer[-50:]

def read_serial(port, config):
    """Lee y parsea datos de un puerto serial"""
    name = config['name']
    color = config['color']
    packet_size = config['packet_size']
    packet_type = config['type']

    try:
        ser = serial.Serial(port, 9600, timeout=1)
        print(f"{color}[{name}] Conectado a {port}{Colors.RESET}")

        while True:
            packet = find_packet(ser, packet_size)

            if packet:
                if packet_type == 'gps_can':
                    parsed = parse_gps_can(packet)
                    if parsed:
                        print(format_gps_can(parsed, color))
                        print()
                else:
                    parsed = parse_lidar_co2(packet)
                    if parsed:
                        print(format_lidar_co2(parsed, color))
                        print()

    except Exception as e:
        print(f"{Colors.RED}[{name}] Error: {e}{Colors.RESET}")

def main():
    print(f"\n{Colors.BOLD}╔══════════════════════════════════════════════════╗{Colors.RESET}")
    print(f"{Colors.BOLD}║     IOVENADO - Serial Monitor Test               ║{Colors.RESET}")
    print(f"{Colors.BOLD}║     Ctrl+C para salir                            ║{Colors.RESET}")
    print(f"{Colors.BOLD}╚══════════════════════════════════════════════════╝{Colors.RESET}\n")

    threads = []
    for port, config in PORTS.items():
        t = threading.Thread(target=read_serial, args=(port, config), daemon=True)
        t.start()
        threads.append(t)

    try:
        for t in threads:
            t.join()
    except KeyboardInterrupt:
        print(f"\n{Colors.YELLOW}Saliendo...{Colors.RESET}")

if __name__ == '__main__':
    main()