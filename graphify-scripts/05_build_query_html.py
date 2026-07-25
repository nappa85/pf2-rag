import json
import re
from pathlib import Path

GRAPH_JSON = Path("graphify-out/graph.json")
TEMPLATE = Path("graphify-scripts/query_template.html")
OUTPUT = Path("graphify-out/query.html")

graph_json_str = GRAPH_JSON.read_text(encoding="utf-8")
html = TEMPLATE.read_text(encoding="utf-8")

html = html.replace(
    "async function init() {\n  const resp = await fetch('graph.json');\n  graphData = await resp.json();",
    "function init() {\n  graphData = GRAPH_DATA;",
)

script_tag = "<script>"
data_script = f"<script>const GRAPH_DATA = {graph_json_str};</script>"
html = html.replace(script_tag, data_script + "\n" + script_tag, 1)

OUTPUT.write_text(html, encoding="utf-8")
print(f"Written {OUTPUT.stat().st_size} bytes to {OUTPUT}")
