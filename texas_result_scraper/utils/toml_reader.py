from pathlib import Path
import tomli
from typing import Dict
from dataclasses import dataclass


@dataclass
class TomlReader:
    """
    A class used to read and process TOML files.

    Attributes:
        file (Path): The path to the TOML file.
        name (str, optional): The name of the TOML file. Defaults to None.
        _data (Dict, optional): The data from the TOML file. Defaults to None.

    Properties:
        data (Dict): Returns the data from the TOML file. Can also set the data.

    Methods:
        replace_null_with_none(data): Replaces all instances of "null" in the data with None.
    """
    file: Path
    name: str = None
    _data: Dict = None

    def __repr__(self):
        return f"{self.file.name}" if not self.name else f"{self.name} TOML file"

    @property
    def data(self) -> Dict:
        with open(self.file, "rb") as f:
            self._data = tomli.load(f)
        return self._data

    @data.setter
    def data(self, value):
        self._data = value

    def replace_null_with_none(self, data):
        def replace_null(item):
            if isinstance(item, dict):
                return {k: replace_null(v) for k, v in item.items()}
            elif isinstance(item, list):
                return [replace_null(v) for v in item]
            elif item == "null":
                return None
            else:
                return item

        self.data = replace_null(data)
        return self.data

    def __post_init__(self):
        # self.load()
        # Replace all values that are "null" with None
        self.data = self.replace_null_with_none(self.data)
