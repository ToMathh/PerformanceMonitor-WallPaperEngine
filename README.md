# 🐱 StrangeCat Monitor - Minimal (Server) v6.0

A lightweight, headless version of StrangeCat Monitor that runs as a system tray icon and provides system performance data via HTTP. Perfect for Wallpaper Engine integration, or background operation without a GUI.

* ✅ No window or graphics
* ✅ Ultra-lightweight & portable
* ✅ Works locally on `127.0.0.1:5100/performance`
* ✅ Compatible with Wallpaper Engine
* ✅ System tray icon with settings
* ✅ Configurable refresh rates (Low 3s / Realtime 1s)
* ✅ Startup at boot support settings
* ✅ Adaptive disk polling (slow drives = 5min)
* ✅ Single instance enforcement

---

# Quick Start

## 1. Download & Launch

Download the latest release and launch:

```txt
StrangeCat.Monitor.Minimal.RECOMMANDED.exe
```

No Python or additional setup required.

---

## 2. Verify the Server is Running

When the app is running, you'll see a tray icon in the system notification area.

Right-click the icon to access settings.

---

## 3. Configure Wallpaper Engine

Open Wallpaper Engine and ensure your wallpaper uses:

```txt
Port: 5100
```

StrangeCat Monitor Minimal serves live data at:

```txt
http://127.0.0.1:5100/performance
```

---

## 4. Done 🎉

Compatible wallpapers will now display your live CPU, RAM, GPU, temperatures, and network activity automatically.

---

# Installation

## Standalone EXE

1. Download the latest release
2. Move it anywhere you want
3. Double-click:

```txt
StrangeCat.Monitor.Minimal.RECOMMANDED.exe
```

No installation required.

---

## Auto-start with Windows

Right-click the tray icon and enable:

* ✅ **Start at boot**

StrangeCat Monitor Minimal will now launch automatically with Windows.

> Recommended for Wallpaper Engine users.

---

# Wallpaper Engine Setup

## How it Works

StrangeCat Monitor Minimal runs a tiny local server:

```txt
http://127.0.0.1:5100/performance
```

Wallpaper Engine wallpapers can read this endpoint and animate your system stats live.

```txt
StrangeCat Monitor Minimal
        │
        ├──► System tray icon
        │
        └──► Local HTTP API (:5100)
                     │
                     └──► Wallpaper Engine wallpaper
```

---

## Test the Connection

Open this address in your browser:

```txt
http://127.0.0.1:5100/performance
```

If you see JSON data, everything is working correctly.

---

## Port Mismatch (Important)

Some wallpapers are designed for other monitoring apps using port `5000`.

StrangeCat Monitor Minimal uses:

```txt
5100
```

If your wallpaper cannot connect:

* either change the wallpaper port to `5100`
* or change the port in:

```txt
%APPDATA%\StrangeCatV6\config.json
```

Edit `http_port` to your desired port.

---

# System Tray Menu

Right-click the tray icon to access:

| Option          | Description                      |
| --------------- | -------------------------------- |
| ✅ Start at boot| Toggle automatic startup         |
| ✅ Low (3s)     | Toggle low refresh mode (3s vs 2s)|
| ❌ Quitter       | Exit the application              |

---

# Refresh Modes

Choose your refresh mode via the tray menu:

| Mode      | CPU/RAM/GPU/VRAM/Network | Disks   |
| --------- | ------------------------ | ------- |
| Realtime  | 1 second (default)       | 60s     |
| Low       | 3 seconds                 | 60s     |

**Slow drives** automatically back off to 5-minute polling to prevent system slowdowns.

---

# Configuration

Settings are stored in:

```txt
%APPDATA%\StrangeCatV6\config.json
```

**Key Settings:**

```json
{
  "refresh_mode": "realtime",
  "disk_interval": 60.0,
  "http_port": 5100
}
```

| Setting        | Values                          | Default |
| -------------- | ------------------------------- | ------- |
| refresh_mode   | `"realtime"`, `"low"`          | `"realtime"` |
| disk_interval  | Seconds (number)                | `60.0`  |
| http_port      | Port number                     | `5100`  |

---

# HTTP API

## Endpoint

```http
GET http://127.0.0.1:5100/performance
```

---

## Example Response

```json
{
  "timestamp": 1781137735.913701,
  "psutil": {
    "cpu": 65.1,
    "cpu_percore": [77.3, 63.7, 53.5, 37.6, 60.2, 61.0, 84.3, 81.1, 51.5, 58.3, 77.5, 77.5, 69.2, 76.7, 53.5, 56.6],
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

---

## Available Metrics

| Metric           | Description              |
| ---------------- | ------------------------ |
| cpu              | Processor usage (%)      |
| cpu_percore      | Per-core usage (%)       |
| memory           | Memory usage (%)         |
| memory_gb        | Memory usage (GB)        |
| gpu_usage        | GPU load (%)             |
| gpu_temp         | GPU temperature          |
| vram_usage       | GPU memory usage (%)     |
| vram_gb          | GPU memory usage (GB)    |
| upload_speed     | Upload speed (MB/s)      |
| download_speed   | Download speed (MB/s)    |
| c_disk, d_disk…  | Drive usage (auto-detected) |

---

# Performance

The minimal version is optimized for ultra-low resource usage:

| Resource | Usage (Idle) |
| -------- | ------------ |
| **CPU**  | < 1%         |
| **RAM**  | ~30-50 MB    |
| **Disk** | Adaptive polling prevents slowdowns on sleeping drives |
| **Network** | Minimal HTTP overhead |

---

# Disk Monitoring

StrangeCat Monitor Minimal automatically detects all connected drives (C:, D:, E:, F:, G:, etc.).

## Adaptive Polling

- **Fast drives**: Poll every 60 seconds (configurable)
- **Slow drives** (spinning HDDs, sleeping drives): Automatically back off to 5 minutes

This prevents UI freezes and system slowdowns when accessing slow disks.

---

# CPU Temperature

Windows usually requires an external helper application for accurate CPU temperatures.

StrangeCat Monitor Minimal automatically tries multiple methods and uses the first available source.

## Recommended: LibreHardwareMonitor

For the best compatibility:

1. Download LibreHardwareMonitor
2. Run it as Administrator
3. Leave it running in the background
4. Restart StrangeCat Monitor Minimal

---

## Temperature Source Priority

| Priority | Source               |
| -------- | -------------------- |
| 1        | psutil built-in      |
| 2        | LibreHardwareMonitor |
| 3        | OpenHardwareMonitor  |
| 4        | CoreTemp             |

---

# Single Instance

Only one instance of StrangeCat Monitor Minimal can run at a time. If you try to launch a second instance, it will exit silently.

This prevents duplicate entries in Task Manager and port conflicts.

---

# Troubleshooting

## Wallpaper Shows "--" or No Data

Checklist:

* Is StrangeCat Monitor Minimal running? (Check system tray)
* Is the tray icon visible?
* Is Wallpaper Engine using port `5100`?
* Does this URL work?

```txt
http://127.0.0.1:5100/performance
```

---

## CPU Temperature Shows N/A

Install and run:

```txt
LibreHardwareMonitor
```

as Administrator.

---

## GPU Shows 0% or Missing Data

GPU monitoring currently supports:

* ✅ NVIDIA GPUs
* ❌ AMD GPUs
* ❌ Intel GPUs

StrangeCat Monitor Minimal uses:

```txt
nvidia-smi
```

for GPU metrics.

---

## Port 5100 Already in Use

Edit the config file:

```txt
%APPDATA%\StrangeCatV6\config.json
```

Change:

```json
{
  "http_port": 5101
}
```

Then restart the app.

---

## Reset All Settings

Delete:

```txt
%APPDATA%\StrangeCatV6\config.json
```

The app will recreate default settings automatically.

---

# For Developers

## Run from Source

Requires:

* Python 3.8+

Install dependencies:

```bash
pip install psutil pystray pillow
```

Launch:

```bash
python UltraLowPerf/main.py
```

---

# Build From Source

```bash
pip install pyinstaller psutil pystray pillow

cd UltraLowPerf
build.bat
```

Output:

```txt
dist/StrangeCat.Monitor.Minimal.RECOMMANDED.exe
```

---

# Wallpaper Integration Example

```javascript
const PORT = 5100;

async function fetchStats() {
  try {
    const res = await fetch(
      `http://127.0.0.1:${PORT}/performance` 
    );

    const data = await res.json();
    const ps = data.psutil ?? {};

    console.log(ps.cpu);
    console.log(ps.memory);
    console.log(ps.gpu_usage);
    console.log(ps.cpu_temp);
    console.log(ps.c_disk);

  } catch {
    // Monitor offline
  }
}

setInterval(fetchStats, 2000);
fetchStats();
```

---

# Config File

```txt
%APPDATA%\StrangeCatV6\config.json
```

All application settings are stored here.

Deleting the file resets everything to defaults.

---

# Changelog

## v6.0

* Initial release of Minimal (Server) version
* Headless operation with system tray icon
* Configurable refresh modes (Realtime 1s / Normal 2s / Low 3s)
* Startup at boot support via Windows Registry
* Adaptive disk polling (slow drives = 5min)
* Single instance enforcement
* HTTP API identical to full app for wallpaper compatibility

---

# License

See the main project license file.

---

# Support

For issues or feature requests, please visit the [main repository](../../).
