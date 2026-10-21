"""Every tool registers once, and graph_stats is the graph-module version.

Run: .venv/bin/python -m pytest tests/test_tool_registry.py
"""
import asyncio
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


def test_graph_stats_is_the_graph_module_tool():
    import stella_server
    tools = {t.name: t for t in asyncio.run(stella_server.mcp.list_tools())}
    assert tools["graph_stats"].description.startswith("Return current knowledge graph statistics")
    assert len(tools) == 88


def test_no_tool_registers_twice():
    import importlib
    import stella_server
    seen = []
    handler = logging.Handler()
    handler.emit = lambda record: seen.append(record.getMessage())
    logging.getLogger("mcp.server.fastmcp.tools.tool_manager").addHandler(handler)
    try:
        importlib.reload(stella_server)
    finally:
        logging.getLogger("mcp.server.fastmcp.tools.tool_manager").removeHandler(handler)
    assert not [m for m in seen if "already exists" in m], seen
