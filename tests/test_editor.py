import pandas as pd
import pytest

from core import auto_plan, flatten
from editor import ColumnEditor


@pytest.fixture
def flat():
    df = pd.DataFrame({
        "customer_id": [34123, 555, 9],
        "name": ["jason brody", None, "ann lee"],
        "amount": [1.5, 2.0, None],
    })
    return flatten(df)[0]


async def run_keys(flat, keys):
    app = ColumnEditor(flat, auto_plan(flat, seed=1), "t")
    async with app.run_test(size=(120, 30)) as pilot:
        for k in keys:
            await pilot.press(k)
        await pilot.pause()
    return app


async def test_enter_accepts_guesses(flat):
    app = await run_keys(flat, ["enter"])
    assert app.return_value.columns["customer_id"].mode == "partial"


async def test_change_mode_of_second_column(flat):
    # right -> name, tab -> mode field, down: partial -> full
    app = await run_keys(flat, ["right", "tab", "down", "enter"])
    plan = app.return_value
    assert plan.columns["name"].mode == "full"
    assert plan.columns["customer_id"].mode == "partial"


async def test_keep_on_text_needs_second_enter(flat):
    # name mode: partial -> keep is up once (wraps to last)
    app = await run_keys(flat, ["right", "tab", "up", "enter"])
    assert app.return_value is None  # first enter only warns
    assert app.confirming is True
    app2 = await run_keys(flat, ["right", "tab", "up", "enter", "enter"])
    assert app2.return_value.columns["name"].mode == "keep"


async def test_escape_cancels(flat):
    app = await run_keys(flat, ["escape"])
    assert app.return_value is None


async def test_masked_sample_hides_raw(flat):
    app = ColumnEditor(flat, auto_plan(flat, seed=1), "t")
    async with app.run_test(size=(120, 30)):
        text = str(app.query_one("#c1").render())
        assert "jason brody" not in text
        assert "34123" not in str(app.query_one("#c0").render())


async def test_arrows_work_when_columns_overflow():
    df = pd.DataFrame({f"col{i}": ["abcdef"] for i in range(10)})
    app = ColumnEditor(df, auto_plan(df, seed=1), "t")
    async with app.run_test(size=(80, 20)) as pilot:
        await pilot.press("right", "right", "right")
        assert app.idx == 3


async def test_index_picker_order_and_toggle(flat):
    from editor import IndexPicker
    app = IndexPicker(flat, "t")
    async with app.run_test(size=(120, 30)) as pilot:
        # tick name, then customer_id, untick + retick nothing else
        await pilot.press("right", "space", "left", "down", "right", "right", "space", "space", "enter")
    assert app.return_value == ["name", "customer_id"]


async def test_index_picker_none_and_cancel(flat):
    from editor import IndexPicker
    app = IndexPicker(flat, "t")
    async with app.run_test() as pilot:
        await pilot.press("enter")
    assert app.return_value == []
    app = IndexPicker(flat, "t")
    async with app.run_test() as pilot:
        await pilot.press("escape")
    assert app.return_value is None
