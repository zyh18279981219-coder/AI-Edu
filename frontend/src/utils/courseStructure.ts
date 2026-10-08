import type { CourseGraphNode } from '../types/teacher';

export interface EditableCourseNode {
  name: string;
  description?: string;
  source?: CourseGraphNode;
  passthrough?: boolean;
  children?: EditableCourseNode[];
}

/** Keep stable IDs, resources, and node metadata when editing labels/topology. */
export function buildEditedCourseGraph(root: CourseGraphNode, name: string, chapters: EditableCourseNode[]): CourseGraphNode {
  const childKeys = ['children', 'grandchildren', 'great-grandchildren'] as const;
  function build(item: EditableCourseNode): CourseGraphNode[] {
    if (!item.name.trim()) throw new Error('章节、小节和知识点名称不能为空');
    const node: CourseGraphNode = JSON.parse(JSON.stringify(item.source || {}));
    node.name = item.name.trim();
    if (item.description !== undefined) node.description = item.description.trim();
    if (item.children) {
      const key = childKeys.find(k => Array.isArray(node[k])) || 'children';
      childKeys.forEach(k => { delete node[k]; });
      node[key] = item.children.flatMap(build);
    }
    return item.passthrough ? (node.children || []) : [node];
  }
  const graph: CourseGraphNode = JSON.parse(JSON.stringify(root));
  const key = childKeys.find(k => Array.isArray(graph[k])) || 'children';
  childKeys.forEach(k => { delete graph[k]; });
  graph.name = name.trim();
  graph[key] = chapters.flatMap(build);
  return graph;
}
