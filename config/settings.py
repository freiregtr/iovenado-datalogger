# IOVENADO DataLogger - Configuration Settings

# Serial communication
SERIAL_PORT = '/dev/ttyAMA0'  # Raspberry Pi UART
SERIAL_BAUDRATE = 115200
SERIAL_TIMEOUT = 2.0

# Packet protocol
PACKET_HEADER = b'\xAA\x55'
PACKET_FOOTER = b'\x0D\x0A'

# Status byte bit masks (from ESP32 v2.0 protocol)
STATUS_GPS_FIX = 0x01      # bit 0 - GPS has fix
STATUS_GPS_CONN = 0x02     # bit 1 - GPS connected
STATUS_CAN_ACTIVE = 0x04   # bit 2 - CAN traffic detected
# Note: Lidar and CO2 now connect directly to Pi, not via ESP32

# View settings
GPS_TIME_WINDOW = 60       # seconds
LIDAR_TIME_WINDOW = 60     # seconds
CO2_TIME_WINDOW = 300      # seconds (5 minutes - CO2 changes slowly)
CAN_MAX_MESSAGES = 500     # max messages in terminal view

# Lidar range
LIDAR_MIN_CM = 0
LIDAR_MAX_CM = 1200

# CO2 reference levels (ppm)
CO2_LEVEL_EXCELLENT = 600
CO2_LEVEL_GOOD = 1000
CO2_LEVEL_MODERATE = 2000

# Colors
COLOR_CONNECTED = "#2ecc71"
COLOR_DISCONNECTED = "#e74c3c"
COLOR_WARNING = "#f39c12"
COLOR_GPS = "#3498db"
COLOR_LIDAR = "#2ecc71"
COLOR_CO2 = "#9b59b6"
COLOR_CAN = "#e67e22"

# Data logging
DATA_OUTPUT_DIR = './data'      # Directory for CSV output
CSV_FLUSH_INTERVAL = 10         # Flush CSV files every N packets

# Application
APP_NAME = "IOVENADO DataLogger"
APP_VERSION = "1.0-alpha"
WINDOW_MIN_WIDTH = 1200
WINDOW_MIN_HEIGHT = 800
