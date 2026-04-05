"""
CourseTree: loads data/course/big_data.json and builds
  - _leaf_map:     node_id -> node_path (root-to-leaf list of names)
  - _resource_map: node_id -> list of resource path strings
"""

import json
from pathlib import Path


# Keys that indicate a node has children
_CHILD_KEYS = ("grandchildren", "great-grandchildren")


class CourseTree:
    def __init__(self, path: str = "data/course/big_data.json"):
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)

        self._leaf_map: dict[str, list[str]] = {}
        self._all_node_map: dict[str, list[str]] = {}
        self._resource_map: dict[str, list[str]] = {}
        self._alias_map: dict[str, str] = {
            "\u534a\u7ed3\u6784\u5316\u6570\u636e": "\u534a\u7ed3\u6784\u5316\u6570\u636e\u548c\u51c6\u7ed3\u6784\u5316\u6570\u636e",
            "\u6570\u636e\u7ba1\u7406\u8fc7\u7a0b": "\u6570\u636e\u7ba1\u7406\u7684\u8fc7\u7a0b",
            "\u6570\u636e\u6e05\u6d17": "\u6570\u636e\u6e05\u6d17\u548c\u5efa\u6a21",
        }

        root_name: str = data.get("root_name", "")
        for child in data.get("children", []):
            self._traverse(child, [root_name])

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _get_children(self, node: dict) -> list:
        """Return the first non-empty child list found, or []."""
        for key in _CHILD_KEYS:
            children = node.get(key)
            if children:
                return children
        return []

    def _parse_resource(self, node: dict) -> list[str]:
        rp = node.get("resource_path", "")
        if isinstance(rp, list):
            return [r for r in rp if r]
        if isinstance(rp, str) and rp:
            return [rp]
        return []

    def _traverse(self, node: dict, path_so_far: list[str]) -> None:
        name: str = node.get("name", "")
        current_path = path_so_far + [name]
        self._all_node_map[name] = current_path
        children = self._get_children(node)

        if not children:
            # Leaf node
            self._leaf_map[name] = current_path
            self._resource_map[name] = self._parse_resource(node)
        else:
            # Internal node — also store its resources (for ResourceRecommender)
            resources = self._parse_resource(node)
            if resources:
                self._resource_map[name] = resources
            for child in children:
                self._traverse(child, current_path)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def get_all_leaf_nodes(self) -> list[str]:
        """Return all leaf node IDs."""
        return list(self._leaf_map.keys())

    def get_node_path(self, node_id: str) -> list[str]:
        """Return root-to-leaf path for node_id, or [] if not found."""
        return self._leaf_map.get(node_id, [])

    def resolve_node_path(self, node_id: str) -> list[str]:
        """Return the best-effort path for a node, supporting non-leaf nodes and aliases."""
        if not node_id:
            return []

        if node_id in self._leaf_map:
            return self._leaf_map[node_id]

        if node_id in self._all_node_map:
            return self._all_node_map[node_id]

        canonical = self._alias_map.get(node_id)
        if canonical:
            if canonical in self._leaf_map:
                return self._leaf_map[canonical]
            if canonical in self._all_node_map:
                return self._all_node_map[canonical]

        contains_matches = [
            path for name, path in self._all_node_map.items()
            if node_id in name or name in node_id
        ]
        if contains_matches:
            return max(contains_matches, key=len)

        return []

    def get_resource_paths(self, node_id: str) -> list[str]:
        """Return resource path list for node_id, or [] if not found / no resources."""
        return self._resource_map.get(node_id, [])
