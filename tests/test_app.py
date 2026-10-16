import os

from app import list_files


def test_list_files(tmp_path):
    names = ["old.csv", "new.xlsx", "x.masked.csv", "notes.txt", "x.masked.schema.md"]
    for i, n in enumerate(names):
        f = tmp_path / n
        f.write_text("a")
        os.utime(f, (1000 + i, 1000 + i))
    os.utime(tmp_path / "new.xlsx", (5000, 5000))
    (tmp_path / "sub").mkdir()
    (tmp_path / "sub" / "deep.csv").write_text("a")
    assert [p.name for p in list_files(tmp_path)] == ["new.xlsx", "old.csv"]
