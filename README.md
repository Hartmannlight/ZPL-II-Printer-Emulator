# ZPL-II-Printer-Emulator

A small virtual ZPL II network printer for development. It listens for raw ZPL on a TCP
port, renders the label through Labelary, and shows recent print jobs in a minimal web UI.

## Quick start

```bash
uv sync --extra dev
uv run zpl-printer-emulator
```

Open the UI:

```text
http://127.0.0.1:9191
```

Configure a development printer in PrintHub/ZPLGrid like this:

```yaml
- id: virtual-zpl-dev
  name: Virtual ZPL Dev Printer
  model: ZPL-II-Printer-Emulator
  vendor: Local
  driver: zpl
  connection:
    protocol: raw9100
    host: 127.0.0.1
    port: 9100
    timeout_ms: 3000
  media:
    loaded:
      width_mm: 50
      height_mm: 25
      color: white
      type: virtual
  alignment:
    dpi: 203
    offset_x_mm: 0
    offset_y_mm: 0
  zpl:
    darkness: 10
    print_speed: 3
    print_mode: tear_off
  defaults:
    copies: 1
    rotation: 0
  capabilities:
    supports_status: false
    supports_graphics: true
    supports_cut: false
  enabled: true
```

## Configuration

Environment variables:

- `ZPL_EMULATOR_HOST`: web host, default `127.0.0.1`
- `ZPL_EMULATOR_WEB_PORT`: web port, default `9191`
- `ZPL_EMULATOR_TCP_HOST`: TCP printer host, default `127.0.0.1`
- `ZPL_EMULATOR_TCP_PORT`: TCP printer port, default `9100`
- `ZPL_EMULATOR_LABEL_WIDTH_IN`: label width for Labelary, default `1.9685`
- `ZPL_EMULATOR_LABEL_HEIGHT_IN`: label height for Labelary, default `0.9843`
- `ZPL_EMULATOR_DPMM`: Labelary density, default `8`
- `ZPL_EMULATOR_LABELARY_URL`: Labelary base URL, default `https://api.labelary.com`

## Tests

```bash
uv run pytest
```
