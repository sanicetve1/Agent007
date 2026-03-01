from agentic_app.tools import get_tool


def test_add_tool():
    tool = get_tool("add")
    assert tool.run(a=2, b=3) == 5


def test_subtract_tool():
    tool = get_tool("subtract")
    assert tool.run(a=5, b=3) == 2


def test_multiply_tool():
    tool = get_tool("multiply")
    assert tool.run(a=4, b=3) == 12


def test_divide_tool():
    tool = get_tool("divide")
    assert tool.run(a=10, b=2) == 5


def test_divide_by_zero():
    tool = get_tool("divide")
    try:
        tool.run(a=1, b=0)
    except ValueError as exc:
        assert "Division by zero" in str(exc)
    else:  # pragma: no cover
        assert False, "Expected ValueError for division by zero"

