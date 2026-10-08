import copy
import threading
from contextlib import contextmanager

import pytest
from fastapi.testclient import TestClient

from DatabaseModule.course_resources import assign_node_ids, graph_children, hydrate_resource_graph, resource_is_enabled


class CourseStore:
    def __init__(self):
        self.courses = {}
        self.resources = []

    def get_course_summary(self, course_id):
        if course_id not in self.courses:
            return None
        graph, status = self.courses[course_id]
        resources = self.list_course_resources(course_id)
        return dict(course_id=course_id, course_name=graph['name'], lifecycle_status=status,
                    leaf_node_count=2, resource_count=len(resources),
                    enabled_resource_count=sum(resource_is_enabled(item) for item in resources))

    def get_course_payload(self, course_id):
        row = self.courses.get(course_id)
        return copy.deepcopy(row[0]) if row else None

    def list_course_resources(self, course_id):
        return copy.deepcopy([item for item in self.resources if item['course_id'] == course_id])

    def sync_course_from_graph(self, course_id, graph_data, *, lifecycle_status, **kwargs):
        assign_node_ids(graph_data)
        self.courses[course_id] = copy.deepcopy(graph_data), lifecycle_status
        def walk(node):
            for path in node.get('resource_path', []):
                if not any(item['course_id'] == course_id and item['node_id'] == node['node_id'] and item['resource_path'] == path for item in self.resources):
                    self.resources.append(dict(resource_id=len(self.resources)+1, course_id=course_id,
                        node_id=node['node_id'], node_name=node['name'], resource_path=path,
                        review_status='enabled', is_enabled=True, is_deleted=False))
            for child in graph_children(node):
                walk(child)
        for child in graph_children(graph_data):
            walk(child)
        return {'nodes': 5, 'resources': len(self.list_course_resources(course_id))}

    def set_resource_review_status(self, course_id, node_id, resource_path, **kwargs):
        for item in self.resources:
            if (item['course_id'], item['node_id'], item['resource_path']) == (course_id, node_id, resource_path):
                item.update(kwargs)
                return True
        return False

    def publish_course(self, course_id, **kwargs):
        graph, _ = self.courses[course_id]
        self.courses[course_id] = graph, 'published'
        return True

    def list_student_courses(self, username):
        return [self.get_course_summary(key) for key in self.courses if self.courses[key][1] == 'published']


@pytest.fixture
def workflow(monkeypatch):
    import app as api
    store = CourseStore()
    monkeypatch.setattr(api, 'database_store', store)
    monkeypatch.setattr(api, '_require_teacher_or_admin', lambda _: {'username': 'teacher', 'user_type': 'teacher'})
    monkeypatch.setattr(api, 'get_current_user', lambda _: {'username': 'student', 'user_type': 'student'})
    monkeypatch.setattr(api, '_resource_candidates_for_node', lambda name, count: ['https://example.org/lesson.pdf', 'https://example.org/lesson2.pdf'][:count])
    api._clear_course_cache_for_course('test_resource_course')
    return api, store, TestClient(api.app)


def create(client, auto_bind=False):
    return client.post('/api/course-digital-twin/initial-graph', json={
        'course_id': 'test_resource_course', 'course_name': 'Independent test course',
        'outline_text': '第1章 第一章\n  1.1 第一节\n    相同知识点\n第2章 第二章\n  2.1 第二节\n    相同知识点',
        'bind_resource_candidates': auto_bind, 'max_resources_per_leaf': 2})


def test_create_bind_review_publish_disable_cycle(workflow):
    api, store, client = workflow
    course_id = 'test_resource_course'
    result = create(client)
    assert result.status_code == 200
    assert result.json()['summary']['lifecycle_status'] == 'draft'
    assert create(client).status_code == 409
    assert client.get('/api/knowledge-graph', params={'course_id': course_id}).status_code == 404
    bind = client.post('/api/course-digital-twin/resource-candidates/bind', json={'course_id': course_id, 'max_resources_per_leaf': 2})
    assert bind.status_code == 200
    assert bind.json()['review_marked_count'] == 4
    rows = bind.json()['resources']
    assert len({row['node_id'] for row in rows}) == 2
    assert all(row['review_status'] == 'pending' and not row['is_enabled'] for row in rows)
    resource = rows[0]
    review = {key: resource[key] for key in ('course_id', 'node_id', 'resource_path')}
    assert client.post('/api/course-digital-twin/resource-review', json={**review, 'is_enabled': True, 'review_status': 'enabled'}).status_code == 200
    assert client.post('/api/course-digital-twin/publish', json={'course_id': course_id}).status_code == 200
    assert len(client.get('/api/student/courses').json()['courses']) == 1
    graph = client.get('/api/knowledge-graph', params={'course_id': course_id}).json()
    assert [leaf['resource_path'] for leaf in api._leaf_graph_nodes(graph)] == [[resource['resource_path']], []]
    rebound = client.post('/api/course-digital-twin/resource-candidates/bind', json={'course_id': course_id, 'max_resources_per_leaf': 2}).json()
    assert rebound['bind_result']['attached_resources'] == 0
    assert rebound['sync_result'] == {'nodes': 0, 'resources': 0}
    assert rebound['review_marked_count'] == 0
    assert rebound['summary']['enabled_resource_count'] == 1
    assert client.post('/api/course-digital-twin/resource-review', json={**review, 'is_enabled': False, 'review_status': 'disabled'}).status_code == 200
    graph = client.get('/api/knowledge-graph', params={'course_id': course_id}).json()
    assert all(not leaf['resource_path'] for leaf in api._leaf_graph_nodes(graph))
    assert client.post('/api/course-digital-twin/resource-review', json={**review, 'is_enabled': True, 'review_status': 'enabled'}).status_code == 200
    assert client.get('/api/course-digital-twin/' + course_id).json()['summary']['enabled_resource_count'] == 1


def test_auto_binding_creates_pending_not_enabled(workflow):
    _, _, client = workflow
    result = create(client, auto_bind=True).json()
    assert result['review_marked_count'] == 4
    assert result['summary']['enabled_resource_count'] == 0


def test_create_preserves_descriptions_for_repeated_point_names(workflow):
    import json
    _, _, client = workflow
    paths = [['第一章', '第一节', '相同知识点'], ['第二章', '第二节', '相同知识点']]
    result = client.post('/api/course-digital-twin/initial-graph', json={
        'course_id': 'description_test', 'course_name': 'Course',
        'outline_text': '第1章 第一章\n  1.1 第一节\n    相同知识点\n第2章 第二章\n  2.1 第二节\n    相同知识点',
        'node_descriptions': {json.dumps(path, ensure_ascii=False, separators=(',', ':')): text
                              for path, text in zip(paths, ['First objective', 'Second objective'])},
    })
    assert result.status_code == 200
    graph = result.json()['graph_data']
    assert [c['grandchildren'][0]['great-grandchildren'][0]['description'] for c in graph['children']] == ['First objective', 'Second objective']


def test_manual_binding_validation_and_duplicate(workflow):
    api, _, client = workflow
    result = create(client).json()
    node_id = api._leaf_graph_nodes(result['graph_data'])[0]['node_id']
    request = {'course_id': 'test_resource_course', 'node_id': node_id, 'resource_path': 'https://example.org/manual.pdf'}
    assert client.post('/api/course-digital-twin/resources/add', json={**request, 'node_id': 'wrong-node'}).status_code == 400
    assert client.post('/api/course-digital-twin/resources/add', json={**request, 'resource_path': 'https://so.csdn.net/so/search?q=x'}).status_code == 400
    assert client.post('/api/course-digital-twin/resources/add', json={**request, 'resource_path': 'data/nonexistent.pdf'}).status_code == 400
    assert client.post('/api/course-digital-twin/resources/add', json={**request, 'resource_path': 'javascript:alert(1)'}).status_code == 400
    result = client.post('/api/course-digital-twin/resources/add', json=request)
    assert result.status_code == 200
    assert result.json()['resources'][0]['review_status'] == 'pending'
    assert client.post('/api/course-digital-twin/resources/add', json=request).status_code == 409


def test_disabled_pending_and_deleted_rows_do_not_fall_back_to_stale_graph():
    graph = {'name': 'course', 'children': [{'name': 'node', 'resource_path': ['stale.pdf']}]}
    rows = [dict(node_id='node', resource_path=f'{status}.pdf', review_status=status, is_enabled=True, is_deleted=False)
            for status in ('pending', 'disabled', 'enabled')]
    rows.append(dict(node_id='node', resource_path='deleted.pdf', review_status='enabled', is_enabled=True, is_deleted=True))
    assert hydrate_resource_graph(graph, rows)['children'][0]['resource_path'] == ['enabled.pdf']
    assert hydrate_resource_graph(graph, [])['children'][0]['resource_path'] == []
    assert graph['children'][0]['resource_path'] == ['stale.pdf']


def test_mysql_review_rejects_inconsistent_enable_flag():
    from DatabaseModule.mysql_store import MySQLStore
    calls = []
    class Cursor:
        rowcount = 1
        def __enter__(self): return self
        def __exit__(self, *_): pass
        def execute(self, sql, params): calls.append((sql, params))
    class Connection:
        def cursor(self): return Cursor()
    @contextmanager
    def connection(): yield Connection()
    store = MySQLStore.__new__(MySQLStore)
    store._lock = threading.RLock()
    store.connection = connection
    assert store.set_resource_review_status('course', 'node', 'resource', is_enabled=True, review_status='pending')
    assert calls[0][1][0] == 0
    assert 'is_deleted = 0' in calls[0][0]
