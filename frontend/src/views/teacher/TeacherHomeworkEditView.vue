<template>
  <div class="homework-edit-shell">
    <section class="card-panel">
      <div class="section-head">
        <h3>{{ isEdit ? "编辑作业" : "新建作业" }}</h3>
        <div class="actions-row">
          <button class="ghost-btn" type="button" @click="router.push({ name: 'teacher-homework' })">返回列表</button>
        </div>
      </div>

      <div class="form-grid">
        <label>
          作业标题
          <input v-model="form.title" class="input" type="text" />
        </label>
        <label>
          班级
          <select v-model="form.class_name" class="input">
            <option value="">未指定班级</option>
            <option v-for="className in classOptions" :key="className" :value="className">{{ className }}</option>
          </select>
        </label>
        <label>
          课程ID
          <select v-model="form.course_id" class="input">
            <option v-for="courseId in courseOptions" :key="courseId" :value="courseId">{{ courseId }}</option>
          </select>
        </label>
        <label>
          关联章节
          <select v-model="selectedNodeId" class="input" @change="onNodeSelected">
            <option value="">不关联章节</option>
            <option v-for="node in courseNodes" :key="node.node_id" :value="node.node_id">
              {{ node.node_path.join(" > ") }}
            </option>
          </select>
        </label>
        <label>
          作业类型
          <select v-model="form.assignment_type" class="input">
            <option value="subjective">主观题</option>
            <option value="objective">客观题（判断）</option>
            <option value="choice">选择题（单/多选）</option>
            <option value="code">代码实践</option>
          </select>
        </label>
        <label v-if="form.assignment_type === 'objective' || form.assignment_type === 'choice'">
          判题结果展示
          <select v-model="form.objective_result_mode" class="input">
            <option value="immediate">学生提交后自动判题并显示结果（默认）</option>
            <option value="manual_review">教师批改后再显示结果</option>
          </select>
        </label>
        <label>
          截止时间
          <input v-model="form.due_at" class="input" type="datetime-local" />
        </label>
        <label>
          满分
          <input v-model.number="form.total_score" class="input" type="number" min="0" step="0.1" />
        </label>
        <label class="checkbox-line">
          <input v-model="form.allow_late" type="checkbox" />
          允许逾期提交
        </label>
      </div>

      <label class="full-width">
        作业简介
        <textarea v-model="form.description" class="input input-textarea" rows="3" />
      </label>

      <label class="full-width">
        评分标准
        <textarea v-model="form.rubric" class="input input-textarea" rows="3" />
      </label>
      <label class="full-width">
        章节上下文（用于AI出题）
        <textarea
          v-model="form.chapter_context"
          class="input input-textarea"
          rows="3"
          placeholder="可粘贴本章节重点、教学要求、能力目标等"
        />
      </label>

      <section class="coverage-panel full-width">
        <div class="coverage-head">
          <div>
            <strong>教师确认覆盖知识点</strong>
            <p>不勾选时，本作业只作为章节综合实践能力证据；勾选后，结果才会作为对应叶子知识点的辅助证据。</p>
          </div>
          <button class="ghost-btn small" type="button" :disabled="!selectedNodeId" @click="selectRelatedLeafCoverage">
            选中关联章节下叶子点
          </button>
        </div>
        <div class="coverage-grid">
          <label v-for="node in leafCourseNodes" :key="node.node_id" class="coverage-option">
            <input v-model="selectedCoverageNodeIds" type="checkbox" :value="node.node_id" />
            <span>{{ node.node_path.join(" > ") }}</span>
          </label>
        </div>
        <div v-if="!leafCourseNodes.length" class="muted">当前课程暂无可确认的叶子知识点。</div>
      </section>

      <div class="section-head section-gap">
        <h3>题目列表</h3>
        <button class="ghost-btn" type="button" @click="addQuestion">新增题目</button>
      </div>

      <div class="question-card" v-for="(q, idx) in form.questions" :key="idx">
        <div class="section-head compact">
          <strong>题目 {{ idx + 1 }}</strong>
          <button class="ghost-btn small" type="button" @click="removeQuestion(idx)">删除</button>
        </div>
        <label class="full-width">
          题目标题
          <input v-model="q.title" class="input" type="text" />
        </label>
        <label class="full-width">
          题目要求
          <textarea v-model="q.prompt" class="input input-textarea" rows="4" />
        </label>
        <template v-if="form.assignment_type === 'objective' || form.assignment_type === 'choice'">
          <label class="full-width">
            选项（每行一个，如：A. xxx）
            <textarea
              class="input input-textarea"
              rows="4"
              :value="(q.options || []).join('\n')"
              @input="updateQuestionOptions(idx, ($event.target as HTMLTextAreaElement).value)"
            />
          </label>
          <label class="full-width">
            标准答案（如：A 或 A,C）
            <input v-model="q.correct_answer" class="input" type="text" />
          </label>
        </template>
        <template v-if="form.assignment_type === 'code'">
          <div class="full-width testcase-panel">
            <div class="section-head compact testcase-head">
              <strong>测试点编辑器</strong>
              <button class="ghost-btn small" type="button" @click="addTestCase(idx)">新增测试点</button>
            </div>
            <div v-if="!(q.test_cases || []).length" class="testcase-empty">暂无测试点，请点击“新增测试点”。</div>
            <div class="testcase-row" v-for="(tc, tcIdx) in (q.test_cases || [])" :key="`tc-${idx}-${tcIdx}`">
              <div class="testcase-grid">
                <label>
                  输入
                  <textarea v-model="tc.input" class="input input-textarea" rows="3" placeholder="例如：1 2\n" />
                </label>
                <label>
                  期望输出
                  <textarea v-model="tc.expected" class="input input-textarea" rows="3" placeholder="例如：3" />
                </label>
                <label>
                  分值权重
                  <input v-model.number="tc.weight" class="input" type="number" min="0" step="0.1" />
                </label>
                <label class="checkbox-line testcase-checkbox">
                  <input v-model="tc.is_file_io" type="checkbox" />
                  使用 input.txt 文件输入
                </label>
              </div>
              <div class="actions-row">
                <button class="ghost-btn small" type="button" @click="removeTestCase(idx, tcIdx)">删除测试点</button>
              </div>
            </div>
          </div>
        </template>
        <label class="full-width">
          参考答案
          <textarea v-model="q.reference_answer" class="input input-textarea" rows="3" />
        </label>
        <label class="full-width">
          评分点
          <textarea v-model="q.rubric" class="input input-textarea" rows="3" />
        </label>
      </div>

      <div class="actions-row section-gap">
        <button class="ghost-btn" type="button" @click="openDraftModal">AI 草稿</button>
        <button class="ghost-btn" type="button" :disabled="saving" @click="save(false)">{{ saving ? "保存中..." : "保存草稿" }}</button>
        <button class="ghost-btn" type="button" :disabled="saving" @click="save(true)">{{ saving ? "发布中..." : "保存并发布" }}</button>
      </div>
    </section>

    <section v-if="notice" class="card-panel state-card">{{ notice }}</section>
    <section v-if="error" class="card-panel state-card error-state">{{ error }}</section>

    <div v-if="draftModal.visible" class="modal-mask" @click.self="draftModal.visible = false">
      <div class="modal-card">
        <div class="section-head">
          <h3>AI 出题草稿</h3>
          <button class="ghost-btn" type="button" @click="draftModal.visible = false">关闭</button>
        </div>

        <div class="form-grid">
          <label>
            主题
            <input v-model="draftModal.topic" class="input" type="text" placeholder="例如：二分查找" />
          </label>
          <label>
            难度
            <select v-model="draftModal.difficulty" class="input">
              <option value="简单">简单</option>
              <option value="中等">中等</option>
              <option value="困难">困难</option>
            </select>
          </label>
        </div>

        <div class="actions-row">
          <button class="ghost-btn" type="button" :disabled="draftModal.loading" @click="generateDraft">
            {{ draftModal.loading ? "生成中..." : "生成草稿" }}
          </button>
          <button class="ghost-btn" type="button" :disabled="!draftModal.result" @click="applyDraft">应用到当前编辑页</button>
        </div>

        <div v-if="draftModal.result" class="question-card">
          <p><strong>{{ draftModal.result.title }}</strong></p>
          <p>{{ draftModal.result.description || "无简介" }}</p>
          <div v-for="(q, idx) in draftModal.result.questions" :key="idx" class="question-card nested">
            <p><strong>{{ idx + 1 }}. {{ q.title }}</strong></p>
            <p class="multiline">{{ q.prompt }}</p>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import {
  homeworkGenerateDraft,
  homeworkGetAssignment,
  homeworkListAssignments,
  homeworkListCourseNodes,
  homeworkPublishAssignment,
  homeworkPublishStatus,
  homeworkUpdateAssignment,
} from "../../api/homework";
import type { HomeworkCourseNode, HomeworkKnowledgePointCoverage, HomeworkQuestion, HomeworkTestCase } from "../../types/homework";
import type { HomeworkAssignment } from "../../types/homework";

const router = useRouter();
const route = useRoute();

const saving = ref(false);
const notice = ref("");
const error = ref("");
const courseNodes = ref<HomeworkCourseNode[]>([]);
const selectedNodeId = ref("");
const selectedCoverageNodeIds = ref<string[]>([]);
const syncingCourse = ref(false);

const assignmentId = computed(() => String(route.params.assignmentId || ""));
const isEdit = computed(() => Boolean(assignmentId.value));
const assignmentOptions = ref<HomeworkAssignment[]>([]);
const courseOptions = computed(() => {
  const values = assignmentOptions.value.map((item) => String(item.course_id || "").trim()).filter(Boolean);
  if (form.course_id.trim()) {
    values.push(form.course_id.trim());
  }
  const unique = Array.from(new Set(values));
  return unique.length ? unique : ["course_big_data"];
});
const classOptions = computed(() => {
  const values = assignmentOptions.value.map((item) => String(item.class_name || "").trim()).filter(Boolean);
  if (form.class_name.trim()) {
    values.push(form.class_name.trim());
  }
  return Array.from(new Set(values));
});
const leafCourseNodes = computed(() =>
  courseNodes.value.filter((node) => {
    const path = Array.isArray(node.node_path) ? node.node_path : [];
    return !courseNodes.value.some((candidate) => {
      const candidatePath = Array.isArray(candidate.node_path) ? candidate.node_path : [];
      return candidatePath.length > path.length
        && path.every((segment, index) => candidatePath[index] === segment);
    });
  }),
);

const form = reactive({
  title: "",
  description: "",
  assignment_type: "subjective" as "subjective" | "objective" | "choice" | "code",
  class_name: "",
  course_id: "course_big_data",
  node_id: "",
  node_name: "",
  node_path: [] as string[],
  chapter_context: "",
  objective_result_mode: "immediate" as "immediate" | "manual_review",
  due_at: "",
  allow_late: false,
  total_score: 100,
  rubric: "",
  questions: [] as HomeworkQuestion[],
});

const draftModal = reactive({
  visible: false,
  topic: "",
  difficulty: "中等",
  loading: false,
  result: null as null | {
    title: string;
    description: string;
    assignment_type: "subjective" | "objective" | "choice" | "code";
    course_id: string;
    node_id: string;
    node_name: string;
    node_path: string[];
    chapter_context: string;
    due_at?: string | null;
    allow_late: boolean;
    total_score: number;
    rubric: string;
    questions: HomeworkQuestion[];
  },
});

function normalizeQuestion(q?: HomeworkQuestion): HomeworkQuestion {
  const normalizedCases = Array.isArray(q?.test_cases)
    ? q!.test_cases!.map((item) => normalizeTestCase(item))
    : [];
  return {
    title: q?.title || "",
    prompt: q?.prompt || "",
    options: Array.isArray(q?.options) ? q?.options : [],
    correct_answer: q?.correct_answer || "",
    reference_answer: q?.reference_answer || "",
    rubric: q?.rubric || "",
    test_cases: normalizedCases,
  };
}

function normalizeTestCase(tc?: HomeworkTestCase): HomeworkTestCase {
  return {
    input: String(tc?.input || ""),
    expected: String(tc?.expected ?? tc?.output ?? ""),
    weight: Number(tc?.weight ?? 0),
    is_file_io: Boolean(tc?.is_file_io),
  };
}

function createDefaultTestCase(): HomeworkTestCase {
  return {
    input: "",
    expected: "",
    weight: 0,
    is_file_io: false,
  };
}

function updateQuestionOptions(index: number, raw: string) {
  const lines = raw
    .split("\n")
    .map((item) => item.trim())
    .filter(Boolean);
  form.questions[index].options = lines;
}

function addTestCase(questionIndex: number) {
  const question = form.questions[questionIndex];
  if (!question) return;
  if (!Array.isArray(question.test_cases)) {
    question.test_cases = [];
  }
  question.test_cases.push(createDefaultTestCase());
}

function removeTestCase(questionIndex: number, caseIndex: number) {
  const question = form.questions[questionIndex];
  if (!question || !Array.isArray(question.test_cases)) return;
  question.test_cases.splice(caseIndex, 1);
}

function toDateTimeLocal(value?: string | null) {
  if (!value) return "";
  const d = new Date(value);
  if (Number.isNaN(d.getTime())) return "";
  const pad = (n: number) => `${n}`.padStart(2, "0");
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`;
}

function addQuestion() {
  form.questions.push(normalizeQuestion());
}

function removeQuestion(index: number) {
  form.questions.splice(index, 1);
  if (!form.questions.length) {
    addQuestion();
  }
}

function normalizeCoveragePoints(points?: HomeworkKnowledgePointCoverage[]) {
  if (!Array.isArray(points)) return [];
  const validNodeIds = new Set(courseNodes.value.map((node) => node.node_id));
  return points
    .map((item) => String(item.node_id || "").trim())
    .filter((nodeId, index, rows) => nodeId && rows.indexOf(nodeId) === index && (!validNodeIds.size || validNodeIds.has(nodeId)));
}

function buildCoveragePayload(): HomeworkKnowledgePointCoverage[] {
  const selected = new Set(selectedCoverageNodeIds.value);
  return leafCourseNodes.value
    .filter((node) => selected.has(node.node_id))
    .map((node) => ({
      course_id: form.course_id,
      node_id: node.node_id,
      coverage_source: "teacher_confirmed",
      recommended_by_system: false,
      confirmed_by_teacher: true,
      confidence: 100,
      reason: `教师确认该作业覆盖知识点：${node.node_path.join(" > ")}`,
    }));
}

function selectRelatedLeafCoverage() {
  const related = courseNodes.value.find((node) => node.node_id === selectedNodeId.value);
  if (!related) return;
  const relatedPath = Array.isArray(related.node_path) ? related.node_path : [];
  const targetIds = leafCourseNodes.value
    .filter((node) => {
      const path = Array.isArray(node.node_path) ? node.node_path : [];
      return relatedPath.every((segment, index) => path[index] === segment);
    })
    .map((node) => node.node_id);
  selectedCoverageNodeIds.value = Array.from(new Set([...selectedCoverageNodeIds.value, ...targetIds]));
}

function fillForm(data: {
  title: string;
  description: string;
  assignment_type: "subjective" | "objective" | "choice" | "code";
  class_name: string;
  course_id: string;
  node_id: string;
  node_name: string;
  node_path: string[];
  chapter_context: string;
  objective_result_mode?: "immediate" | "manual_review";
  due_at?: string | null;
  allow_late: boolean;
  total_score: number;
  rubric: string;
  questions: HomeworkQuestion[];
  covered_knowledge_points?: HomeworkKnowledgePointCoverage[];
}) {
  form.title = data.title;
  form.description = data.description;
  form.assignment_type = data.assignment_type;
  form.class_name = data.class_name;
  form.course_id = data.course_id || "course_big_data";
  form.node_id = data.node_id || "";
  form.node_name = data.node_name || "";
  form.node_path = Array.isArray(data.node_path) ? data.node_path : [];
  form.chapter_context = data.chapter_context || "";
  form.objective_result_mode = data.objective_result_mode || "immediate";
  selectedNodeId.value = form.node_id;
  form.due_at = toDateTimeLocal(data.due_at);
  form.allow_late = data.allow_late;
  form.total_score = data.total_score;
  form.rubric = data.rubric;
  form.questions = (data.questions || []).map((item) => normalizeQuestion(item));
  selectedCoverageNodeIds.value = normalizeCoveragePoints(data.covered_knowledge_points);
  if (!form.questions.length) {
    addQuestion();
  }
}

async function loadCourseNodes() {
  try {
    const courseId = form.course_id.trim() || "course_big_data";
    const res = await homeworkListCourseNodes(courseId);
    courseNodes.value = res.nodes || [];
    selectedCoverageNodeIds.value = normalizeCoveragePoints(
      selectedCoverageNodeIds.value.map((nodeId) => ({ node_id: nodeId, course_id: courseId })),
    );
  } catch (e) {
    courseNodes.value = [];
    error.value = e instanceof Error ? e.message : "章节列表加载失败";
  }
}

async function loadMetaOptions() {
  try {
    const res = await homeworkListAssignments(false);
    assignmentOptions.value = res.assignments || [];
  } catch {
    assignmentOptions.value = [];
  }
}

function onNodeSelected() {
  const target = courseNodes.value.find((item) => item.node_id === selectedNodeId.value);
  if (!target) {
    form.node_id = "";
    form.node_name = "";
    form.node_path = [];
    return;
  }
  form.node_id = target.node_id;
  form.node_name = target.node_name;
  form.node_path = Array.isArray(target.node_path) ? target.node_path : [];
  if (!form.chapter_context.trim()) {
    form.chapter_context = `章节路径：${form.node_path.join(" > ")}`;
  }
}

async function loadDetail() {
  syncingCourse.value = true;
  await loadMetaOptions();
  if (!isEdit.value) {
    addQuestion();
    await loadCourseNodes();
    syncingCourse.value = false;
    return;
  }
  try {
    const res = await homeworkGetAssignment(assignmentId.value);
    fillForm({
      title: res.assignment.title,
      description: res.assignment.description,
      assignment_type: res.assignment.assignment_type,
      class_name: res.assignment.class_name,
      course_id: res.assignment.course_id || "course_big_data",
      node_id: res.assignment.node_id || "",
      node_name: res.assignment.node_name || "",
      node_path: res.assignment.node_path || [],
      chapter_context: res.assignment.chapter_context || "",
      objective_result_mode: res.assignment.objective_result_mode || "immediate",
      due_at: res.assignment.due_at,
      allow_late: res.assignment.allow_late,
      total_score: res.assignment.total_score,
      rubric: res.assignment.rubric,
      questions: res.assignment.questions,
      covered_knowledge_points: res.assignment.covered_knowledge_points || [],
    });
    await loadCourseNodes();
    if (form.node_id) {
      selectedNodeId.value = form.node_id;
    }
  } catch (e) {
    error.value = e instanceof Error ? e.message : "加载作业失败";
  } finally {
    syncingCourse.value = false;
  }
}

function openDraftModal() {
  draftModal.visible = true;
  draftModal.topic = form.title || "";
  draftModal.result = null;
}

async function generateDraft() {
  if (!draftModal.topic.trim()) {
    error.value = "请先输入草稿主题";
    return;
  }
  draftModal.loading = true;
  try {
    const res = await homeworkGenerateDraft({
      topic: draftModal.topic,
      assignment_type: form.assignment_type,
      difficulty: draftModal.difficulty,
      class_name: form.class_name,
      course_id: form.course_id,
      node_id: form.node_id,
      node_name: form.node_name,
      node_path: form.node_path,
      chapter_context: form.chapter_context,
      objective_result_mode: form.objective_result_mode,
    });
    if (res.draft) {
      draftModal.result = res.draft;
      notice.value = res.ok ? "AI 草稿生成成功" : "草稿生成成功（当前使用兜底模板）";
    } else {
      draftModal.result = null;
      error.value = "未收到草稿内容，请稍后重试";
    }
  } catch (e) {
    error.value = e instanceof Error ? e.message : "AI 草稿生成失败";
  } finally {
    draftModal.loading = false;
  }
}

function applyDraft() {
  if (!draftModal.result) return;
  fillForm({
    ...draftModal.result,
    class_name: form.class_name,
    course_id: form.course_id,
    node_id: form.node_id,
    node_name: form.node_name,
    node_path: form.node_path,
    chapter_context: form.chapter_context,
  });
  draftModal.visible = false;
  notice.value = "草稿已应用到编辑页";
}

async function save(publishNow: boolean) {
  error.value = "";
  notice.value = "";

  if (!form.title.trim()) {
    error.value = "请填写作业标题";
    return;
  }
  if (!form.questions.length || form.questions.some((q) => !q.prompt?.trim())) {
    error.value = "请确保每道题都填写了题目要求";
    return;
  }

  if (form.assignment_type === "code") {
    const invalidCaseQuestionIndex = form.questions.findIndex((q) => {
      const cases = (q.test_cases || []).map((item) => normalizeTestCase(item));
      if (!cases.length) {
        return true;
      }
      return cases.some((tc) => !String(tc.expected || "").trim());
    });
    if (invalidCaseQuestionIndex >= 0) {
      error.value = `第 ${invalidCaseQuestionIndex + 1} 题的测试点不完整，请至少保留一个测试点且每个测试点必须填写期望输出`;
      return;
    }
  }

  saving.value = true;
  const payload = {
    title: form.title,
    description: form.description,
    assignment_type: form.assignment_type,
    class_name: form.class_name,
    course_id: form.course_id,
    node_id: form.node_id,
    node_name: form.node_name,
    node_path: form.node_path,
    chapter_context: form.chapter_context,
    objective_result_mode: form.objective_result_mode,
    due_at: form.due_at || null,
    allow_late: form.allow_late,
    total_score: form.total_score,
    rubric: form.rubric,
    covered_knowledge_points: buildCoveragePayload(),
    questions: form.questions.map((q) => {
      const normalized = normalizeQuestion(q);
      if (form.assignment_type !== "code") {
        normalized.test_cases = [];
        return normalized;
      }
      normalized.test_cases = (normalized.test_cases || [])
        .map((tc) => normalizeTestCase(tc))
        .filter((tc) => String(tc.expected || "").trim())
        .map((tc) => ({
          input: String(tc.input || ""),
          expected: String(tc.expected || ""),
          weight: Number(tc.weight || 0),
          is_file_io: Boolean(tc.is_file_io),
        }));
      return normalized;
    }),
  };

  try {
    if (isEdit.value) {
      await homeworkUpdateAssignment(assignmentId.value, payload);
      if (publishNow) {
        await homeworkPublishStatus(assignmentId.value);
      }
      notice.value = publishNow ? "作业已更新并发布" : "作业修改已保存";
    } else {
      await homeworkPublishAssignment({ ...payload, publish_now: publishNow });
      notice.value = publishNow ? "作业已创建并发布" : "作业草稿已创建";
    }
    setTimeout(() => {
      router.push({ name: "teacher-homework" });
    }, 500);
  } catch (e) {
    error.value = e instanceof Error ? e.message : "保存失败";
  } finally {
    saving.value = false;
  }
}

watch(
  () => form.course_id,
  () => {
    if (syncingCourse.value) {
      return;
    }
    selectedNodeId.value = "";
    selectedCoverageNodeIds.value = [];
    form.node_id = "";
    form.node_name = "";
    form.node_path = [];
    loadCourseNodes();
  },
);

onMounted(loadDetail);
</script>

<style scoped>
.homework-edit-shell {
  display: grid;
  gap: 16px;
}

.form-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 10px;
}

.actions-row {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
}

.coverage-panel {
  display: grid;
  gap: 12px;
  border: 1px solid #dbeafe;
  border-radius: 10px;
  padding: 12px;
  background: #f8fbff;
}

.coverage-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
}

.coverage-head strong {
  color: #111827;
}

.coverage-head p {
  margin: 4px 0 0;
  color: #4b5563;
  font-size: 13px;
  line-height: 1.6;
}

.coverage-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 8px;
  max-height: 220px;
  overflow: auto;
}

.coverage-option {
  display: grid;
  grid-template-columns: auto minmax(0, 1fr);
  align-items: flex-start;
  gap: 8px;
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  padding: 8px 10px;
  background: #fff;
  color: #374151;
  font-size: 13px;
  line-height: 1.5;
}

.coverage-option span {
  overflow-wrap: anywhere;
}

.input {
  width: 100%;
  border: 1px solid #d0d7de;
  border-radius: 12px;
  padding: 8px 10px;
  margin-top: 6px;
}

.input-textarea {
  resize: vertical;
}

.full-width {
  display: block;
  margin-top: 10px;
}

.checkbox-line {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-top: 30px;
}

.section-gap {
  margin-top: 12px;
}

.question-card {
  border: 1px solid #e8eef6;
  border-radius: 10px;
  padding: 10px;
  margin-top: 10px;
}

.question-card.nested {
  margin-top: 8px;
  background: #fafcff;
}

.testcase-panel {
  border: 1px solid #e5edf7;
  border-radius: 10px;
  padding: 10px;
  background: #fbfdff;
}

.testcase-head {
  margin-bottom: 8px;
}

.testcase-empty {
  color: #6b7280;
  font-size: 13px;
}

.testcase-row {
  border: 1px solid #e6edf5;
  border-radius: 12px;
  padding: 10px;
  margin-top: 8px;
  background: #fff;
}

.testcase-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 8px 10px;
}

.testcase-checkbox {
  margin-top: 24px;
}

.section-head.compact {
  margin-bottom: 6px;
}

.ghost-btn.small {
  padding: 4px 8px;
}

.modal-mask {
  position: fixed;
  z-index: 99;
  inset: 0;
  background: rgba(0, 0, 0, 0.35);
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 16px;
}

.modal-card {
  width: min(880px, 96vw);
  max-height: 90vh;
  overflow: auto;
  background: #fff;
  border-radius: 12px;
  padding: 14px;
}

.multiline {
  white-space: pre-wrap;
}

@media (max-width: 900px) {
  .form-grid {
    grid-template-columns: 1fr;
  }

  .testcase-grid {
    grid-template-columns: 1fr;
  }

  .coverage-head {
    flex-direction: column;
  }

  .coverage-grid {
    grid-template-columns: 1fr;
  }

  .testcase-checkbox {
    margin-top: 0;
  }
}
</style>
