import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { transformSync } from 'esbuild';

const source = readFileSync(new URL('../src/utils/courseStructure.ts', import.meta.url), 'utf8');
const { code } = transformSync(source, { loader: 'ts', format: 'esm' });
const { buildEditedCourseGraph } = await import(`data:text/javascript;base64,${Buffer.from(code).toString('base64')}`);

test('renaming preserves IDs, resources, metadata and child dialect without mutating input', () => {
  const point = { node_id: 'stable-point', name: 'Old name', resource_path: ['https://example.org/a.pdf'], difficulty: 2 };
  const section = { node_id: 'stable-section', name: 'Section', 'great-grandchildren': [point] };
  const chapter = { node_id: 'stable-chapter', name: 'Chapter', grandchildren: [section] };
  const root = { name: 'Course', children: [chapter] };
  const result = buildEditedCourseGraph(root, 'Renamed course', [{ name: 'Chapter', source: chapter,
    children: [{ name: 'Section', source: section, children: [{ name: 'New name', description: 'Objective', source: point }] }] }]);
  const saved = result.children[0].grandchildren[0]['great-grandchildren'][0];
  assert.equal(saved.node_id, 'stable-point');
  assert.deepEqual(saved.resource_path, point.resource_path);
  assert.equal(saved.difficulty, 2);
  assert.equal(saved.description, 'Objective');
  assert.equal(point.name, 'Old name');
});

test('visual placeholder section does not change a direct-leaf graph topology', () => {
  const point = { name: 'Point', node_id: 'p' };
  const chapter = { name: 'Chapter', node_id: 'c', children: [point] };
  const graph = buildEditedCourseGraph({ children: [chapter] }, 'Course', [{ name: 'Chapter', source: chapter,
    children: [{ name: 'Visual section', passthrough: true, children: [{ name: 'Point', source: point }] }] }]);
  assert.equal(graph.children[0].children[0].node_id, 'p');
});

test('blank names are rejected before saving', () => {
  assert.throws(() => buildEditedCourseGraph({}, 'Course', [{ name: ' ' }]), /不能为空/);
});
