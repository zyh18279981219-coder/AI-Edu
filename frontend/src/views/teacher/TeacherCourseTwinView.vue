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

        <div class="tree-editor">
          <div class="tree-editor-head">
            <div>
              <span class="field-label">课程结构</span>
              <p>按章节、小节、知识点维护课程树；资源候选只会绑定到叶子知识点。</p>
            </div>
            <button class="tree-add-root" type="button" :disabled="loading" @click="addChapter">
              <Plus />
              <span>添加章节</span>
            </button>
          </div>

          <div class="course-tree-form">
            <div v-for="(chapter, chapterIndex) in treeForm" :key="chapter.id" class="tree-node tree-node--chapter">
              <div class="tree-row tree-row--chapter">
                <button class="tree-toggle" type="button" :aria-label="chapter.collapsed ? '展开章节' : '收起章节'" @click="chapter.collapsed = !chapter.collapsed">
                  <ArrowRight v-if="chapter.collapsed" />
                  <ArrowDown v-else />
                </button>
                <span class="tree-type tree-type--chapter">章</span>
                <span class="tree-index">第 {{ chapterIndex + 1 }} 章</span>
                <input v-model.trim="chapter.name" class="tree-input" placeholder="输入章节名称，如 数据采集" />
                <div class="tree-actions">
                  <button class="tree-icon-btn" type="button" title="添加小节" aria-label="添加小节" :disabled="loading" @click="addSection(chapter)">
                    <Plus />
                  </button>
                  <button class="tree-icon-btn danger" type="button" title="删除章节" aria-label="删除章节" :disabled="loading || treeForm.length <= 1" @click="removeChapter(chapterIndex)">
                    <Delete />
                  </button>
                </div>
              </div>

              <div v-if="!chapter.collapsed" class="tree-children">
                <div v-for="(section, sectionIndex) in chapter.children" :key="section.id" class="tree-node tree-node--section">
                  <div class="tree-row tree-row--section">
                    <button class="tree-toggle" type="button" :aria-label="section.collapsed ? '展开小节' : '收起小节'" @click="section.collapsed = !section.collapsed">
                      <ArrowRight v-if="section.collapsed" />
                      <ArrowDown v-else />
                    </button>
                    <span class="tree-type tree-type--section">节</span>
                    <span class="tree-index">{{ chapterIndex + 1 }}.{{ sectionIndex + 1 }}</span>
                    <input v-model.trim="section.name" class="tree-input" placeholder="输入小节名称，如 数据采集概述" />
                    <div class="tree-actions">
                      <button class="tree-icon-btn" type="button" title="添加知识点" aria-label="添加知识点" :disabled="loading" @click="addKnowledgePoint(section)">
                        <Plus />
                      </button>
                      <button class="tree-icon-btn danger" type="button" title="删除小节" aria-label="删除小节" :disabled="loading || chapter.children.length <= 1" @click="removeSection(chapter, sectionIndex)">
                        <Delete />
                      </button>
                    </div>
                  </div>

                  <div v-if="!section.collapsed" class="tree-leaves">
                    <div v-for="(point, pointIndex) in section.children" :key="point.id" class="tree-node tree-node--leaf">
                      <span class="tree-leaf-rail"></span>
                      <span class="tree-type tree-type--point">点</span>
                      <span class="tree-index">{{ chapterIndex + 1 }}.{{ sectionIndex + 1 }}.{{ pointIndex + 1 }}</span>
                      <input v-model.trim="point.name" class="tree-input" placeholder="输入知识点名称，如 Flume 基础" />
                      <div class="tree-actions">
                        <button class="tree-icon-btn danger" type="button" title="删除知识点" aria-label="删除知识点" :disabled="loading || section.children.length <= 1" @click="removeKnowledgePoint(section, pointIndex)">
                          <Delete />
                        </button>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>

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
import { ArrowDown, ArrowRight, Delete, Plus } from "@element-plus/icons-vue";
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


type KnowledgePointFormNode = {
  id: string;
  name: string;
};

type SectionFormNode = {
  id: string;
  name: string;
  collapsed: boolean;
  children: KnowledgePointFormNode[];
};

type ChapterFormNode = {
  id: string;
  name: string;
  collapsed: boolean;
  children: SectionFormNode[];
};

const courses = ref<CourseDigitalTwinSummary[]>([]);
const selectedSummary = ref<CourseDigitalTwinSummary | null>(null);
const generatedSummary = ref<CourseDigitalTwinSummary | null>(null);
const graphData = ref<CourseGraphNode | null>(null);
const resources = ref<CourseDigitalTwinResource[]>([]);
const loading = ref(false);
const error = ref("");
const notice = ref("");
const treeForm = ref<ChapterFormNode[]>([
  createChapter("数据采集", [
    createSection("数据采集概述", ["Flume 基础", "Kafka 数据接入"])
  ])
]);

const form = reactive({
  course_id: "course_big_data",
  course_name: "大数据分析",
  outline_text: "",
  bind_resource_candidates: true,
  max_resources_per_leaf: 2,
});

const activeCourseId = computed(() => generatedSummary.value?.course_id || selectedSummary.value?.course_id || "");
const activeSummary = computed(() => generatedSummary.value || selectedSummary.value);
const outlineText = computed(() => serializeTreeForm());
const canGenerate = computed(() => Boolean(form.course_id.trim() && form.course_name.trim() && outlineText.value.trim()));
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

function createId(prefix: string) {
  return `${prefix}_${Date.now().toString(36)}_${Math.random().toString(36).slice(2, 8)}`;
}

function createPoint(name = ""): KnowledgePointFormNode {
  return { id: createId("point"), name };
}

function createSection(name = "", points: string[] = [""]): SectionFormNode {
  return {
    id: createId("section"),
    name,
    collapsed: false,
    children: points.length ? points.map((item) => createPoint(item)) : [createPoint()],
  };
}

function createChapter(name = "", sections: SectionFormNode[] = [createSection()]): ChapterFormNode {
  return {
    id: createId("chapter"),
    name,
    collapsed: false,
    children: sections.length ? sections : [createSection()],
  };
}

function addChapter() {
  treeForm.value.push(createChapter());
}

function removeChapter(index: number) {
  if (treeForm.value.length <= 1) return;
  treeForm.value.splice(index, 1);
}

function addSection(chapter: ChapterFormNode) {
  chapter.children.push(createSection());
  chapter.collapsed = false;
}

function removeSection(chapter: ChapterFormNode, index: number) {
  if (chapter.children.length <= 1) return;
  chapter.children.splice(index, 1);
}

function addKnowledgePoint(section: SectionFormNode) {
  section.children.push(createPoint());
  section.collapsed = false;
}

function removeKnowledgePoint(section: SectionFormNode, index: number) {
  if (section.children.length <= 1) return;
  section.children.splice(index, 1);
}

function serializeTreeForm() {
  const lines: string[] = [];
  treeForm.value.forEach((chapter, chapterIndex) => {
    const chapterName = chapter.name.trim();
    if (!chapterName) return;
    lines.push(`第${chapterIndex + 1}章 ${chapterName}`);
    chapter.children.forEach((section, sectionIndex) => {
      const sectionName = section.name.trim();
      if (!sectionName) return;
      lines.push(`  ${chapterIndex + 1}.${sectionIndex + 1} ${sectionName}`);
      section.children.forEach((point) => {
        const pointName = point.name.trim();
        if (pointName) lines.push(`    ${pointName}`);
      });
    });
  });
  return lines.join("\n");
}

function buildOutlineText() {
  form.outline_text = serializeTreeForm();
  return form.outline_text;
}


function graphToTree(node: CourseGraphNode | null): ChapterFormNode[] {
  const chapters = childrenOf(node).map((chapter) => {
    const chapterChildren = childrenOf(chapter);
    const isLeaves = chapterChildren.length > 0 && chapterChildren.every(c => childrenOf(c).length === 0);
    
    let sections;
    if (isLeaves) {
      sections = [createSection("默认小节", chapterChildren.map(p => String(p.name || "")))];
    } else {
      sections = chapterChildren.map((section) => {
        const sectionChildren = childrenOf(section);
        if (sectionChildren.length === 0) {
          return createSection(String(section.name || ""), [String(section.name || "")]);
        }
        const points = sectionChildren.map((point) => createPoint(String(point.name || "")));
        return createSection(String(section.name || ""), points.map((point) => point.name));
      });
    }
    return createChapter(String(chapter.name || ""), sections);
  });
  return normalizeTree(chapters);
}

function normalizeTree(chapters: ChapterFormNode[]) {
  const normalized = chapters.length ? chapters : [createChapter("数据采集")];
  normalized.forEach((chapter) => {
    if (!chapter.children.length) chapter.children.push(createSection("知识点小节", ["核心知识点"]));
    chapter.children.forEach((section) => {
      if (!section.children.length) section.children.push(createPoint("核心知识点"));
    });
  });
  return normalized;
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
    treeForm.value = graphToTree(graphData.value);
    buildOutlineText();
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
      outline_text: buildOutlineText(),
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
  grid-template-columns: minmax(0, 1fr) 420px;
  gap: 24px;
  align-items: start;
}

.course-twin-grid.lower {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 420px;
  gap: 24px;
  align-items: start;
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
.compact-field {
  display: flex;
  flex-direction: column;
  gap: 6px;
  color: #4b5563;
  font-size: 13px;
}

.builder-options {
  justify-content: space-between;
  margin: 12px 0;
}

.tree-editor {
  margin-top: 14px;
  border: none;
  border-radius: 12px;
  background:
    linear-gradient(90deg, rgba(37, 99, 235, 0.04) 0 1px, transparent 1px 100%) 34px 0 / 28px 100%,
    #f8fbff;
  box-shadow: inset 0 2px 10px rgba(15, 23, 42, 0.02), 0 0 0 1px rgba(219, 228, 240, 0.6);
  overflow: hidden;
}

.tree-editor-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
  padding: 13px 14px;
  border-bottom: 1px solid rgba(219, 228, 240, 0.6);
  background: #ffffff;
}

.tree-editor-head p {
  margin: 3px 0 0;
  color: #64748b;
  font-size: 12px;
}

.field-label {
  display: block;
  color: #1f2937;
  font-size: 13px;
  font-weight: 800;
}

.tree-add-root {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  min-height: 32px;
  border: 1px solid #bfdbfe;
  border-radius: 7px;
  padding: 0 10px;
  color: #1d4ed8;
  background: #eff6ff;
  font-size: 12px;
  font-weight: 800;
  white-space: nowrap;
  cursor: pointer;
  transition: all 0.2s;
}

.tree-add-root:hover {
  background: #dbeafe;
}

.tree-add-root svg,
.tree-toggle svg,
.tree-icon-btn svg {
  width: 14px;
  height: 14px;
}

.course-tree-form {
  display: flex;
  flex-direction: column;
  gap: 12px;
  max-height: 430px;
  overflow: auto;
  padding: 16px;
}

.tree-node {
  position: relative;
  min-width: 500px;
}

.tree-row {
  display: grid;
  grid-template-columns: 28px 34px 76px minmax(100px, 1fr) auto;
  gap: 8px;
  align-items: center;
  min-height: 46px;
  border: 1px solid rgba(220, 230, 242, 0.6);
  border-radius: 10px;
  padding: 7px 10px;
  background: rgba(255, 255, 255, 0.94);
  box-shadow: 0 4px 12px rgba(15, 23, 42, 0.02);
  transition: all 0.2s ease;
}

.tree-row:hover {
  box-shadow: 0 6px 16px rgba(15, 23, 42, 0.06);
  border-color: rgba(191, 219, 254, 0.8);
}

.tree-row--chapter {
  border-color: #bfdbfe;
  background: #ffffff;
}

.tree-row--section {
  grid-template-columns: 28px 34px 58px minmax(100px, 1fr) auto;
  background: #fbfdff;
}

.tree-node--leaf {
  display: grid;
  grid-template-columns: 28px 34px 76px minmax(100px, 1fr) auto;
  gap: 8px;
  align-items: center;
  min-height: 42px;
  border: 1px solid rgba(225, 232, 240, 0.6);
  border-radius: 10px;
  padding: 7px 10px;
  background: #ffffff;
  transition: all 0.2s ease;
}

.tree-node--leaf:hover {
  box-shadow: 0 4px 12px rgba(15, 23, 42, 0.04);
  border-color: rgba(191, 219, 254, 0.5);
}

.tree-children,
.tree-leaves {
  display: flex;
  flex-direction: column;
  gap: 8px;
  margin-left: 34px;
  padding: 8px 0 0 18px;
  border-left: 2px solid #dbeafe;
}

.tree-leaves {
  margin-left: 32px;
  border-left-color: #dcfce7;
}

.tree-leaf-rail {
  justify-self: center;
  width: 9px;
  height: 9px;
  border-radius: 99px;
  background: #16a34a;
  box-shadow: 0 0 0 4px #dcfce7;
}

.tree-toggle,
.tree-icon-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border: none; box-shadow: 0 4px 12px rgba(0,0,0,0.03); padding: 16px;
  border-radius: 7px;
  background: #fff;
  color: #334155;
  width: 30px;
  height: 30px;
  font-size: 12px;
  font-weight: 800;
  cursor: pointer;
}

.tree-toggle {
  width: 28px;
  height: 28px;
  padding: 0;
  color: #2563eb;
}

.tree-actions {
  display: inline-flex;
  align-items: center;
  justify-content: flex-end;
  gap: 6px;
}

.tree-toggle:disabled,
.tree-icon-btn:disabled,
.tree-add-root:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.tree-type {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 30px;
  height: 24px;
  border-radius: 999px;
  font-size: 12px;
  font-weight: 900;
}

.tree-type--chapter {
  color: #1d4ed8;
  background: #dbeafe;
}

.tree-type--section {
  color: #0f766e;
  background: #ccfbf1;
}

.tree-type--point {
  color: #15803d;
  background: #dcfce7;
}

.tree-index {
  color: #64748b;
  font-size: 12px;
  font-weight: 800;
  white-space: nowrap;
}

.tree-input {
  width: 100%;
  min-width: 0;
  height: 34px;
  border: 1px solid transparent;
  border-radius: 6px;
  padding: 0 8px;
  color: #111827;
  font: inherit;
  font-weight: 700;
  background: transparent;
}

.tree-input:hover {
  border-color: #dbe4f0;
  background: #fff;
}

.tree-input:focus {
  outline: none;
  border-color: #2563eb;
  background: #fff;
  box-shadow: 0 0 0 3px rgba(37, 99, 235, 0.12);
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
  border: none; box-shadow: 0 4px 12px rgba(0,0,0,0.03); padding: 16px;
  background: #fff;
  border-radius: 12px;
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
  border: none; box-shadow: 0 4px 12px rgba(0,0,0,0.03); padding: 16px;
  border-radius: 12px;
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
  border: none; box-shadow: 0 4px 12px rgba(0,0,0,0.03); padding: 16px;
  border-radius: 12px;
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
  border: none; box-shadow: 0 4px 12px rgba(0,0,0,0.03); padding: 16px;
  border-radius: 12px;
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

  .tree-row,
  .tree-row--section,
  .tree-node--leaf {
    grid-template-columns: 28px 32px minmax(54px, auto) minmax(0, 1fr);
  }

  .tree-actions {
    grid-column: 1 / -1;
    justify-content: flex-end;
  }
}
</style>
