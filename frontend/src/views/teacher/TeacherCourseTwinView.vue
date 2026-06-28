<template>
  <div class="teacher-course-twin-shell">
    <section class="hero-panel app-hero app-hero--teacher">
      <div>
        <p class="eyebrow">课程数字孪生</p>
        <h1>课程底座建设台</h1>
        <p class="hero-desc">教师录入课程大纲后生成初始知识图谱，系统按叶子知识点绑定资源候选，审核通过后发布给学生端和诊断链路使用。</p>
      </div>
      <div class="course-twin-hero-actions">
        <button class="ghost-btn" type="button" :disabled="loading" @click="loadCourses">刷新</button>
        <button class="primary-btn" type="button" :disabled="!activeCourseId || loading" @click="publishCurrentCourse">
          发布课程底座
        </button>
      </div>
    </section>

    <section v-if="notice" class="card-panel state-card">{{ notice }}</section>
    <section v-if="error" class="card-panel state-card error">{{ error }}</section>

    <section class="course-twin-grid">
      <article class="card-panel course-twin-builder">
        <div class="section-heading">
          <div>
            <p class="eyebrow">Initial Graph</p>
            <h3>教师生成初始知识图谱</h3>
          </div>
          <span class="status-pill">{{ generatedSummary?.lifecycle_status || selectedSummary?.lifecycle_status || "draft" }}</span>
        </div>

        <div class="form-grid">
          <label>
            <span>课程 ID</span>
            <input v-model.trim="form.course_id" class="input" placeholder="course_big_data" />
          </label>
          <label>
            <span>课程名称</span>
            <input v-model.trim="form.course_name" class="input" placeholder="大数据分析" />
          </label>
        </div>

        <label class="outline-field">
          <span>课程大纲</span>
          <textarea v-model="form.outline_text" class="input input-textarea" rows="14" />
        </label>

        <div class="builder-options">
          <label class="checkbox-row">
            <input v-model="form.bind_resource_candidates" type="checkbox" />
            <span>生成后同时绑定资源候选</span>
          </label>
          <label class="compact-field">
            <span>每个叶子节点</span>
            <input v-model.number="form.max_resources_per_leaf" class="input" type="number" min="1" max="3" />
          </label>
        </div>

        <div class="action-row">
          <button class="primary-btn" type="button" :disabled="loading || !canGenerate" @click="generateInitialGraph">
            {{ loading ? "处理中..." : "生成并保存图谱" }}
          </button>
          <button class="ghost-btn" type="button" :disabled="loading || !activeCourseId" @click="bindResources">
            绑定资源候选
          </button>
        </div>
      </article>

      <article class="card-panel course-twin-side">
        <div class="section-heading">
          <div>
            <p class="eyebrow">Course Base</p>
            <h3>课程状态</h3>
          </div>
        </div>
        <div class="course-list">
          <button
            v-for="course in courses"
            :key="course.course_id"
            type="button"
            class="course-row"
            :class="{ active: course.course_id === activeCourseId }"
            @click="selectCourse(course.course_id)"
          >
            <span>
              <strong>{{ course.course_name }}</strong>
              <small>{{ course.course_id }}</small>
            </span>
            <em>{{ course.lifecycle_status }}</em>
          </button>
          <div v-if="!courses.length" class="muted">暂无课程底座</div>
        </div>

        <div v-if="activeSummary" class="summary-grid">
          <div><span>节点</span><strong>{{ activeSummary.node_count }}</strong></div>
          <div><span>叶子</span><strong>{{ activeSummary.leaf_node_count ?? 0 }}</strong></div>
          <div><span>资源</span><strong>{{ activeSummary.resource_count }}</strong></div>
          <div><span>启用</span><strong>{{ activeSummary.enabled_resource_count ?? 0 }}</strong></div>
        </div>
      </article>
    </section>

    <section class="course-twin-grid lower">
      <article class="card-panel">
        <div class="section-heading">
          <div>
            <p class="eyebrow">Graph Preview</p>
            <h3>知识图谱预览</h3>
          </div>
        </div>
        <div v-if="flatGraphNodes.length" class="graph-tree">
          <div
            v-for="item in flatGraphNodes"
            :key="item.key"
            class="graph-node-line"
            :style="{ marginLeft: `${item.depth * 14}px` }"
          >
            <strong>{{ item.name }}</strong>
            <span v-if="item.resourceCount">{{ item.resourceCount }} 个资源</span>
          </div>
        </div>
        <div v-else class="muted">生成或选择课程后显示图谱结构</div>
      </article>

      <article class="card-panel">
        <div class="section-heading">
          <div>
            <p class="eyebrow">Resource Review</p>
            <h3>资源绑定审核</h3>
          </div>
          <button class="ghost-btn small" type="button" :disabled="!activeCourseId || loading" @click="refreshResources">
            刷新资源
          </button>
        </div>
        <div class="resource-review-list">
          <div v-for="resource in resources" :key="resource.resource_id" class="resource-review-row">
            <div>
              <strong>{{ resource.node_name || resource.node_id }}</strong>
              <a :href="resource.resource_path" target="_blank" rel="noreferrer">{{ displayResource(resource.resource_path) }}</a>
              <span>{{ resource.resource_source }} · {{ resource.review_status }} · {{ resource.quality_status }}</span>
            </div>
            <div class="resource-actions">
              <button class="ghost-btn small" type="button" :disabled="loading" @click="setResourceEnabled(resource, true)">启用</button>
              <button class="ghost-btn small danger" type="button" :disabled="loading" @click="setResourceEnabled(resource, false)">禁用</button>
            </div>
          </div>
          <div v-if="!resources.length" class="muted">暂无资源候选</div>
        </div>
      </article>
    </section>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from "vue";
import {
  bindCourseResourceCandidates,
  fetchCourseDigitalTwin,
  fetchCourseDigitalTwinCourses,
  fetchCourseDigitalTwinResources,
  generateCourseInitialGraph,
  publishCourseDigitalTwin,
  reviewCourseDigitalTwinResource,
} from "../../api/teacher";
import type { CourseDigitalTwinResource, CourseDigitalTwinSummary, CourseGraphNode } from "../../types/teacher";

const DEFAULT_OUTLINE = `第1章 数据采集
  1.1 数据采集概述
    Flume 基础
    Kafka 数据接入
  1.2 数据预处理
    缺失值处理
    数据标准化
第2章 数据分析建模
  2.1 描述性统计
    统计指标解释
  2.2 聚类分析
    K-means 算法`;

const courses = ref<CourseDigitalTwinSummary[]>([]);
const selectedSummary = ref<CourseDigitalTwinSummary | null>(null);
const generatedSummary = ref<CourseDigitalTwinSummary | null>(null);
const graphData = ref<CourseGraphNode | null>(null);
const resources = ref<CourseDigitalTwinResource[]>([]);
const loading = ref(false);
const error = ref("");
const notice = ref("");

const form = reactive({
  course_id: "course_big_data",
  course_name: "大数据分析",
  outline_text: DEFAULT_OUTLINE,
  bind_resource_candidates: true,
  max_resources_per_leaf: 2,
});

const activeCourseId = computed(() => generatedSummary.value?.course_id || selectedSummary.value?.course_id || "");
const activeSummary = computed(() => generatedSummary.value || selectedSummary.value);
const canGenerate = computed(() => Boolean(form.course_id.trim() && form.course_name.trim() && form.outline_text.trim()));
const flatGraphNodes = computed(() => {
  const rows: Array<{ key: string; name: string; depth: number; resourceCount: number }> = [];
  function walk(node: CourseGraphNode, depth: number) {
    const resources = Array.isArray(node.resource_path)
      ? node.resource_path
      : node.resource_path
        ? [node.resource_path]
        : [];
    rows.push({
      key: `${depth}-${nodeKey(node)}-${rows.length}`,
      name: String(node.name || "未命名节点"),
      depth,
      resourceCount: resources.length,
    });
    childrenOf(node).forEach((child) => walk(child, depth + 1));
  }
  childrenOf(graphData.value).forEach((node) => walk(node, 0));
  return rows;
});

function childrenOf(node: CourseGraphNode | null | undefined): CourseGraphNode[] {
  if (!node) return [];
  return node.children || node.grandchildren || node["great-grandchildren"] || [];
}

function nodeKey(node: CourseGraphNode) {
  return String(node.node_id || node.id || node.name || Math.random());
}

function displayResource(path: string) {
  try {
    const url = new URL(path);
    return `${url.hostname}${url.pathname}`.slice(0, 88);
  } catch {
    return path.slice(0, 88);
  }
}

function setBusyMessage(message = "") {
  error.value = "";
  notice.value = message;
}

async function loadCourses() {
  loading.value = true;
  setBusyMessage();
  try {
    const data = await fetchCourseDigitalTwinCourses();
    courses.value = data.courses || [];
    if (!selectedSummary.value && courses.value.length) {
      await selectCourse(courses.value[0].course_id);
    }
  } catch (err) {
    error.value = err instanceof Error ? err.message : "课程列表加载失败";
  } finally {
    loading.value = false;
  }
}

async function selectCourse(courseId: string) {
  if (!courseId) return;
  loading.value = true;
  setBusyMessage();
  try {
    const data = await fetchCourseDigitalTwin(courseId);
    selectedSummary.value = data.summary;
    generatedSummary.value = null;
    graphData.value = data.graph_data as CourseGraphNode;
    form.course_id = data.summary.course_id;
    form.course_name = data.summary.course_name;
    await loadResources(courseId);
  } catch (err) {
    error.value = err instanceof Error ? err.message : "课程详情加载失败";
  } finally {
    loading.value = false;
  }
}

async function generateInitialGraph() {
  loading.value = true;
  setBusyMessage("正在生成课程图谱...");
  try {
    const data = await generateCourseInitialGraph({
      course_id: form.course_id,
      course_name: form.course_name,
      outline_text: form.outline_text,
      lifecycle_status: "draft",
      bind_resource_candidates: form.bind_resource_candidates,
      max_resources_per_leaf: form.max_resources_per_leaf,
    });
    generatedSummary.value = data.summary;
    selectedSummary.value = data.summary;
    graphData.value = data.graph_data;
    notice.value = `已生成 ${data.validation.node_count} 个节点、${data.validation.leaf_node_count} 个叶子知识点`;
    await loadResources(data.course_id);
    await refreshCourseListOnly();
  } catch (err) {
    error.value = err instanceof Error ? err.message : "初始图谱生成失败";
    notice.value = "";
  } finally {
    loading.value = false;
  }
}

async function bindResources() {
  const courseId = activeCourseId.value;
  if (!courseId) return;
  loading.value = true;
  setBusyMessage("正在绑定资源候选...");
  try {
    const data = await bindCourseResourceCandidates({
      course_id: courseId,
      max_resources_per_leaf: form.max_resources_per_leaf,
      overwrite: false,
      review_status: "pending",
    });
    generatedSummary.value = data.summary;
    selectedSummary.value = data.summary;
    graphData.value = data.graph_data;
    resources.value = data.resources;
    notice.value = `已新增 ${data.bind_result.attached_resources} 条资源候选，${data.review_marked_count} 条进入审核`;
    await refreshCourseListOnly();
  } catch (err) {
    error.value = err instanceof Error ? err.message : "资源候选绑定失败";
    notice.value = "";
  } finally {
    loading.value = false;
  }
}

async function loadResources(courseId: string) {
  if (!courseId) return;
  const data = await fetchCourseDigitalTwinResources(courseId);
  resources.value = data.resources || [];
}

async function refreshResources() {
  const courseId = activeCourseId.value;
  if (!courseId) return;
  loading.value = true;
  setBusyMessage();
  try {
    await loadResources(courseId);
    notice.value = "资源清单已刷新";
  } catch (err) {
    error.value = err instanceof Error ? err.message : "资源清单刷新失败";
  } finally {
    loading.value = false;
  }
}

async function refreshCourseListOnly() {
  const data = await fetchCourseDigitalTwinCourses();
  courses.value = data.courses || [];
}

async function setResourceEnabled(resource: CourseDigitalTwinResource, enabled: boolean) {
  loading.value = true;
  setBusyMessage();
  try {
    const data = await reviewCourseDigitalTwinResource({
      course_id: resource.course_id,
      node_id: resource.node_id,
      resource_path: resource.resource_path,
      is_enabled: enabled,
      review_status: enabled ? "enabled" : "disabled",
      quality_status: enabled ? "passed" : "candidate",
    });
    selectedSummary.value = data.summary;
    generatedSummary.value = data.summary;
    await loadResources(resource.course_id);
    notice.value = enabled ? "资源已启用" : "资源已禁用";
  } catch (err) {
    error.value = err instanceof Error ? err.message : "资源审核失败";
  } finally {
    loading.value = false;
  }
}

async function publishCurrentCourse() {
  const courseId = activeCourseId.value;
  if (!courseId) return;
  loading.value = true;
  setBusyMessage("正在发布课程底座...");
  try {
    const data = await publishCourseDigitalTwin(courseId);
    selectedSummary.value = data.summary;
    generatedSummary.value = data.summary;
    notice.value = "课程底座已发布";
    await refreshCourseListOnly();
  } catch (err) {
    error.value = err instanceof Error ? err.message : "课程发布失败";
    notice.value = "";
  } finally {
    loading.value = false;
  }
}

onMounted(loadCourses);
</script>

<style scoped>
.teacher-course-twin-shell {
  display: flex;
  flex-direction: column;
  gap: 18px;
}

.course-twin-hero-actions,
.action-row,
.builder-options,
.resource-actions {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}

.course-twin-grid {
  display: grid;
  grid-template-columns: minmax(0, 1.35fr) minmax(320px, 0.65fr);
  gap: 18px;
  align-items: start;
}

.course-twin-grid.lower {
  grid-template-columns: minmax(0, 0.9fr) minmax(0, 1.1fr);
}

.section-heading {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  align-items: flex-start;
  margin-bottom: 14px;
}

.section-heading h3 {
  margin: 2px 0 0;
}

.form-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
}

.form-grid label,
.outline-field,
.compact-field {
  display: flex;
  flex-direction: column;
  gap: 6px;
  color: #4b5563;
  font-size: 13px;
}

.outline-field {
  margin-top: 12px;
}

.builder-options {
  justify-content: space-between;
  margin: 12px 0;
}

.checkbox-row {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  color: #374151;
}

.compact-field {
  width: 128px;
}

.status-pill {
  border: 1px solid #bfdbfe;
  border-radius: 999px;
  padding: 4px 10px;
  color: #1d4ed8;
  background: #eff6ff;
  font-size: 12px;
  font-style: normal;
}

.course-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
  max-height: 290px;
  overflow: auto;
}

.course-row {
  border: 1px solid #e5e7eb;
  background: #fff;
  border-radius: 8px;
  padding: 10px;
  display: flex;
  justify-content: space-between;
  gap: 10px;
  text-align: left;
  cursor: pointer;
}

.course-row.active {
  border-color: #2563eb;
  background: #eff6ff;
}

.course-row span,
.resource-review-row div:first-child {
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 3px;
}

.course-row small,
.course-row em,
.resource-review-row span,
.muted {
  color: #6b7280;
  font-size: 12px;
}

.summary-grid {
  margin-top: 14px;
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 10px;
}

.summary-grid div {
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  padding: 10px;
}

.summary-grid span {
  display: block;
  color: #6b7280;
  font-size: 12px;
}

.summary-grid strong {
  font-size: 22px;
  color: #111827;
}

.graph-tree,
.resource-review-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
  max-height: 520px;
  overflow: auto;
}

.graph-node-line {
  min-height: 34px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  padding: 7px 9px;
  background: #fff;
}

.graph-node-line span {
  color: #2563eb;
  font-size: 12px;
  white-space: nowrap;
}

.resource-review-row {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  gap: 12px;
  align-items: center;
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  padding: 10px;
}

.resource-review-row a {
  color: #2563eb;
  text-decoration: none;
  overflow-wrap: anywhere;
}

.danger {
  color: #b91c1c;
}

@media (max-width: 980px) {
  .course-twin-grid,
  .course-twin-grid.lower,
  .form-grid {
    grid-template-columns: 1fr;
  }

  .resource-review-row {
    grid-template-columns: 1fr;
  }
}
</style>
