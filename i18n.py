"""ui strings in english and bahasa indonesia. role/mode names stay as-is (they are values)."""

from __future__ import annotations

LANGS = {"en": "English", "id": "Bahasa Indonesia"}

_lang = "en"

STRINGS: dict[str, tuple[str, str]] = {
    # app
    "banner": ("mask data, keep the shape", "samarkan data, bentuknya tetap"),
    "cancelled": ("cancelled", "dibatalkan"),
    "path_prompt": ("path to file:", "path file:"),
    "path_invalid": ("must be an existing {exts} file", "harus file {exts} yang sudah ada"),
    "not_a_file": ("not a file:", "bukan file:"),
    "no_files": ("no supported files in {folder}", "tidak ada file yang didukung di {folder}"),
    "today": ("today", "hari ini"),
    "yesterday": ("yesterday", "kemarin"),
    "days_ago": ("{n} days ago", "{n} hari lalu"),
    "type_path": ("✎ type a path…", "✎ ketik path…"),
    "pick_file": ("file to mask: (arrows to move, type to filter)",
                  "file yang mau disamarkan: (panah untuk pindah, ketik untuk filter)"),
    "sheet": ("sheet:", "sheet:"),
    "overview_title": ("{rows} rows x {cols} columns", "{rows} baris x {cols} kolom"),
    "overview_index": (", index: {names}", ", index: {names}"),
    "h_column": ("column", "kolom"),
    "h_dtype": ("dtype", "dtype"),
    "h_null": ("null %", "% null"),
    "h_unique": ("unique", "unik"),
    "h_role": ("role", "peran"),
    "h_mode": ("mode", "mode"),
    "h_sample": ("sample", "contoh"),
    "preview_title": ("masked preview", "pratinjau hasil samaran"),
    "summary_title": ("masking plan (sample row shown masked)",
                      "rencana masking (contoh baris ditampilkan tersamar)"),
    "real_values": ("⚠ real values", "⚠ nilai asli"),
    "ask_role": ("[{col}] ({dtype}) role:", "[{col}] ({dtype}) peran:"),
    "ask_mode": ("[{col}] mask mode:", "[{col}] mode samaran:"),
    "confirm_keep": ("[{col}] keep real {role} values unmasked?",
                     "[{col}] biarkan nilai {role} asli tanpa disamarkan?"),
    "no_date_format": ("couldn't detect a date format for {col}; masking it as text",
                       "format tanggal {col} tidak terdeteksi; disamarkan sebagai teks"),
    "pick_change": ("which columns do you want to change? (space to tick, enter with none = accept)",
                    "kolom mana yang mau diubah? (spasi untuk centang, enter tanpa pilihan = terima)"),
    "index_unavailable": ("index picker unavailable ({err}); using prompts",
                          "pemilih index tidak tersedia ({err}); pakai prompt"),
    "pick_index": ("which columns form the index? (none = plain range index, 2+ = multiindex)",
                   "kolom mana yang jadi index? (kosong = nomor baris biasa, 2+ = multiindex)"),
    "editor_unavailable": ("column editor unavailable ({err}); using prompts",
                           "editor kolom tidak tersedia ({err}); pakai prompt"),
    "ask_rows": ("how many rows to export? (of {total}, 'all' for everything)",
                 "berapa baris yang diekspor? (dari {total}, 'semua' untuk semuanya)"),
    "rows_invalid": ("a positive number or 'all'", "angka positif atau 'semua'"),
    "ask_id_width": ("fixed width for masked ids:", "lebar tetap untuk id yang disamarkan:"),
    "positive_number": ("a positive number", "angka positif"),
    "save_to": ("save to:", "simpan ke:"),
    "no_overwrite": ("refusing to overwrite the input file", "tidak akan menimpa file input"),
    "bad_output": ("unsupported output type:", "jenis output tidak didukung:"),
    "confirm_write": ("write {n} masked rows to {out}?", "tulis {n} baris tersamar ke {out}?"),
    "nothing_written": ("nothing written", "tidak ada yang ditulis"),
    "done": ("done", "selesai"),
    "notes_hint": ("(dtypes & roles, paste it next to the data)", "(dtype & peran, tempel di samping data)"),
    "disclaimer": ("partial masking still reveals part of each value: fine for an llm, not for public release.",
                   "mode partial masih memperlihatkan sebagian nilai: aman untuk llm, bukan untuk dipublikasikan."),
    # editor
    "title_counts": ("({rows} rows, {cols} columns)", "({rows} baris, {cols} kolom)"),
    "step_masking": ("step 2: masking", "langkah 2: masking"),
    "step_index": ("step 1: index columns", "langkah 1: kolom index"),
    "help_editor": ("←/→ column   ↑/↓ change   tab role/mode   enter done   esc cancel",
                    "←/→ kolom   ↑/↓ ubah   tab peran/mode   enter selesai   esc batal"),
    "help_index": ("←/→ column   space or ↑/↓ toggle index   enter done (none = plain index)   esc cancel",
                   "←/→ kolom   spasi atau ↑/↓ pilih index   enter selesai (kosong = index biasa)   esc batal"),
    "f_role": ("role", "peran"),
    "f_mode": ("mode", "mode"),
    "confirm_risky": ("⚠ {cols} will be exported with REAL values. enter again to confirm, any change to cancel.",
                      "⚠ {cols} akan diekspor dengan nilai ASLI. enter lagi untuk konfirmasi, ubah apa saja untuk batal."),
    "risky": ("⚠ real values kept in: {cols}", "⚠ nilai asli dibiarkan di: {cols}"),
    "no_index": ("no index: plain row numbers", "tanpa index: nomor baris biasa"),
    "index_one": ("index: {col}", "index: {col}"),
    "index_multi": ("multiindex: {cols}", "multiindex: {cols}"),
    "unique_count": ("unique: {n}/{total}", "unik: {n}/{total}"),
    "index_on": ("[✓] index #{n}", "[✓] index #{n}"),
    "index_off": ("[ ] index", "[ ] index"),
}

ALL_WORDS = ("all", "semua")  # accepted in either language


def set_lang(lang: str) -> None:
    global _lang
    if lang not in LANGS:
        raise ValueError(f"unknown language: {lang}")
    _lang = lang


def get_lang() -> str:
    return _lang


def t(key: str, **kw: object) -> str:
    en, id_ = STRINGS[key]
    text = id_ if _lang == "id" else en
    return text.format(**kw) if kw else text
