"""APEXIUM: practical, transparent tools for real-world motorsport data."""
from .client import Apexium, Race
from .dataset import Dataset
from .transport import ApexiumError, APIError
from . import analytics

__version__ = "1.0.0"
__all__ = ["Apexium", "Race", "Dataset", "ApexiumError", "APIError", "analytics"]
