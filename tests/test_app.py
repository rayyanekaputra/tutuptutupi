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


def test_translations_complete_and_formatting():
    from i18n import STRINGS, set_lang, t
    for key, (en, id_) in STRINGS.items():
        assert en and id_, key
    set_lang("id")
    try:
        assert t("days_ago", n=3) == "3 hari lalu"
    finally:
        set_lang("en")
    assert t("days_ago", n=3) == "3 days ago"
