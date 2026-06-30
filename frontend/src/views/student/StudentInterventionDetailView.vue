<template>
  <div class="intervention-detail-shell">
    <section class="card-panel">
      <div class="section-head">
        <h3>任务包详情</h3>
        <div class="actions-row">
          <button class="ghost-btn" type="button" @click="loadDetail">刷新</button>
          <button class="ghost-btn" type="button" @click="router.push({ name: 'student-intervention' })">返回列表</button>
        </div>
      </div>

      <section v-if="loading" class="state-card">加载中...</section>
      <section v-else-if="error" class="state-card error-state">{{ error }}</section>
      <template v-else-if="pkg">
        <div class="summary-grid">
          <div><strong>任务包：</strong>{{ pkg.id }}</div>
          <div><strong>教师：</strong>{{ pkg.teacher_username }}</div>
          <div><strong>状态：</strong>{{ statusLabel(pkg.student_status) }}</div>
          <div><strong>进度：</strong>{{ progressText(pkg) }}</div>
        </div>

        <div class="actions-row" v-if="pkg.student_status === 'pending'">
          <button class="ghost-btn" type="button" :disabled="busy" @click="decide('accepted')">接受并开始</button>
          <button class="ghost-btn" type="button" :disabled="busy" @click="decide('declined')">暂不做</button>
        </div>
        <div class="state-card" v-if="!canAnswerQuestions">
          {{ pkg.student_status === "pending" ? "请先接受任务包后再开始。" : "当前任务包状态下不可作答。" }}
        </div>

        <section class="card-panel mini-card">
          <p><strong>教学策略：</strong>{{ pkg.strategy_summary || "-" }}</p>
        </section>


        <section v-if="structuredTasks.length" class="card-panel mini-card">
          <div class="section-head compact"><strong>在线任务</strong></div>
          <div class="intervention-task-list">
            <article v-for="task in structuredTasks" :key="`${task.type}-${task.taskId}`" class="intervention-task-card">
              <span class="task-kind">{{ task.label }}</span>
              <strong>{{ task.title || task.taskId }}</strong>
              <p>{{ task.nodeId || "未绑定知识点" }} · {{ task.required ? "必做" : "选做" }} · {{ task.completed ? "已完成" : "待完成" }}</p>
              <div class="actions-row">
                <button v-if="task.type === 'resource'" class="ghost-btn" type="button" :disabled="!task.target" @click="openResource(task.target)">打开资源</button>
                <button v-if="task.type === 'assignment'" class="ghost-btn" type="button" :disabled="!task.target" @click="goHomework(task.target)">进入作业</button>
                <button v-if="task.type === 'quiz'" class="ghost-btn" type="button" @click="goQuiz(task.nodeId)">进入测验</button>
                <button class="ghost-btn" type="button" :disabled="busy || !canAnswerQuestions" @click="toggleStructuredTask(task)">
                  {{ task.completed ? "取消完成" : "标记完成" }}
                </button>
              </div>
            </article>
          </div>
        </section>

        <div class="two-col">
          <section class="card-panel mini-card">
            <div class="section-head compact"><strong>题目列表</strong></div>
            <div class="industry-table-wrap">
              <table class="industry-table">
                <thead>
                  <tr>
                    <th>#</th>
                    <th>标题</th>
                    <th>状态</th>
                    <th>操作</th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="(q, idx) in pkg.questions" :key="q.id">
                    <td>{{ idx + 1 }}</td>
                    <td>{{ q.title }}</td>
                    <td>{{ answerStatusLabel(getAnswerStatus(q.id)) }}</td>
                    <td>
                      <button class="ghost-btn" type="button" @click="selectQuestion(q.id)">进入作答</button>
                    </td>
                  </tr>
                  <tr v-if="!pkg.questions?.length">
                    <td colspan="4">暂无题目</td>
                  </tr>
                </tbody>
              </table>
            </div>
          </section>

          <section class="card-panel mini-card" v-if="selectedQuestion">
            <div class="section-head compact">
              <strong>{{ selectedQuestion.title }}</strong>
              <span class="muted">题型：{{ questionTypeLabel(selectedQuestion.question_type) }} · 难度：{{ selectedQuestion.difficulty }}</span>
            </div>
            <p class="multiline">{{ selectedQuestion.prompt }}</p>
            <div v-if="selectedQuestion.question_type === 'single_choice'" class="field">
              <span>你的答案（单选）</span>
              <template v-if="(selectedQuestion.options || []).length">
              <label
                v-for="(option, index) in selectedQuestion.options || []"
                :key="`${selectedQuestion.id}-single-${index}`"
                class="option-row"
              >
                <input
                  type="radio"
                  :name="`single-${selectedQuestion.id}`"
                  :value="extractChoiceValue(option)"
                  :checked="currentAnswer === extractChoiceValue(option)"
                  :disabled="!canAnswerQuestions"
                  @change="selectSingleChoice(extractChoiceValue(option))"
                />
                <span>{{ option }}</span>
              </label>
              </template>
              <input
                v-else
                v-model="currentAnswer"
                class="input"
                :disabled="!canAnswerQuestions"
                placeholder="请输入选项值，如 A"
              />
            </div>
            <div v-else-if="selectedQuestion.question_type === 'multiple_choice'" class="field">
              <span>你的答案（多选）</span>
              <template v-if="(selectedQuestion.options || []).length">
              <label
                v-for="(option, index) in selectedQuestion.options || []"
                :key="`${selectedQuestion.id}-multi-${index}`"
                class="option-row"
              >
                <input
                  type="checkbox"
                  :value="extractChoiceValue(option)"
                  :checked="multipleChoiceValues.includes(extractChoiceValue(option))"
                  :disabled="!canAnswerQuestions"
                  @change="toggleMultipleChoice(extractChoiceValue(option))"
                />
                <span>{{ option }}</span>
              </label>
              </template>
              <input
                v-else
                v-model="currentAnswer"
                class="input"
                :disabled="!canAnswerQuestions"
                placeholder="请输入选项值，多个用逗号分隔，如 A,C"
              />
            </div>
            <label v-else class="field">
              <span>你的答案</span>
              <textarea
                v-model="currentAnswer"
                :rows="selectedQuestion.question_type === 'code' ? 14 : 10"
                class="input input-textarea"
                :disabled="!canAnswerQuestions"
                :placeholder="selectedQuestion.question_type === 'code' ? '请输入代码答案' : '请输入本题答案'"
              />
            </label>
            <label class="field">
              <span>本题备注（自动保存）</span>
              <textarea
                v-model="currentNote"
                rows="3"
                class="input input-textarea"
                :disabled="!canAnswerQuestions"
                placeholder="记录本题疑问、思路或反馈"
              />
            </label>
            <div class="actions-row">
              <button class="ghost-btn" type="button" :disabled="busy || !selectedQuestion || !canAnswerQuestions" @click="saveCurrentAnswer">
                {{ busy ? "保存中..." : "保存本题答案" }}
              </button>
              <span class="muted" v-if="autoSaveState">{{ autoSaveState }}</span>
            </div>
          </section>
        </div>
      </template>
    </section>
  </div>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import axios from "axios";
import {
  interventionStudentDecision,
  interventionStudentPackageDetail,
  interventionStudentSaveAnswer,
  interventionStudentUpdateTask,
} from "../../api/intervention";
import type { InterventionPackage, InterventionQuestion } from "../../types/intervention";

type StructuredTaskRow = {
  type: "resource" | "assignment" | "quiz" | "code";
  label: string;
  taskId: string;
  title: string;
  target: string;
  nodeId: string;
  required: boolean;
  completed: boolean;
};

const route = useRoute();
const router = useRouter();

const loading = ref(false);
const busy = ref(false);
const error = ref("");
const pkg = ref<InterventionPackage | null>(null);
const selectedQuestionId = ref("");
const currentAnswer = ref("");
const currentNote = ref("");
const autoSaveState = ref("");
let autoSaveTimer: ReturnType<typeof setTimeout> | null = null;
let syncingFromServer = false;

const packageId = computed(() => String(route.params.packageId || ""));

const selectedQuestion = computed<InterventionQuestion | null>(() => {
  const questions = pkg.value?.questions || [];
  return questions.find((item) => item.id === selectedQuestionId.value) || null;
});

const canAnswerQuestions = computed(() => {
  const status = pkg.value?.student_status;
  return status === "accepted" || status === "in_progress" || status === "completed";
});

const structuredTasks = computed(() => {
  const current = pkg.value;
  if (!current) return [] as StructuredTaskRow[];
  return [
    ...(current.resource_tasks || []).map((item) => ({
      type: "resource" as const,
      label: "资源",
      taskId: String(item.id || item.resource_id || item.resource_path || item.title || ""),
      title: item.title || item.resource_path || "推荐资源",
      target: item.resource_path || "",
      nodeId: item.node_id || "",
      required: item.required !== false,
      completed: item.status === "completed",
    })),
    ...(current.assignment_tasks || []).map((item) => ({
      type: "assignment" as const,
      label: "作业",
      taskId: String(item.id || item.assignment_id || item.title || ""),
      title: item.title || item.assignment_id || "作业任务",
      target: item.assignment_id || "",
      nodeId: item.node_id || "",
      required: item.required !== false,
      completed: item.status === "completed",
    })),
    ...(current.quiz_tasks || []).map((item) => ({
      type: "quiz" as const,
      label: "测验",
      taskId: String(item.id || item.quiz_id || item.title || ""),
      title: item.title || item.quiz_id || "测验任务",
      target: item.quiz_id || "",
      nodeId: item.node_id || "",
      required: item.required !== false,
      completed: item.status === "completed",
    })),
    ...(current.code_tasks || []).map((item) => ({
      type: "code" as const,
      label: "代码",
      taskId: String(item.id || item.task_id || item.title || ""),
      title: item.title || item.task_id || "代码练习",
      target: item.task_id || "",
      nodeId: item.node_id || "",
      required: item.required !== false,
      completed: item.status === "completed",
    })),
  ].filter((item) => item.taskId);
});

function formatTime(value?: string) {
  if (!value) return "-";
  return new Date(value).toLocaleString();
}
function statusLabel(status: string) {
  if (status === "accepted") return "已接受";
  if (status === "declined") return "暂不做";
  if (status === "in_progress") return "进行中";
  if (status === "completed") return "已完成";
  return "待处理";
}

function answerStatusLabel(status: string) {
  if (status === "completed") return "已完成";
  return "待作答";
}
function questionTypeLabel(type?: string) {
  if (type === "fill_blank") return "填空题";
  if (type === "single_choice") return "单选题";
  if (type === "multiple_choice") return "多选题";
  if (type === "code") return "编程题";
  return "主观题";
}

function extractChoiceValue(option: string) {
  const text = String(option || "").trim();
  const match = text.match(/^([A-Za-z])[\.\s、:：-]+/);
  if (match?.[1]) return match[1].toUpperCase();
  return text.toUpperCase();
}

const multipleChoiceValues = computed(() => {
  if (!currentAnswer.value) return [] as string[];
  return currentAnswer.value
    .split(",")
    .map((x) => x.trim().toUpperCase())
    .filter(Boolean);
});

function selectSingleChoice(value: string) {
  currentAnswer.value = value.toUpperCase();
}

function toggleMultipleChoice(value: string) {
  const next = new Set(multipleChoiceValues.value);
  const normalized = value.toUpperCase();
  if (next.has(normalized)) next.delete(normalized);
  else next.add(normalized);
  currentAnswer.value = Array.from(next).sort().join(",");
}

function progressText(item: InterventionPackage) {
  const rate = Math.round((item.progress?.completion_rate || 0) * 100);
  const answered = item.progress?.completed_items ?? item.progress?.answered_questions ?? 0;
  const total = item.progress?.total_items ?? item.progress?.total_questions ?? (item.questions?.length || 0);
  return `${rate}% (${answered}/${total})`;
}

function openResource(resourcePath?: string) {
  const target = String(resourcePath || "").trim();
  if (!target) return;
  window.open(target, "_blank", "noopener,noreferrer");
}

function goHomework(assignmentId?: string) {
  const target = String(assignmentId || "").trim();
  if (!target) return;
  router.push({ name: "student-homework-detail", params: { assignmentId: target } });
}

function goQuiz(nodeId?: string) {
  router.push({ name: "student-quiz", query: nodeId ? { node_id: nodeId } : undefined });
}

async function toggleStructuredTask(task: { type: "resource" | "assignment" | "quiz" | "code"; taskId: string; completed: boolean }) {
  if (!pkg.value) return;
  if (!canAnswerQuestions.value) {
    error.value = "请先接受任务包后再更新任务状态。";
    return;
  }
  busy.value = true;
  error.value = "";
  try {
    await interventionStudentUpdateTask(pkg.value.id, {
      task_type: task.type,
      task_id: task.taskId,
      completed: !task.completed,
    });
    await loadDetail();
  } catch (e) {
    error.value = e instanceof Error ? e.message : "任务状态更新失败";
  } finally {
    busy.value = false;
  }
}

function getAnswerStatus(questionId: string) {
  const target = (pkg.value?.answers || []).find((item) => item.question_id === questionId);
  return target?.status || "pending";
}

function syncCurrentAnswer() {
  if (!pkg.value || !selectedQuestionId.value) {
    currentAnswer.value = "";
    currentNote.value = "";
    return;
  }
  const target = (pkg.value.answers || []).find((item) => item.question_id === selectedQuestionId.value);
  syncingFromServer = true;
  currentAnswer.value = target?.answer || "";
  currentNote.value = target?.note || "";
  setTimeout(() => {
    syncingFromServer = false;
  }, 0);
}

function selectQuestion(questionId: string) {
  selectedQuestionId.value = questionId;
  syncCurrentAnswer();
}

async function loadDetail() {
  if (!packageId.value) return;
  loading.value = true;
  error.value = "";
  try {
    const res = await interventionStudentPackageDetail(packageId.value);
    pkg.value = res.package;
    if (!selectedQuestionId.value && pkg.value.questions?.length) {
      selectedQuestionId.value = pkg.value.questions[0].id;
    }
    syncCurrentAnswer();
  } catch (e) {
    error.value = e instanceof Error ? e.message : "加载详情失败";
  } finally {
    loading.value = false;
  }
}

async function decide(decision: "accepted" | "declined") {
  if (!pkg.value) return;
  busy.value = true;
  error.value = "";
  try {
    await interventionStudentDecision(pkg.value.id, { decision, note: "" });
    await loadDetail();
  } catch (e) {
    error.value = e instanceof Error ? e.message : "操作失败";
  } finally {
    busy.value = false;
  }
}

async function saveCurrentAnswer() {
  if (!pkg.value || !selectedQuestion.value) return;
  if (!canAnswerQuestions.value) {
    error.value = "请先点击“接受并开始”后再作答。";
    return;
  }
  busy.value = true;
  error.value = "";
  try {
    await interventionStudentSaveAnswer(pkg.value.id, {
      question_id: selectedQuestion.value.id,
      answer: currentAnswer.value,
      note: currentNote.value,
    });
    autoSaveState.value = `已保存 ${new Date().toLocaleTimeString()}`;
    await loadDetail();
  } catch (e) {
    if (axios.isAxiosError(e)) {
      const detail =
        typeof e.response?.data === "string"
          ? e.response.data
          : (e.response?.data as { detail?: string } | undefined)?.detail;
      error.value = detail || "保存答案失败";
    } else {
      error.value = e instanceof Error ? e.message : "保存答案失败";
    }
  } finally {
    busy.value = false;
  }
}

function scheduleAutoSave() {
  if (!pkg.value || !selectedQuestion.value) return;
  if (pkg.value.student_status === "declined" || pkg.value.student_status === "pending") return;
  if (syncingFromServer) return;
  if (autoSaveTimer) clearTimeout(autoSaveTimer);
  autoSaveState.value = "自动保存中...";
  autoSaveTimer = setTimeout(async () => {
    try {
      await interventionStudentSaveAnswer(pkg.value!.id, {
        question_id: selectedQuestion.value!.id,
        answer: currentAnswer.value,
        note: currentNote.value,
      });
      autoSaveState.value = `已自动保存 ${new Date().toLocaleTimeString()}`;
      await loadDetail();
    } catch {
      autoSaveState.value = "自动保存失败，请手动保存";
    }
  }, 1200);
}

watch([currentAnswer, currentNote], () => {
  scheduleAutoSave();
});

onMounted(loadDetail);
onBeforeUnmount(() => {
  if (autoSaveTimer) clearTimeout(autoSaveTimer);
});
</script>

<style scoped>
.intervention-detail-shell {
  display: grid;
  gap: 16px;
}

.summary-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
  gap: 8px;
  margin-bottom: 12px;
}

.mini-card {
  border-radius: 12px;
  padding: 12px;
}

.intervention-task-list {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
  gap: 10px;
}

.intervention-task-card {
  display: grid;
  gap: 8px;
  align-content: start;
  border: 1px solid #e2e8f0;
  border-radius: 10px;
  padding: 12px;
  background: #fff;
}

.intervention-task-card p {
  margin: 0;
  color: #64748b;
  font-size: 13px;
}

.task-kind {
  width: fit-content;
  border-radius: 999px;
  background: #eef2ff;
  color: #3730a3;
  padding: 3px 8px;
  font-size: 12px;
  font-weight: 700;
}

.two-col {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 10px;
}

.field {
  display: grid;
  gap: 6px;
  margin-top: 8px;
}

.input {
  width: 100%;
  border: 1px solid #d0d7de;
  border-radius: 8px;
  padding: 8px 10px;
  font-size: 14px;
}

.input-textarea {
  resize: vertical;
  line-height: 1.6;
}

.option-row {
  display: flex;
  align-items: center;
  gap: 8px;
}

@media (max-width: 900px) {
  .two-col {
    grid-template-columns: 1fr;
  }
}
</style>

