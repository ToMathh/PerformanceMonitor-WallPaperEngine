# StrangeCat Monitor - Minimal (Server)

A lightweight, headless version of StrangeCat Monitor that runs as a system tray icon and provides system performance data via HTTP. Perfect for remote monitoring or background operation without a GUI.

## Features

- **Headless Operation**: No window or graphics - runs entirely in the background
- **System Tray Icon**: Minimal tray icon with easy access to settings
- **HTTP Server**: Exposes real-time performance data as JSON on `http://127.0.0.1:5100/performance`
- **Configurable Refresh Rates**: 
  - **Low Mode** (default): 3-second refresh for CPU, RAM, GPU, VRAM, network
  - **Normal Mode**: 2-second refresh
- **Startup at Boot**: Optional automatic launch when Windows starts
- **Adaptive Disk Polling**: Slow drives are polled less frequently (5 minutes) to prevent system slowdowns
- **Single Instance**: Prevents multiple copies from running simultaneously

## Installation

### From Source

1. Ensure Python 3.8+ is installed
2. Install dependencies:
   ```bash
   pip install psutil pystray pillow
   ```
3. Run the application:
   ```bash
   python UltraLowPerf/main.py
   ```

### From Executable

Download and run the pre-built executable from the [Releases](../../releases) page.

## Usage

### System Tray Menu

Right-click the tray icon to access:
- **Start at boot**: Toggle automatic startup when Windows starts
- **Low (3s)**: Toggle low refresh mode (3s vs 2s)
- **Quitter**: Exit the application

### HTTP API

The server provides performance data at:
```
http://127.0.0.1:5100/performance
```

**Response Format:**
```json
{
  "timestamp": 1781137735.913701,
  "psutil": {
    "cpu": 65.1,
    "cpu_percore": [77.3, 63.7, 53.5, ...],
    "memory": 51.1,
    "memory_gb": "16.1 GB/31.6 GB",
    "gpu_usage": 45.2,
    "vram_usage": 32.8,
    "vram_gb": "3.2 GB/10.0 GB",
    "gpu_temp": 65,
    "upload_speed": 1.2,
    "download_speed": 5.4,
    "c_disk": "120.5 GB/500.0 GB",
    "d_disk": "200.3 GB/1000.0 GB"
  },
  "hwinfo": []
}
```

### Configuration

Settings are stored in:
```
%APPDATA%\StrangeCatV6\config.json
```

**Key Settings:**
- `refresh_mode`: `"low"` (3s), `"normal"` (2s), or `"realtime"` (1s)
- `disk_interval`: Disk update interval in seconds (default: 60)
- `http_port`: HTTP server port (default: 5100)

## Performance

The minimal version is optimized for low resource usage:
- **CPU**: < 1% on idle
- **RAM**: ~30-50 MB
- **Network**: Minimal HTTP overhead
- **Disk**: Adaptive polling prevents slowdowns on sleeping drives

## Building the Executable

```bash
cd UltraLowPerf
build.bat
```

This creates a single executable in `dist/` using PyInstaller.

## Compatibility

- **OS**: Windows 10/11
- **Python**: 3.8+
- **Dependencies**: psutil, pystray, pillow

## License

See the main project license file.

## Support

For issues or feature requests, please visit the [main repository](../../).
