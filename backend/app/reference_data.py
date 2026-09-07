import json
from pathlib import Path

REFERENCE_DATA_PATH = Path(__file__).parents[2] / "shared" / "reference_data.json"

with REFERENCE_DATA_PATH.open(encoding="utf-8") as reference_data_file:
    REFERENCE_DATA = json.load(reference_data_file)

DEPARTMENTS: tuple[str, ...] = tuple(REFERENCE_DATA["departments"])
COUNTRY_CURRENCIES: dict[str, str] = REFERENCE_DATA["countries"]
BANDS: tuple[str, ...] = tuple(REFERENCE_DATA["bands"])
STATUSES: tuple[str, ...] = tuple(REFERENCE_DATA["statuses"])
