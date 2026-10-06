from pathlib import Path

import configuration


def get_xml(xml_file_name: str) -> str:
    xml_file_path = Path(configuration.DATA_PATH, xml_file_name)
    try:
        with open(xml_file_path, mode="r") as file:
            return file.read()
    except FileNotFoundError:
        raise TypeError("No XML")
