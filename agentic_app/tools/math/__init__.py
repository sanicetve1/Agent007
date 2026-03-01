from agentic_app.tools.math.add import AddTool
from agentic_app.tools.math.subtract import SubtractTool
from agentic_app.tools.math.multiply import MultiplyTool
from agentic_app.tools.math.divide import DivideTool
from agentic_app.tools.registry import register_tool


def _register_math_tools() -> None:
    register_tool(AddTool())
    register_tool(SubtractTool())
    register_tool(MultiplyTool())
    register_tool(DivideTool())


_register_math_tools()

