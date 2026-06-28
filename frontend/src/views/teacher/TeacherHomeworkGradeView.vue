<template>
  <div class="homework-grade-shell">
    <section class="card-panel">
      <div class="section-head">
        <h3>批改详情</h3>
        <div class="actions-row">
          <button class="ghost-btn" type="button" @click="loadData">刷新</button>
          <button class="ghost-btn" type="button" @click="goBack">返回提交列表</button>
        </div>
      </div>

      <section v-if="loading" class="state-card">加载中...</section>
      <section v-else-if="error" class="state-card error-state">{{ error }}</section>
      <template v-else-if="assignment && submission">
        <div class="summary-grid">
          <div><strong>作业：</strong>{{ assignment.title }}</div>
          <div><strong>学生：</strong>{{ submission.student_username }}</div>
          <div><strong>题型：</strong>{{ typeLabel(assignment.assignment_type) }}</div>
          <div><strong>提交时间：</strong>{{ formatTime(submission.submitted_at) }}</div>
          <div><strong>状态：</strong>{{ submission.status }}</div>
          <div><strong>满分：</strong>{{ assignment.total_score }}</div>
        </div>

        <div class="question-card" v-for="(q, idx) in assignment.questions" :key="idx">
          <p><strong>题目 {{ idx + 1 }}：{{ q.title }}</strong></p>
          <p class="multiline">{{ q.prompt }}</p>
          <label class="full-width">学生作答</label>
          <template v-if="assignment.assignment_type === 'code'">
            <div class="answer-meta">
              <span class="meta-chip">语言：{{ answerLanguageLabel(idx) }}</span>
            </div>
            <MonacoEditor
              :value="getAnswerByIndex(idx)"
              :language="editorLanguageByIndex(idx)"
              theme="vs-dark"
              :options="codePreviewOptions"
              :height="'260px'"
              class="code-preview"
            />
          </template>
          <div v-else class="answer-box multiline">{{ getAnswerByIndex(idx) || '（该题未作答）' }}</div>
        </div>

        <template v-if="assignment.assignment_type !== 'code'">
          <section class="card-panel inner-panel">
            <div class="section-head">
              <h3>AI 辅助批改</h3>
              <button class="ghost-btn" type="button" :disabled="gradingAI" @click="runAiGrade">
                {{ gradingAI ? "生成中..." : "生成 AI 建议" }}
              </button>
            </div>
            <p><strong>AI建议分：</strong>{{ submission.ai_score ?? '-' }}</p>
            <p><strong>AI评语：</strong></p>
            <div class="answer-box multiline">{{ submission.ai_feedback || '暂无' }}</div>
          </section>

          <section class="card-panel inner-panel">
            <div class="section-head">
              <h3>教师终审</h3>
              <button class="ghost-btn" type="button" @click="useAISuggestion">采用 AI 建议</button>
            </div>

            <div class="form-grid">
              <label>
                终审分数
                <input v-model.number="gradeForm.score" class="input" type="number" min="0" step="0.1" />
              </label>
            </div>

            <label class="full-width">
              终审评语
              <textarea v-model="gradeForm.comment" class="input input-textarea" rows="5" />
            </label>

            <div class="actions-row">
              <button class="ghost-btn" type="button" :disabled="saving" @click="saveFinalGrade">
                {{ saving ? "保存中..." : "保存终审结果" }}
              </button>
            </div>
          </section>
        </template>

        <section v-else class="card-panel inner-panel">
          <div class="section-head">
            <h3>代码题自动判题</h3>
            <button class="ghost-btn" type="button" :disabled="gradingAI" @click="runAiGrade">
              {{ gradingAI ? "审查中..." : "AI 审查代码" }}
            </button>
          </div>
          <p><strong>系统评分：</strong>{{ submission.teacher_score ?? submission.ai_score ?? '-' }}</p>
          <p><strong>系统反馈：</strong></p>
          <div class="answer-box multiline">{{ submission.teacher_comment || submission.ai_feedback || '暂无' }}</div>
          <p><strong>AI审查建议：</strong></p>
          <div class="answer-box multiline">{{ submission.ai_feedback || '暂无' }}</div>
          <template v-if="judgeSummary && judgeSummary.details.length">
            <p class="judge-title"><strong>沙箱判题结果：</strong>通过 {{ judgeSummary.passed }}/{{ judgeSummary.total }}</p>
            <p><strong>总分：</strong>{{ judgeSummary.earned_score ?? 0 }} / {{ judgeSummary.total_score ?? 0 }}</p>
            <div class="industry-table-wrap">
              <table class="industry-table">
                <thead>
                  <tr>
                    <th>#</th>
                    <th>状态</th>
                    <th>得分</th>
                    <th>输入</th>
                    <th>期望</th>
                    <th>实际</th>
                    <th>stderr</th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="detail in judgeSummary.details" :key="detail.case">
                    <td>{{ detail.case }}</td>
                    <td>{{ detail.ok ? 'Passed' : detail.status || 'Wrong Answer' }}</td>
                    <td>{{ detail.score ?? 0 }} / {{ detail.weight ?? 0 }}</td>
                    <td><pre class="oj-pre">{{ detail.input }}</pre></td>
                    <td><pre class="oj-pre">{{ detail.expected }}</pre></td>
                    <td><pre class="oj-pre">{{ detail.actual }}</pre></td>
                    <td><pre class="oj-pre">{{ detail.stderr || '-' }}</pre></td>
                  </tr>
                </tbody>
              </table>
            </div>
          </template>
        </section>
      </template>
    </section>

    <section v-if="notice" class="card-panel state-card">{{ notice }}</section>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from "vue";
import MonacoEditor from "@guolao/vue-monaco-editor";
import { useRoute, useRouter } from "vue-router";
import {
  homeworkAiGrade,
  homeworkFinalGrade,
  homeworkGetSubmission,
} from "../../api/homework";
import type { HomeworkAssignment, HomeworkSubmission } from "../../types/homework";

const route = useRoute();
const router = useRouter();

const loading = ref(false);
const saving = ref(false);
const gradingAI = ref(false);
const notice = ref("");
const error = ref("");

const assignment = ref<HomeworkAssignment | null>(null);
const submission = ref<HomeworkSubmission | null>(null);

const gradeForm = reactive({ score: 0, comment: "" });
const codePreviewOptions = {
  readOnly: true,
  minimap: { enabled: false },
  fontSize: 13,
  lineNumbers: "on" as const,
  automaticLayout: true,
  scrollBeyondLastLine: false,
};

const submissionId = computed(() => String(route.params.submissionId || ""));
const judgeSummary = computed(() => {
  const rationale = String(submission.value?.ai_rationale || "").trim();
  if (!rationale.startsWith("{")) {
    return null;
  }
  try {
    const parsed = JSON.parse(rationale) as Record<string, unknown>;
    const passed = Number(parsed.passed ?? -1);
    const total = Number(parsed.total ?? -1);
    const detailsRaw = Array.isArray(parsed.details) ? parsed.details : [];
    const details = detailsRaw
      .filter((item): item is Record<string, unknown> => typeof item === "object" && item !== null)
      .map((item) => ({
        case: Number(item.case ?? 0),
        ok: Boolean(item.ok),
        status: String(item.status ?? ""),
        score: Number(item.score ?? 0),
        weight: Number(item.weight ?? 0),
        input: String(item.input ?? ""),
        expected: String(item.expected ?? ""),
        actual: String(item.actual ?? ""),
        stderr: String(item.stderr ?? ""),
      }));
    if (passed >= 0 && total >= 0) {
      return {
        passed,
        total,
        earned_score: Number(parsed.earned_score ?? 0),
        total_score: Number(parsed.total_score ?? 0),
        details,
      };
    }
  } catch {
    return null;
  }
  return null;
});

function formatTime(value?: string | null) {
  if (!value) return "-";
  return new Date(value).toLocaleString();
}

function typeLabel(value: string) {
  if (value === "code") return "代码题";
  if (value === "objective") return "客观题";
  if (value === "choice") return "选择题";
  return "主观题";
}

function goBack() {
  if (assignment.value?.id) {
    router.push({ name: "teacher-homework-submissions", params: { assignmentId: assignment.value.id } });
    return;
  }
  router.push({ name: "teacher-homework" });
}

function getAnswerByIndex(index: number) {
  if (!submission.value?.answers) return "";
  const found = submission.value.answers.find((item) => Number(item.question_index) === index);
  return found ? String(found.answer ?? "") : "";
}

function getAnswerLanguageByIndex(index: number) {
  if (!submission.value?.answers) return "python";
  const found = submission.value.answers.find((item) => Number(item.question_index) === index);
  const raw = String(found?.language || "").toLowerCase();
  if (raw === "java") return "java";
  if (raw === "cpp" || raw === "c++") return "cpp";
  return "python";
}

function editorLanguageByIndex(index: number) {
  const lang = getAnswerLanguageByIndex(index);
  if (lang === "java") return "java";
  if (lang === "cpp") return "cpp";
  return "python";
}

function answerLanguageLabel(index: number) {
  const lang = getAnswerLanguageByIndex(index);
  if (lang === "java") return "Java";
  if (lang === "cpp") return "C++";
  return "Python";
}

function fillGradeForm() {
  gradeForm.score = submission.value?.teacher_score ?? submission.value?.ai_score ?? 0;
  gradeForm.comment = submission.value?.teacher_comment || submission.value?.ai_feedback || "";
}

async function loadData() {
  if (!submissionId.value) return;
  loading.value = true;
  error.value = "";
  try {
    const res = await homeworkGetSubmission(submissionId.value);
    assignment.value = res.assignment;
    submission.value = res.submission;
    fillGradeForm();
  } catch (e) {
    error.value = e instanceof Error ? e.message : "加载批改详情失败";
  } finally {
    loading.value = false;
  }
}

function useAISuggestion() {
  if (!submission.value) return;
  gradeForm.score = submission.value.ai_score ?? gradeForm.score;
  gradeForm.comment = submission.value.ai_feedback || gradeForm.comment;
}

async function runAiGrade() {
  if (!submission.value) return;
  gradingAI.value = true;
  error.value = "";
  notice.value = "";
  try {
    await homeworkAiGrade(submission.value.id);
    notice.value = "AI 建议已更新";
    await loadData();
  } catch (e) {
    error.value = e instanceof Error ? e.message : "AI 批改失败";
  } finally {
    gradingAI.value = false;
  }
}

async function saveFinalGrade() {
  if (!submission.value) return;
  saving.value = true;
  error.value = "";
  notice.value = "";
  try {
    await homeworkFinalGrade(submission.value.id, gradeForm.score, gradeForm.comment);
    notice.value = "终审结果已保存";
    await loadData();
  } catch (e) {
    error.value = e instanceof Error ? e.message : "保存终审失败";
  } finally {
    saving.value = false;
  }
}

onMounted(loadData);
</script>

<style scoped>
.homework-grade-shell {
  display: grid;
  gap: 16px;
}

.summary-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 8px 12px;
  margin-bottom: 10px;
}

.actions-row {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
}

.form-grid {
  display: grid;
  grid-template-columns: 1fr;
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

.question-card {
  border: 1px solid #e8eef6;
  border-radius: 10px;
  padding: 10px;
  margin-top: 10px;
}

.inner-panel {
  margin-top: 12px;
}

.answer-box {
  border: none; box-shadow: 0 4px 12px rgba(0,0,0,0.03); padding: 16px;
  border-radius: 12px;
  padding: 10px;
  background: #fafafa;
}

.code-preview {
  border: 1px solid #1f2937;
  border-radius: 12px;
  overflow: hidden;
}

.answer-meta {
  margin-bottom: 8px;
}

.meta-chip {
  display: inline-flex;
  align-items: center;
  border: 1px solid #d4dbe7;
  border-radius: 999px;
  padding: 4px 10px;
  font-size: 12px;
  color: #334155;
  background: #f8fbff;
}

.oj-pre {
  margin: 0;
  white-space: pre-wrap;
}

.judge-title {
  margin-top: 10px;
}

.multiline {
  white-space: pre-wrap;
}

@media (max-width: 900px) {
  .summary-grid {
    grid-template-columns: 1fr;
  }
}
</style>
