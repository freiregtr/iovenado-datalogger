# IOVENADO DataLogger

Sistema de adquisición de datos para vehículo con sensores GPS, Lidar, CO2 y CAN bus.

## Características

- **Visualización en tiempo real** con interfaz Qt
- **Grabación a CSV** de todos los sensores
- **Exportación a ZIP** para transferencia
- **Modo headless** para operación sin interfaz gráfica
- **Control remoto Bluetooth** desde app Android

---

## Modos de Operación

### 1. Modo GUI (Interfaz Gráfica)

Visualización en tiempo real con grabación manual.

```bash
# Con hardware real
python main.py

# Con datos simulados (testing)
python main.py --mock
```

**Controles:**
- **Start Recording** - Inicia grabación a CSV
- **Stop Recording** - Detiene y ofrece exportar a ZIP
- **Reset Views** - Limpia gráficos
- **Reconnect** - Reconecta puerto serial

### 2. Modo Headless (Sin GUI)

Para operación en background o control remoto.

```bash
# Lectura sin grabación
python main.py --headless

# Lectura con grabación automática
python main.py --headless --record

# Grabar por 60 segundos y terminar
python main.py --headless --record --duration 60

# Con datos simulados
python main.py --headless --mock --record --duration 30
```

### 3. Servicio Bluetooth

Control remoto desde app Android.

```bash
# Ejecutar servidor Bluetooth manualmente
python bluetooth_service/bt_server.py

# O instalar como servicio systemd (autoarranque)
sudo bash bluetooth_service/install_service.sh
```

**Comandos Bluetooth:**
- `START_DATALOGGER` - Inicia grabación
- `STOP_DATALOGGER` - Detiene grabación
- `GET_STATUS` - Obtiene estado (RUNNING/STOPPED)
- `LIST_CSV` - Lista archivos disponibles (JSON)
- `GET_CSV <session_id>` - Descarga archivo ZIP

---

## Instalación

### En PC (Development/Testing)

```bash
cd datalogger

# Crear virtual environment
python -m venv venv

# Activar venv (Windows)
venv\Scripts\activate

# Activar venv (Linux/Mac)
source venv/bin/activate

# Instalar dependencias
pip install -r requirements.txt

# Probar con datos simulados
python main.py --mock
```

### En Raspberry Pi 5

```bash
# 1. Instalar dependencias del sistema
sudo apt-get update
sudo apt-get install -y bluetooth libbluetooth-dev python3-pip python3-venv git

# 2. Clonar repositorio
cd /home/pi
git clone https://github.com/freiregtr/iovenado-datalogger.git
cd iovenado-datalogger

# 3. Crear virtual environment
python3 -m venv venv

# 4. Activar venv
source venv/bin/activate

# 5. Instalar PyBluez desde GitHub (evita problemas con setuptools)
pip install git+https://github.com/pybluez/pybluez.git#egg=pybluez

# 6. Verificar que bluetooth está instalado correctamente
python -c "import bluetooth; print('✓ Bluetooth module OK')"

# 7. Instalar resto de dependencias Python
pip install -r requirements.txt

# 8. Probar en modo GUI (requiere X server)
python main.py --mock

# 9. Probar en modo headless (sin GUI, genera CSVs)
python main.py --headless --mock --record --duration 30

# 10. Verificar que se generaron archivos CSV
ls -lh data/

# 11. Instalar servicio Bluetooth para autoarranque
cd bluetooth_service
sudo bash install_service.sh

# 12. Verificar servicio
sudo systemctl status iovenado-bt
sudo journalctl -u iovenado-bt -f
```

**Nota importante sobre PyBluez:**
- PyBluez del PyPI tiene problemas con setuptools moderno (error use_2to3)
- Se instala directamente desde el repositorio de GitHub que tiene la versión actualizada
- El comando `pip install git+https://github.com/pybluez/pybluez.git` instala la última versión compatible

---

## Estructura de Archivos

### Archivos CSV Generados

Cada sesión de grabación crea 4 archivos CSV:

```
data/
├── gps_2026-01-12_14-30-25.csv
├── lidar_2026-01-12_14-30-25.csv
├── co2_2026-01-12_14-30-25.csv
├── canbus_2026-01-12_14-30-25.csv
└── session_2026-01-12_14-30-25.zip  (exportado)
```

**Formato GPS:**
```csv
timestamp_ms,latitude,longitude,speed_knots,speed_kmh,gps_fix,gps_connected
1234567890,10.308617,-84.087334,22.5,41.7,True,True
```

**Formato Lidar:**
```csv
timestamp_ms,distance_cm,distance_m,lidar_strength,lidar_connected
1234567890,350,3.5,800,True
```

**Formato CO2:**
```csv
timestamp_ms,co2_ppm,co2_connected
1234567890,650,True
```

**Formato CAN Bus:**
```csv
timestamp_ms,can_id,dlc,data_hex,decoded
1234567890,0x7E8,8,41 0C 1A F8 00 00 00 00,RPM: 1726
1234567890,0x7E8,8,41 0D 32 00 00 00 00 00,Speed: 50 km/h
```

---

## Configuración

Editar [config/settings.py](config/settings.py):

```python
# Puerto serial (Raspberry Pi)
SERIAL_PORT = '/dev/ttyAMA0'
SERIAL_BAUDRATE = 115200

# Directorio de salida
DATA_OUTPUT_DIR = './data'
```

---

## Testing

### Test 1: Modo GUI con Mock

```bash
python main.py --mock
# 1. Observar datos simulados
# 2. Clic en "Start Recording"
# 3. Esperar 10 segundos
# 4. Clic en "Stop Recording"
# 5. Exportar a ZIP
# 6. Verificar archivos en ./data
```

### Test 2: Modo Headless

```bash
python main.py --headless --mock --record --duration 10
# Verificar archivos CSV en ./data
```

### Test 3: Servicio Bluetooth

```bash
# En Raspberry Pi
python bluetooth_service/bt_server.py

# Desde Android con "Bluetooth Terminal" app
1. Conectar a "iOvenadoDatalogger"
2. Enviar: START_DATALOGGER
3. Esperar 10 segundos
4. Enviar: STOP_DATALOGGER
5. Enviar: LIST_CSV
6. Enviar: GET_CSV <session_id>
```

---

## Solución de Problemas

### Error: "No such file or directory: '/dev/ttyAMA0'"

**Solución:** Usar modo mock para testing o especificar puerto correcto:

```bash
python main.py --port /dev/ttyUSB0
```

### Error: "PyBluez not installed"

**Solución en Raspberry Pi:**

```bash
sudo apt-get install bluetooth libbluetooth-dev
pip3 install pybluez
```

### El servicio Bluetooth no arranca

**Verificar logs:**

```bash
sudo journalctl -u iovenado-bt -f
```

**Reiniciar servicio:**

```bash
sudo systemctl restart iovenado-bt
```

### Los archivos CSV están vacíos

**Causa:** El datalogger no recibió datos del ESP32.

**Solución:**
1. Verificar conexión serial (`ls /dev/tty*`)
2. Verificar baudrate (115200)
3. Probar con `--mock` para verificar que el logging funciona

---

## Arquitectura

```
┌─────────────────────────────────────┐
│     ESP32 (Sensor Hub)              │
│  - GPS, Lidar, CO2, CAN             │
└──────────────┬──────────────────────┘
               │ UART (115200 baud)
               ▼
┌─────────────────────────────────────┐
│   Raspberry Pi 5                    │
│                                     │
│  ┌──────────────────────────────┐  │
│  │  SerialPacketReader          │  │
│  │  (Lee paquetes binarios)     │  │
│  └──────────┬───────────────────┘  │
│             │                       │
│  ┌──────────▼───────────────────┐  │
│  │  Modo GUI o Headless         │  │
│  └──────────┬───────────────────┘  │
│             │                       │
│  ┌──────────▼───────────────────┐  │
│  │  CSVDataLogger               │  │
│  │  (Guarda a archivos)         │  │
│  └──────────────────────────────┘  │
│                                     │
│  ┌──────────────────────────────┐  │
│  │  Bluetooth Service (Opt)     │  │
│  │  (Control remoto)            │  │
│  └──────────────────────────────┘  │
└─────────────────────────────────────┘
               ▲
               │ Bluetooth Classic
               │
┌──────────────┴──────────────────────┐
│   App Android                       │
│  - START/STOP datalogger            │
│  - Descargar CSVs                   │
└─────────────────────────────────────┘
```

---

## Desarrollo

### Estructura del Código

```
datalogger/
├── main.py                      # Entry point
├── requirements.txt             # Dependencias
├── README.md                    # Este archivo
│
├── config/
│   └── settings.py              # Configuración
│
├── core/
│   ├── packet.py                # SensorPacket, CANMessage
│   ├── serial_reader.py         # Lectura UART
│   ├── data_logger.py           # Guardado CSV
│   └── headless_datalogger.py   # Modo sin GUI
│
├── views/
│   ├── main_window.py           # Ventana principal
│   ├── dashboard_view.py        # Grid 2x2 resumen
│   ├── gps_view.py              # Display GPS
│   ├── lidar_view.py            # Gráfico Lidar
│   ├── co2_view.py              # Gráfico CO2
│   └── can_view.py              # Terminal CAN
│
├── bluetooth_service/
│   ├── bt_server.py             # Servidor Bluetooth
│   ├── iovenado-bt.service      # systemd service
│   └── install_service.sh       # Script instalación
│
└── data/                        # Archivos CSV (generados)
```

### Agregar Nuevo Sensor

1. Modificar `core/packet.py` - Agregar campos a `SensorPacket`
2. Modificar `core/serial_reader.py` - Decodificar nuevos campos
3. Modificar `core/data_logger.py` - Crear nuevo CSV
4. Crear nueva vista en `views/`
5. Agregar vista a `MainWindow`

---

## Próximos Pasos

- [ ] Desarrollar app Android
- [ ] Testing con hardware real
- [ ] Optimización de batería en modo headless
- [ ] Compresión 7z (mejor ratio)
- [ ] Web interface (opcional)

---

## Licencia

MIT License

---

## Contacto

Proyecto: IOVENADO
Versión: 1.0-alpha
Fecha: 2026-01-12
