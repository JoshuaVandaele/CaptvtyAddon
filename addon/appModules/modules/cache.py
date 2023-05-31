import json
import os
import shutil
import tempfile
import threading
from typing import Any, Dict


class Cache(dict):
    """Class for handling a JSON cache file in a thread-safe manner."""

    def __init__(self, cache_file: str):
        """
        Constructor method.

        Raises:
            IOError: If the cache file cannot be read.
            json.JSONDecodeError: If the cache file does not contain valid JSON.

        Args:
            cache_file (str): Path to the cache file.
        """
        self.cache_file: str = os.path.abspath(cache_file)
        self.lock: threading.Lock = threading.Lock()
        super().__init__(self._load_cache_from_file())

    def _cache_file_exists(self) -> bool:
        """Checks if the cache file exists.

        Returns:
            bool: True if the cache file exists, False otherwise.
        """
        return os.path.exists(self.cache_file) and os.path.isfile(self.cache_file)

    def _load_cache_from_file(self) -> Dict[str, Any]:
        """
        Load data from the cache file. If the file does not exist or an error occurs,
        returns an empty dictionary.

        Raises:
            IOError: If the cache file cannot be read.
            json.JSONDecodeError: If the cache file does not contain valid JSON.

        Returns:
            Dict[str, Any]: The data loaded from the cache file or an empty dictionary.
        """
        with self.lock:
            # Check if the cache file exists. If not, return an empty dictionary.
            if not self._cache_file_exists():
                return {}

            # Check if the cache file is empty. If so, return an empty dictionary.
            file_size: int = os.path.getsize(self.cache_file)
            if file_size == 0:
                return {}

            with open(self.cache_file, "r") as f:
                return json.load(f)

    def save_cache_to_file(self) -> None:
        """
        Save data to the cache file.

        Raises:
            IOError: If the cache file cannot be written to.
            FileNotFoundError: If the cache file cannot be found.
        """
        with self.lock:
            # We first write the data to a temporary file and then move it.
            # This is to avoid the cache file being corrupted if the program crashes while writing to it.
            with tempfile.NamedTemporaryFile(
                mode="w", dir=os.path.dirname(self.cache_file), delete=False
            ) as tf:
                json.dump(self, tf)
                tempname: str = tf.name
            shutil.move(tempname, self.cache_file)
