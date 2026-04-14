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
          <input v-model="form.class_name" class="input" type="text" />
        </label>
        <label>
          作业类型
          <select v-model="form.assignment_type" class="input">
            <option value="subjective">主观题</option>
            <option value="objective">客观题</option>
            <option value="choice">选择题</option>
            <option value="code">代码实践</option>
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
          <label class="full-width">
            测试用例（JSON）
            <textarea
              class="input input-textarea"
              rows="5"
              :value="JSON.stringify(q.test_cases || [], null, 2)"
              @input="updateQuestionCases(idx, ($event.target as HTMLTextAreaElement).value)"
            />
          </label>
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
import { computed, onMounted, reactive, ref } from "vue";
import { useRoute, useRouter } from "vue-router";
import {
  homeworkGenerateDraft,
  homeworkGetAssignment,
  homeworkPublishAssignment,
  homeworkPublishStatus,
  homeworkUpdateAssignment,
} from "../../api/homework";
import type { HomeworkQuestion } from "../../types/homework";

const router = useRouter();
const route = useRoute();

const saving = ref(false);
const notice = ref("");
const error = ref("");

const assignmentId = computed(() => String(route.params.assignmentId || ""));
const isEdit = computed(() => Boolean(assignmentId.value));

const form = reactive({
  title: "",
  description: "",
  assignment_type: "subjective" as "subjective" | "objective" | "choice" | "code",
  class_name: "",
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
    due_at?: string | null;
    allow_late: boolean;
    total_score: number;
    rubric: string;
    questions: HomeworkQuestion[];
  },
});

function normalizeQuestion(q?: HomeworkQuestion): HomeworkQuestion {
  return {
    title: q?.title || "",
    prompt: q?.prompt || "",
    options: Array.isArray(q?.options) ? q?.options : [],
    correct_answer: q?.correct_answer || "",
    reference_answer: q?.reference_answer || "",
    rubric: q?.rubric || "",
    test_cases: Array.isArray(q?.test_cases) ? q?.test_cases : [],
  };
}

function updateQuestionOptions(index: number, raw: string) {
  const lines = raw
    .split("\n")
    .map((item) => item.trim())
    .filter(Boolean);
  form.questions[index].options = lines;
}

function updateQuestionCases(index: number, raw: string) {
  try {
    const parsed = JSON.parse(raw);
    if (Array.isArray(parsed)) {
      form.questions[index].test_cases = parsed;
    }
  } catch {
    // Ignore invalid JSON while user is typing.
  }
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

function fillForm(data: {
  title: string;
  description: string;
  assignment_type: "subjective" | "objective" | "choice" | "code";
  class_name: string;
  due_at?: string | null;
  allow_late: boolean;
  total_score: number;
  rubric: string;
  questions: HomeworkQuestion[];
}) {
  form.title = data.title;
  form.description = data.description;
  form.assignment_type = data.assignment_type;
  form.class_name = data.class_name;
  form.due_at = toDateTimeLocal(data.due_at);
  form.allow_late = data.allow_late;
  form.total_score = data.total_score;
  form.rubric = data.rubric;
  form.questions = (data.questions || []).map((item) => normalizeQuestion(item));
  if (!form.questions.length) {
    addQuestion();
  }
}

async function loadDetail() {
  if (!isEdit.value) {
    addQuestion();
    return;
  }
  try {
    const res = await homeworkGetAssignment(assignmentId.value);
    fillForm({
      title: res.assignment.title,
      description: res.assignment.description,
      assignment_type: res.assignment.assignment_type,
      class_name: res.assignment.class_name,
      due_at: res.assignment.due_at,
      allow_late: res.assignment.allow_late,
      total_score: res.assignment.total_score,
      rubric: res.assignment.rubric,
      questions: res.assignment.questions,
    });
  } catch (e) {
    error.value = e instanceof Error ? e.message : "加载作业失败";
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
    });
    draftModal.result = res.draft;
    notice.value = res.ok ? "AI 草稿生成成功" : "AI 不可用，已返回兜底草稿";
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

  saving.value = true;
  const payload = {
    title: form.title,
    description: form.description,
    assignment_type: form.assignment_type,
    class_name: form.class_name,
    due_at: form.due_at || null,
    allow_late: form.allow_late,
    total_score: form.total_score,
    rubric: form.rubric,
    questions: form.questions.map((q) => normalizeQuestion(q)),
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

.input {
  width: 100%;
  border: 1px solid #d0d7de;
  border-radius: 8px;
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
}
</style>
