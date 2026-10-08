"""Canonical node identities and resource visibility for course graphs."""
import copy
from collections import Counter


def graph_children(node):
    for key in ("children", "grandchildren", "great-grandchildren"):
        if isinstance(node.get(key), list):
            return [child for child in node[key] if isinstance(child, dict)]
    return []


def assign_node_ids(graph):
    """Match the IDs used by MySQL, including repeated names in different sections."""
    counts = Counter()
    def count(node):
        counts[str(node.get("name") or "").strip()] += 1
        for child in graph_children(node):
            count(child)
    for child in graph_children(graph):
        count(child)
    def walk(node, path):
        name = str(node.get("name") or "").strip()
        path = path + [name]
        fallback = name if counts[name] <= 1 else " / ".join(path)
        node["node_id"] = str(node.get("node_id") or node.get("id") or fallback[:200]).strip()
        for child in graph_children(node):
            walk(child, path)
    for child in graph_children(graph):
        walk(child, [])
    return graph


def resource_is_enabled(resource):
    return (not resource.get("is_deleted") and bool(resource.get("is_enabled"))
            and str(resource.get("review_status") or "enabled").lower() == "enabled")


def hydrate_resource_graph(graph, resources, *, enabled_only=True):
    """DB review rows are authoritative, including empty/disabled resource lists."""
    result = assign_node_ids(copy.deepcopy(graph))
    by_node = {}
    for resource in resources:
        if resource.get("is_deleted") or (enabled_only and not resource_is_enabled(resource)):
            continue
        path = str(resource.get("resource_path") or "").strip()
        if path:
            by_node.setdefault(str(resource["node_id"]), []).append(path)
    def walk(node):
        node["resource_path"] = list(dict.fromkeys(by_node.get(str(node.get("node_id") or ""), [])))
        for child in graph_children(node):
            walk(child)
    walk(result)
    return result
