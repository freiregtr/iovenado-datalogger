# IOVENADO DataLogger - Configuration Settings

# Serial communication - ESP32 #1 (GPS + CAN)
ESP32_1_PORT = '/dev/ttyAMA0'  # GPIO 14/15
ESP32_1_BAUDRATE = 9600

# Serial communication - ESP32 #2 (Lidar + CO2)
ESP32_2_PORT = '/dev/ttyAMA2'  # GPIO 4/5
ESP32_2_BAUDRATE = 9600

SERIAL_TIMEOUT = 2.0

# Packet protocol
PACKET_HEADER = b'\xAA\x55'
PACKET_FOOTER = b'\x0D\x0A'

# Status byte bit masks - ESP32 #1 (GPS + CAN)
STATUS_GPS_FIX = 0x01      # bit 0 - GPS has fix
STATUS_GPS_CONN = 0x02     # bit 1 - GPS connected
STATUS_CAN_ACTIVE = 0x04   # bit 2 - CAN traffic detected

# Status byte bit masks - ESP32 #2 (Lidar + CO2)
STATUS_LIDAR_CONN = 0x01   # bit 0 - Lidar connected
STATUS_CO2_CONN = 0x02     # bit 1 - CO2 sensor connected

# Synchronization settings
SYNC_WINDOW_MS = 500       # Window to consider packets synchronized
BUFFER_TIMEOUT_MS = 2000   # Timeout to consider sensor disconnected

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
APP_VERSION = "2.0-alpha"
WINDOW_MIN_WIDTH = 1200
WINDOW_MIN_HEIGHT = 800
