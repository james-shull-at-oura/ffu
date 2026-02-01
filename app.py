"""
PyWebView DFU Updater – desktop app for BLE firmware updates per DFU Procedure Document v1.0.
"""
import json
from pathlib import Path
import threading
import webview

# Optional: install the package that provides PlatformController (e.g. platform_controller or pyring)
try:
    from platform_controller import PlatformController
except ImportError:
    PlatformController = None

# Default firmware path relative to this script
DEFAULT_FIRMWARE_PATH = (
    Path(__file__).resolve().parent / "bentley_0_2_12" / "bentley-fw.signed.confirmed.bin"
)

# Default advanced DFU settings (per doc); overridden by config.json if present
DEFAULT_ADVANCED = {
    "app_id": 1,
    "start_address": 0,
    "block_size": 512,
    "ring_type": 8,
    "force_flags": 0,
    "reboot_wait": 10,
}

CONFIG_PATH = Path(__file__).resolve().parent / "config.json"


def load_config():
    """Load advanced DFU settings from config.json; use defaults for missing keys."""
    merged = dict(DEFAULT_ADVANCED)
    if CONFIG_PATH.exists():
        try:
            with open(CONFIG_PATH, encoding="utf-8") as f:
                data = json.load(f)
            for key in DEFAULT_ADVANCED:
                if key in data:
                    merged[key] = data[key]
        except (json.JSONDecodeError, OSError):
            pass
    return merged


class DfuApi:
    """API exposed to the WebView via js_api."""

    def __init__(self):
        self._progress = {"current": 0, "total": 0, "message": "", "percentage": 0.0}
        self._progress_lock = threading.Lock()
        self._running = False

    def get_defaults(self):
        """Return default values for the form and advanced (read-only) from config.json."""
        cfg = load_config()
        return {
            "firmware_path": str(DEFAULT_FIRMWARE_PATH),
            "version": "0.2.12",
            "target_name": "oura_",
            "hw_id": "BEM_04",
            "timeout": 10,
            "advanced": cfg,
        }

    def get_progress(self):
        """Return current progress for the UI (thread-safe)."""
        with self._progress_lock:
            return dict(self._progress)

    def start_dfu(
        self,
        firmware_path,
        version,
        target_name,
        hw_id,
        timeout,
    ):
        """
        Run the DFU procedure in a background thread.
        Advanced settings (app_id, start_address, etc.) are read from config.json.
        """
        if PlatformController is None:
            raise RuntimeError(
                "PlatformController is not installed. Add the package that provides it to requirements.txt (e.g. platform_controller or pyring)."
            )

        with self._progress_lock:
            if self._running:
                raise RuntimeError("DFU is already running.")
            self._running = True
            self._progress = {"current": 0, "total": 0, "message": "Starting…", "percentage": 0.0}

        def run():
            try:
                self._set_progress(0, 0, "Connecting…")
                pc = PlatformController(hw_id=hw_id, client_type="ble")
                pc.configure(target_name=target_name, timeout=int(timeout))

                def progress_callback(current: int, total: int, message: str):
                    percentage = (current / total) * 100 if total > 0 else 0
                    self._set_progress(current, total, message, percentage)

                pc.dfu.set_progress_callback(progress_callback)
                self._set_progress(0, 0, "Performing DFU…")

                cfg = load_config()
                success = pc.dfu.perform_dfu(
                    firmware_path=firmware_path,
                    app_id=cfg["app_id"],
                    version=version,
                    start_address=cfg["start_address"],
                    block_size=cfg["block_size"],
                    ring_type=cfg["ring_type"],
                    force_flags=cfg["force_flags"],
                    reboot_wait=cfg["reboot_wait"],
                )
                if success:
                    self._set_progress(100, 100, "DFU completed successfully.", 100.0)
                else:
                    self._set_progress(0, 0, "DFU failed.", 0.0)
                return success
            except Exception as e:
                self._set_progress(0, 0, f"Error: {e}", 0.0)
                raise
            finally:
                with self._progress_lock:
                    self._running = False

        result_holder = []

        def run_and_capture():
            try:
                result_holder.append(run())
            except Exception as e:
                result_holder.append(e)

        thread = threading.Thread(target=run_and_capture)
        thread.start()
        thread.join()
        if result_holder:
            r = result_holder[0]
            if isinstance(r, Exception):
                raise r
            return r
        raise RuntimeError("DFU thread did not return.")

    def _set_progress(self, current, total, message, percentage=None):
        if percentage is None and total > 0:
            percentage = (current / total) * 100
        elif percentage is None:
            percentage = 0.0
        with self._progress_lock:
            self._progress = {
                "current": current,
                "total": total,
                "message": message,
                "percentage": round(percentage, 1),
            }


def main():
    api = DfuApi()
    ui_dir = Path(__file__).resolve().parent / "ui"
    index_path = ui_dir / "index.html"
    url = index_path.as_uri()

    window = webview.create_window(
        "Factory Firmware Updater",
        url=url,
        js_api=api,
        width=520,
        height=560,
    )
    webview.start(debug=False)


if __name__ == "__main__":
    main()
