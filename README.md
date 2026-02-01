# Factory Firmware Updater

# Assumptions
- Target: Update ring with factory firmware to Bentley 0.2.12 customer image.
- Dongle: Must be Pro. [BleuIO Pro](https://www.bleuio.com/bluetooth-low-energy-usb-ssd025.php#product-area)

# Find Target Name
Use pyring-ORT to find the ring's name. You can see and connect to the ring but no normal functionality in pyring-ort after that. The factory firmware as a different api.

# Config (advanced settings)
Edit `config.json` before launch to change advanced DFU parameters (APP_ID, START_ADDRESS, BLOCK_SIZE, RING_TYPE, FORCE_FLAGS, REBOOT_WAIT). These are shown read-only in the app and used for `perform_dfu`. If the file is missing or invalid, doc defaults are used.

# Run the app
Install dependencies (including the package that provides `PlatformController`, e.g. `platform_controller` or `pyring`), then:

```bash
pip install -r requirements.txt
python app.py
```

The pywebview window lets you set firmware path, version, target name, hw_id, and timeout (defaults are pre-filled), then run the DFU and see progress from the progress callback.

