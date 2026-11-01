"""Utilities for exporting JSON-compatible records."""

import csv
import json
import pathlib
from collections.abc import Mapping, Sequence


def json_to_csv(
    records: Sequence[Mapping[str, object]],
    output_folder: str | pathlib.Path = ".",
    filename: str = "output.csv",
) -> pathlib.Path:
    """Writes JSON-compatible records to a UTF-8 CSV file.

    Columns follow first-seen key order and rows preserve record order. Missing
    values are blank; strings are unchanged and other values are JSON strings,
    including explicit None as null. Empty input produces a zero-byte file.

    Args:
        records: JSON-compatible dictionaries with string keys.
        output_folder: Destination folder, created recursively when missing.
        filename: Destination filename. Any existing file is overwritten.

    Returns:
        The destination path without resolving it.

    Raises:
        OSError: If creating the directory or writing the file fails.
    """
    output_path = pathlib.Path(output_folder) / filename
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with output_path.open("w", encoding="utf-8", newline="") as output_file:
        if not records:
            return output_path

        columns: dict[str, None] = {}
        for record in records:
            columns.update(dict.fromkeys(record))

        writer = csv.DictWriter(output_file, fieldnames=list(columns))
        writer.writeheader()
        for record in records:
            writer.writerow(
                {
                    key: value
                    if isinstance(value, str)
                    else json.dumps(value, ensure_ascii=False)
                    for key, value in record.items()
                }
            )

    return output_path
