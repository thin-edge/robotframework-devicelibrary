"""DeviceLibrary for Robot Framework"""
from importlib.metadata import version, PackageNotFoundError
from .DeviceLibrary import DeviceLibrary

try:
    __version__ = version("DeviceLibrary")
except PackageNotFoundError:
    __version__ = "0.0.0"
