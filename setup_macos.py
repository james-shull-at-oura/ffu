"""
py2app setup for building the Factory Firmware Updater .app bundle on macOS.
Usage: python setup_macos.py py2app
"""
import glob
from setuptools import setup

# Data files to include in the .app bundle (relative to Contents/Resources)
DATA_FILES = [
    ("ui", glob.glob("ui/*")),
    ("bentley_0_2_12", glob.glob("bentley_0_2_12/*.bin")),
    (".", ["config.json"]),
]

OPTIONS = {
    "argv_emulation": False,
    "strip": True,
    "includes": ["WebKit", "Foundation", "webview"],
}

setup(
    app=["app.py"],
    data_files=DATA_FILES,
    options={"py2app": OPTIONS},
    setup_requires=["py2app"],
)
