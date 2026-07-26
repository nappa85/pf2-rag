import json
from pathlib import Path

GRAPH_JSON = Path("graphify-out/graph.json")
GRAPH_HTML = Path("graphify-out/graph.html")

graph = json.loads(GRAPH_JSON.read_text(encoding="utf-8"))

desc_map = {}
talent_type_map = {}
level_map = {}
for n in graph["nodes"]:
    if n.get("description"):
        desc_map[n["id"]] = n["description"]
    if n.get("talent_type"):
        talent_type_map[n["id"]] = n["talent_type"]
    if n.get("level") is not None:
        level_map[n["id"]] = n["level"]

html = GRAPH_HTML.read_text(encoding="utf-8")

idx_nodes = html.find("RAW_NODES = ")
idx_edges = html.find("RAW_EDGES = ")
end_nodes = html.find("];", idx_nodes) + 1

nodes_str = html[idx_nodes + len("RAW_NODES = "):end_nodes]
nodes = json.loads(nodes_str)

enriched = 0
for n in nodes:
    nid = n["id"]
    desc = desc_map.get(nid, "")
    ttype = talent_type_map.get(nid, "")
    lv = level_map.get(nid)

    if desc:
        n["description"] = desc
        n["hover_desc"] = desc[:150]
        enriched += 1
    if ttype:
        n["talent_type"] = ttype
    if lv is not None:
        n["level"] = lv

print(f"Enriched {enriched}/{len(nodes)} nodes with descriptions")

new_nodes_str = json.dumps(nodes, ensure_ascii=False)
new_html = html[:idx_nodes + len("RAW_NODES = ")] + new_nodes_str + html[end_nodes:]

# Patch showInfo to display description + talent_type + level
old_showinfo = '    <div class="field"><b>${esc(n.label)}</b></div>\n    <div class="field">Type: ${esc(n._file_type || \'unknown\')}</div>\n    <div class="field">Community: ${esc(n._community_name)}</div>\n    <div class="field">Source: ${esc(n._source_file || \'-\')}</div>\n    <div class="field">Degree: ${n._degree}</div>'

new_showinfo = '    <div class="field"><b>${esc(n.label)}</b></div>\n    <div class="field">Type: ${esc(n._file_type || \'unknown\')}</div>\n    ${n.description ? `<div class="field" style="color:#e0e0e0;margin:6px 0;padding:6px 8px;background:rgba(255,255,255,0.06);border-radius:4px;font-size:12px;line-height:1.5">${esc(n.description)}</div>` : \'\'}\n    ${n.talent_type ? `<div class="field"><span style="color:#aaa">Tipo:</span> ${esc(n.talent_type)}</div>` : \'\'}\n    ${n.level != null ? `<div class="field"><span style="color:#aaa">Livello:</span> ${n.level}</div>` : \'\'}\n    <div class="field">Community: ${esc(n._community_name)}</div>\n    <div class="field">Source: ${esc(n._source_file || \'-\')}</div>\n    <div class="field">Degree: ${n._degree}</div>'

new_html = new_html.replace(old_showinfo, new_showinfo)

# Patch nodesDS mapping to carry description, talent_type, level through
old_ds_map = "_degree: n.degree,"
new_ds_map = "_degree: n.degree, description: n.description, talent_type: n.talent_type, level: n.level, title: n.hover_desc || n.title,"
new_html = new_html.replace(old_ds_map, new_ds_map)

GRAPH_HTML.write_text(new_html, encoding="utf-8")
print(f"Patched graph.html ({len(new_html)} bytes)")
