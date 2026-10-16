import pandas as pd
import pytest

from tutuptutupi import maskers as m
from tutuptutupi.core import ColumnPlan, Plan, auto_plan, mask_frame


@pytest.fixture
def df():
    return pd.DataFrame({
        "region": ["north", "south", "north", "east"] * 3,
        "customer_id": [34123, 9, 1234567890, 555] * 3,
        "name": ["jason brody", "ann lee", None, "vaas montenegro"] * 3,
        "email": ["jb@rook.com", "ann@x.io", "c@d.org", None] * 3,
        "joined": ["15/03/2024", "01/12/2023", None, "28/02/2020"] * 3,
        "amount": [10.5, None, 3.25, 1200.0] * 3,
        "active": [True, False, True, True] * 3,
    })


def test_partial_text():
    assert m.partial_text("jason brody") == "jas** ***dy"
    out = m.partial_text("jb@rook.com")
    assert "@" in out and "." in out and len(out) == 11


def test_partial_id_fixed_width():
    for v in [9, 555, 34123, 1234567890, "AB-77123"]:
        assert len(m.partial_id(v, 8)) == 8
    assert m.partial_id(34123) == "**41****"
    assert m.partial_id(9) == "********"
    k = m.Keyer(1)
    shown = {m.partial_id(v, 8, k) for v in range(34100, 34140)}
    assert len(shown) > 5  # sequential ids don't all look identical
    assert all(len(v) == 8 for v in shown)


def test_partial_date_keeps_format():
    from datetime import datetime
    assert m.partial_date(datetime(2024, 3, 15), "%d/%m/%Y") == "**/**/2024"


def test_auto_roles(df):
    plan = auto_plan(df)
    roles = {c: p.role for c, p in plan.columns.items()}
    assert roles["customer_id"] == "id"
    assert roles["amount"] == "number"
    assert roles["joined"] == "date"
    assert roles["active"] == "bool"
    assert plan.columns["joined"].date_format == "%d/%m/%Y"
    assert plan.columns["amount"].mode == "keep"


def test_shape_and_nulls_preserved(df):
    out = mask_frame(df, auto_plan(df))
    assert out.shape == df.shape
    assert list(out.columns) == list(df.columns)
    assert (out.isna() == df.isna()).all().all()
    pd.testing.assert_series_equal(out["amount"], df["amount"])  # plain numbers untouched


def test_multiindex_preserved(df):
    idx = df.set_index(["region", "customer_id"])
    out = mask_frame(idx, auto_plan(idx))
    assert out.index.names == ["region", "customer_id"]
    assert all(len(v) == 8 for v in out.index.get_level_values("customer_id"))


@pytest.mark.parametrize("mode", ["full", "fake"])
def test_no_real_text_leaks(df, mode):
    plan = auto_plan(df, seed=1)
    for col in ("name", "email", "customer_id"):
        plan.columns[col].mode = mode
    out = mask_frame(df, plan)
    for col in ("name", "email"):
        real = set(df[col].dropna())
        assert not real & set(out[col].dropna())


def test_fake_keeps_dtype_and_is_consistent(df):
    plan = Plan(columns={c: ColumnPlan("number", "fake") for c in ["amount"]}, seed=3)
    small = df[["amount"]]
    a, b = mask_frame(small, plan), mask_frame(small, plan)
    assert a["amount"].dtype == df["amount"].dtype
    pd.testing.assert_frame_equal(a, b)
    assert a["amount"].iloc[0] == a["amount"].iloc[4]  # same input -> same output


def test_fake_int_id_same_digits():
    k = m.Keyer(1)
    assert len(str(m.fake_int(34123, k))) == 5


def test_sampled_range_index_not_written(tmp_path, df):
    from tutuptutupi.core import sample_rows
    from tutuptutupi.fileio import read_table, write_table
    out = tmp_path / "o.csv"
    write_table(mask_frame(sample_rows(df, 3, 0), auto_plan(df)), out)
    assert list(read_table(out).columns) == list(df.columns)
