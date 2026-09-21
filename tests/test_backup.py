import json

from statistic_table.backup import write_backup


def test_write_backup_creates_json_with_expected_content(tmp_path):
    zapasy_row = ["18.9.2026", "LIT", "Příbram", "1", "3"]
    sestavy_row = ["2", "Weber"]

    path = write_backup(6, zapasy_row, sestavy_row, backup_dir=tmp_path)

    assert path.exists()
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert payload["row"] == 6
    assert payload["zapasy"] == zapasy_row
    assert payload["sestavy"] == sestavy_row
    assert "timestamp" in payload


def test_write_backup_creates_missing_directory(tmp_path):
    backup_dir = tmp_path / "nested" / "backups"
    path = write_backup(7, [], [], backup_dir=backup_dir)
    assert path.exists()
    assert path.parent == backup_dir


def test_write_backup_produces_unique_filenames_per_row(tmp_path):
    path_a = write_backup(6, ["x"], ["y"], backup_dir=tmp_path)
    path_b = write_backup(7, ["x"], ["y"], backup_dir=tmp_path)
    assert path_a != path_b
    assert "radek6" in path_a.name
    assert "radek7" in path_b.name
