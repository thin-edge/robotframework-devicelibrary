"""DeviceLibrary for Robot Framework"""
import sys

if sys.version_info < (3, 8):
    from importlib_metadata import version, PackageNotFoundError
else:
    from importlib.metadata import version, PackageNotFoundError

from .DeviceLibrary import DeviceLibrary
from .DeviceLibrary import DeviceAdapter

try:
    __version__ = version("DeviceLibrary")
except PackageNotFoundError:
    __version__ = "0.0.0"
