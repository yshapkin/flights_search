import csv
import json
import pathlib
import types

import pytest

import core.utils
from core.utils import json_utils


def _read_rows(path: pathlib.Path) -> list[list[str]]:
    with path.open(encoding="utf-8", newline="") as csv_file:
        return list(csv.reader(csv_file))


def test_json_utils_import_resolves_new_module_without_function_shim() -> None:
    core_folder = pathlib.Path(__file__).resolve().parents[1] / "src" / "core"
    old_module = core_folder / "utils.py"

    assert not old_module.exists()
    assert not old_module.is_symlink()
    assert pathlib.Path(core.utils.__file__).resolve() == (
        core_folder / "utils" / "__init__.py"
    )
    assert isinstance(json_utils, types.ModuleType)
    assert json_utils.__name__ == "core.utils.json_utils"
    assert pathlib.Path(json_utils.__file__).resolve() == (
        core_folder / "utils" / "json_utils.py"
    )
    assert core.utils.json_utils is json_utils
    assert callable(json_utils.json_to_csv)
    assert not hasattr(core.utils, "json_to_csv")


def test_default_destination_is_an_unresolved_path(
    tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)

    destination = json_utils.json_to_csv([{"code": "FRA"}])

    assert isinstance(destination, pathlib.Path)
    assert destination == pathlib.Path("output.csv")
    assert not destination.is_absolute()
    assert _read_rows(destination) == [["code"], ["FRA"]]


@pytest.mark.parametrize("use_string_folder", [False, True])
def test_custom_folder_and_filename_create_missing_parents(
    tmp_path: pathlib.Path, use_string_folder: bool
) -> None:
    folder = tmp_path / "missing" / "nested"
    output_folder = str(folder) if use_string_folder else folder

    destination = json_utils.json_to_csv(
        [{"code": "FRA"}], output_folder, "airports.csv"
    )

    assert destination == folder / "airports.csv"
    assert folder.is_dir()
    assert destination.is_file()
    assert _read_rows(destination) == [["code"], ["FRA"]]


def test_custom_relative_destination_remains_unresolved(
    tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    folder = pathlib.Path("exports") / "nested"

    destination = json_utils.json_to_csv(
        [{"code": "FRA"}], output_folder=folder, filename="custom.csv"
    )

    assert destination == folder / "custom.csv"
    assert not destination.is_absolute()
    assert _read_rows(destination) == [["code"], ["FRA"]]


def test_first_seen_columns_and_record_order_include_empty_mappings(
    tmp_path: pathlib.Path,
) -> None:
    records = [
        {},
        {"z": "first", "a": "one"},
        {"a": "two", "late": "introduced"},
        {"other": "last", "z": "final"},
        {},
    ]

    destination = json_utils.json_to_csv(records, tmp_path)

    assert _read_rows(destination) == [
        ["z", "a", "late", "other"],
        ["", "", "", ""],
        ["first", "one", "", ""],
        ["", "two", "introduced", ""],
        ["final", "", "", "last"],
        ["", "", "", ""],
    ]


@pytest.mark.parametrize("record_count", [1, 3])
def test_all_empty_mappings_preserve_zero_field_header_and_rows(
    tmp_path: pathlib.Path, record_count: int
) -> None:
    destination = json_utils.json_to_csv(
        [{} for _ in range(record_count)], tmp_path
    )

    assert _read_rows(destination) == [[] for _ in range(record_count + 1)]


def test_sequence_of_mappings_uses_the_public_contract(
    tmp_path: pathlib.Path,
) -> None:
    records = (
        types.MappingProxyType({"b": 1}),
        types.MappingProxyType({"a": 2}),
    )

    destination = json_utils.json_to_csv(records, tmp_path)

    assert _read_rows(destination) == [["b", "a"], ["1", ""], ["", "2"]]


def test_scalar_json_representations_distinguish_null_from_missing(
    tmp_path: pathlib.Path,
) -> None:
    records = [
        {
            "text": "present",
            "integer": 17,
            "negative_integer": -12,
            "zero": 0,
            "float": 1.25,
            "negative_float": -2.5,
            "float_zero": 0.0,
            "true": True,
            "false": False,
            "null": None,
        },
        {"text": "missing"},
    ]

    destination = json_utils.json_to_csv(records, tmp_path)

    assert _read_rows(destination) == [
        [
            "text",
            "integer",
            "negative_integer",
            "zero",
            "float",
            "negative_float",
            "float_zero",
            "true",
            "false",
            "null",
        ],
        [
            "present",
            "17",
            "-12",
            "0",
            "1.25",
            "-2.5",
            "0.0",
            "true",
            "false",
            "null",
        ],
        ["missing", "", "", "", "", "", "", "", "", ""],
    ]


def test_nested_objects_and_lists_remain_json_cells(
    tmp_path: pathlib.Path,
) -> None:
    nested_object = {
        "city": "\u6771\u4eac",
        "items": [1, 1.25, True, False, None, {}, []],
    }
    nested_list = [
        "\u96ea",
        7,
        False,
        None,
        {"label": 'comma, quote" and\r\nnewline'},
        [],
    ]
    records = [
        {
            "object": nested_object,
            "list": nested_list,
            "empty_object": {},
            "empty_list": [],
        }
    ]

    destination = json_utils.json_to_csv(records, tmp_path)
    rows = _read_rows(destination)

    assert len(rows) == 2
    assert rows[0] == ["object", "list", "empty_object", "empty_list"]
    assert [json.loads(cell) for cell in rows[1]] == [
        nested_object,
        nested_list,
        {},
        [],
    ]


@pytest.mark.parametrize(
    ("header", "text"),
    [
        ("comma,header", "before,after"),
        ('quoted"header', 'before "quoted" after'),
        ("carriage\rheader", "before\rafter"),
        ("line\nheader", "before\nafter"),
        ("paired\r\nheader", "before\r\nafter"),
        ("\u65e5\u672c\u8a9e", "M\u00fcnchen \u6771\u4eac \U0001f680"),
        (" leading and trailing ", " \t leading and trailing \t "),
        ("", ""),
    ],
    ids=["comma", "quote", "cr", "lf", "crlf", "unicode", "space", "empty"],
)
def test_headers_and_strings_roundtrip_exactly_in_utf8_csv(
    tmp_path: pathlib.Path, header: str, text: str
) -> None:
    destination = json_utils.json_to_csv([{header: text}], tmp_path)

    assert _read_rows(destination) == [[header], [text]]


@pytest.mark.parametrize(
    "text",
    [
        "null",
        "true",
        "false",
        "42",
        "1.25",
        '{"x": 1}',
        "[true, null]",
        "=SUM(A1:A2)",
        "+SUM(A1:A2)",
        "-SUM(A1:A2)",
        "@SUM(A1:A2)",
        "'literal",
    ],
)
def test_json_and_formula_like_strings_are_not_transformed(
    tmp_path: pathlib.Path, text: str
) -> None:
    destination = json_utils.json_to_csv([{"text": text}], tmp_path)

    assert _read_rows(destination) == [["text"], [text]]


def test_overwrite_truncates_longer_existing_csv(
    tmp_path: pathlib.Path,
) -> None:
    existing = tmp_path / "replace.csv"
    existing.write_bytes(b"name\r\n" + b"x" * 1024 + b"\r\nstale\r\n")

    destination = json_utils.json_to_csv(
        [{"name": "new"}], tmp_path, "replace.csv"
    )

    assert destination == existing
    assert _read_rows(destination) == [["name"], ["new"]]
    assert destination.read_bytes() == b"name\r\nnew\r\n"


@pytest.mark.parametrize("existing_folder", [False, True])
def test_empty_input_creates_zero_byte_file_in_new_or_existing_folder(
    tmp_path: pathlib.Path, existing_folder: bool
) -> None:
    folder = tmp_path / "empty" / "nested"
    if existing_folder:
        folder.mkdir(parents=True)

    destination = json_utils.json_to_csv([], folder, "empty.csv")

    assert destination == folder / "empty.csv"
    assert destination.is_file()
    assert destination.read_bytes() == b""


def test_empty_input_truncates_previously_populated_csv(
    tmp_path: pathlib.Path,
) -> None:
    existing = tmp_path / "populated.csv"
    existing.write_bytes(b"name\r\n" + b"previous" * 100 + b"\r\n")

    destination = json_utils.json_to_csv([], tmp_path, "populated.csv")

    assert destination == existing
    assert destination.is_file()
    assert destination.read_bytes() == b""


def test_file_occupying_output_folder_propagates_native_error(
    tmp_path: pathlib.Path,
) -> None:
    occupied = tmp_path / "occupied"
    occupied.write_text("occupied", encoding="utf-8")

    with pytest.raises(FileExistsError):
        json_utils.json_to_csv([{"code": "FRA"}], occupied)


def test_directory_occupying_output_file_propagates_native_error(
    tmp_path: pathlib.Path,
) -> None:
    occupied = tmp_path / "occupied.csv"
    occupied.mkdir()

    with pytest.raises(IsADirectoryError):
        json_utils.json_to_csv([{"code": "FRA"}], tmp_path, "occupied.csv")
