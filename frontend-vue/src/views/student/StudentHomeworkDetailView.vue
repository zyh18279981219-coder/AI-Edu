<template>
  <div class="homework-detail-shell">
    <section class="card-panel">
      <div class="section-head">
        <h3>作业详情与提交</h3>
        <div class="actions-row">
          <button class="ghost-btn" type="button" @click="loadDetail">刷新</button>
          <button class="ghost-btn" type="button" @click="router.push({ name: 'student-homework' })">返回列表</button>
        </div>
      </div>

      <section v-if="loading" class="state-card">加载中...</section>
      <section v-else-if="error" class="state-card error-state">{{ error }}</section>
      <template v-else-if="assignment">
        <div class="summary-grid">
          <div><strong>标题：</strong>{{ assignment.title }}</div>
          <div><strong>类型：</strong>{{ assignment.assignment_type === 'code' ? '代码实践' : '主观题' }}</div>
          <div><strong>满分：</strong>{{ assignment.total_score }}</div>
          <div><strong>截止：</strong>{{ formatTime(assignment.due_at) }}</div>
          <div><strong>逾期：</strong>{{ assignment.allow_late ? '允许' : '不允许' }}</div>
          <div><strong>状态：</strong>{{ assignment.status }}</div>
        </div>

        <div class="tab-row">
          <button
            v-for="item in tabs"
            :key="item.key"
            class="tab-btn"
            :class="{ active: activeTab === item.key }"
            type="button"
            @click="activeTab = item.key"
          >
            {{ item.label }}
          </button>
        </div>

        <section v-if="activeTab === 'problem'">
          <p class="multiline desc">{{ assignment.description || '无作业简介' }}</p>
          <div class="question-card" v-for="(q, idx) in assignment.questions" :key="`problem-${idx}`">
            <div class="section-head compact">
              <strong>题目 {{ idx + 1 }}：{{ q.title }}</strong>
            </div>
            <p class="multiline">{{ q.prompt }}</p>
          </div>
        </section>

        <section v-if="activeTab === 'submit'">
          <div class="question-card" v-for="(q, idx) in assignment.questions" :key="`submit-${idx}`">
            <div class="section-head compact">
              <strong>题目 {{ idx + 1 }}：{{ q.title }}</strong>
            </div>
            <p class="multiline">{{ q.prompt }}</p>

            <template v-if="assignment.assignment_type === 'objective'">
              <div class="option-grid">
                <label v-for="opt in (q.options || ['A. 正确', 'B. 错误'])" :key="opt" class="option-item">
                  <input type="radio" :name="`q-${idx}`" :value="parseOptionValue(opt)" v-model="answerMap[idx]" />
                  {{ opt }}
                </label>
              </div>
            </template>

            <template v-else-if="assignment.assignment_type === 'choice'">
              <div class="option-grid">
                <label v-for="opt in (q.options || [])" :key="opt" class="option-item">
                  <input
                    type="checkbox"
                    :value="parseOptionValue(opt)"
                    :checked="isSelected(idx, parseOptionValue(opt))"
                    @change="toggleChoice(idx, parseOptionValue(opt), ($event.target as HTMLInputElement).checked)"
                  />
                  {{ opt }}
                </label>
              </div>
            </template>

            <template v-else-if="assignment.assignment_type === 'code'">
              <div class="code-toolbar">
                <label>
                  语言
                  <select v-model="languageMap[idx]" class="input language-select">
                    <option value="python">Python</option>
                    <option value="cpp">C++</option>
                    <option value="java">Java</option>
                  </select>
                </label>
                <label class="upload-label">
                  上传代码文件
                  <input
                    type="file"
                    accept=".py,.cpp,.cc,.cxx,.java,.txt,text/plain"
                    @change="onCodeFileSelected(idx, $event)"
                  />
                </label>
              </div>
              <MonacoEditor
                v-model:value="answerMap[idx]"
                :language="editorLanguage(languageMap[idx])"
                theme="vs-dark"
                :options="editorOptions"
                :height="'320px'"
                class="code-editor"
              />
            </template>

            <label v-else class="full-width">
              你的答案（第 {{ idx + 1 }} 题）
              <textarea
                :value="getAnswer(idx)"
                class="input input-textarea"
                rows="7"
                placeholder="请输入你的作答"
                @input="setAnswer(idx, ($event.target as HTMLTextAreaElement).value)"
              />
            </label>
          </div>

          <div class="actions-row">
            <button class="ghost-btn" type="button" :disabled="submitting" @click="submitAll">
              {{ submitting ? '提交中...' : '提交全部题目' }}
            </button>
          </div>
        </section>

        <section v-if="activeTab === 'result'">
          <section v-if="latestSubmission" class="question-card">
            <div class="section-head compact">
              <strong>最近一次提交结果</strong>
            </div>
            <p><strong>提交时间：</strong>{{ formatTime(latestSubmission.submitted_at) }}</p>
            <p><strong>状态：</strong>{{ latestSubmission.status }}</p>
            <p><strong>得分：</strong>{{ latestSubmission.teacher_score ?? latestSubmission.ai_score ?? '-' }}</p>

            <template v-if="assignment.assignment_type === 'code'">
              <p><strong>判题摘要：</strong>{{ latestSubmission.ai_feedback || latestSubmission.teacher_comment || '-' }}</p>
              <template v-if="latestJudgeReport">
                <p><strong>总分：</strong>{{ latestJudgeReport.earned_score ?? 0 }} / {{ latestJudgeReport.total_score ?? 0 }}</p>
                <div class="result-list">
                  <div v-for="detail in latestJudgeReport.details" :key="`latest-${detail.case}`" class="result-item">
                    <div class="result-title">
                      测试点 {{ detail.case }}：
                      <span :class="['verdict-chip', detail.ok ? 'ok' : 'fail']">[{{ caseVerdict(detail) }}]</span>
                      +{{ detail.score ?? 0 }}分
                    </div>
                    <div class="result-meta">权重：{{ detail.weight ?? 0 }} | {{ detail.is_file_io ? 'FileIO' : 'StdIO' }} | {{ detail.status || '-' }}</div>
                    <div class="result-io-grid">
                      <div>
                        <div class="io-label">输入</div>
                        <pre class="oj-pre">{{ detail.input }}</pre>
                      </div>
                      <div>
                        <div class="io-label">期望</div>
                        <pre class="oj-pre">{{ detail.expected }}</pre>
                      </div>
                      <div>
                        <div class="io-label">实际</div>
                        <pre class="oj-pre">{{ detail.actual }}</pre>
                      </div>
                      <div>
                        <div class="io-label">错误</div>
                        <pre class="oj-pre">{{ detail.stderr || '-' }}</pre>
                      </div>
                    </div>
                  </div>
                </div>
              </template>
            </template>
          </section>
          <section v-else class="state-card">暂无提交结果</section>
        </section>

        <section v-if="activeTab === 'history'" class="history-grid">
          <div class="history-list">
            <table class="industry-table">
              <thead>
                <tr>
                  <th>提交时间</th>
                  <th>状态</th>
                  <th>得分</th>
                </tr>
              </thead>
              <tbody>
                <tr
                  v-for="item in submissionHistory"
                  :key="item.id"
                  :class="{ 'history-active': selectedHistoryId === item.id }"
                  @click="selectedHistoryId = item.id"
                >
                  <td>{{ formatTime(item.submitted_at) }}</td>
                  <td>{{ item.status }}</td>
                  <td>{{ item.teacher_score ?? item.ai_score ?? '-' }}</td>
                </tr>
                <tr v-if="!submissionHistory.length">
                  <td colspan="3">暂无历史提交</td>
                </tr>
              </tbody>
            </table>
          </div>

          <div class="history-detail" v-if="selectedHistorySubmission">
            <p><strong>提交时间：</strong>{{ formatTime(selectedHistorySubmission.submitted_at) }}</p>
            <p><strong>得分：</strong>{{ selectedHistorySubmission.teacher_score ?? selectedHistorySubmission.ai_score ?? '-' }}</p>

            <template v-if="assignment.assignment_type === 'code'">
              <MonacoEditor
                :value="historyCode"
                :language="editorLanguage(historyLanguage)"
                theme="vs-dark"
                :options="historyEditorOptions"
                :height="'320px'"
                class="code-editor"
              />
            </template>
          </div>
        </section>
      </template>
    </section>

    <section v-if="notice" class="card-panel state-card">{{ notice }}</section>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import MonacoEditor from "@guolao/vue-monaco-editor";
import { useRoute, useRouter } from "vue-router";
import {
  homeworkGetAssignment,
  homeworkListMySubmissions,
  homeworkSubmitAssignment,
} from "../../api/homework";
import type {
  CodeLanguage,
  HomeworkAssignment,
  HomeworkSubmission,
  JudgeCaseDetail,
  JudgeReport,
} from "../../types/homework";

const route = useRoute();
const router = useRouter();

const assignment = ref<HomeworkAssignment | null>(null);
const loading = ref(false);
const submitting = ref(false);
const error = ref("");
const notice = ref("");
const answerMap = ref<Record<number, string>>({});
const languageMap = ref<Record<number, CodeLanguage>>({});
const latestSubmission = ref<HomeworkSubmission | null>(null);
const submissionHistory = ref<HomeworkSubmission[]>([]);
const selectedHistoryId = ref("");
const activeTab = ref<"problem" | "submit" | "result" | "history">("problem");

const tabs = [
  { key: "problem", label: "查看" },
  { key: "submit", label: "提交" },
  { key: "result", label: "结果" },
  { key: "history", label: "提交历史" },
] as const;

const editorOptions = {
  minimap: { enabled: false },
  fontSize: 14,
  lineNumbers: "on" as const,
  automaticLayout: true,
  tabSize: 2,
  roundedSelection: false,
  scrollBeyondLastLine: false,
};

const historyEditorOptions = {
  ...editorOptions,
  readOnly: true,
};

const assignmentId = computed(() => String(route.params.assignmentId || ""));
const latestJudgeReport = computed(() => parseJudgeReport(latestSubmission.value?.ai_rationale));
const selectedHistorySubmission = computed(() => submissionHistory.value.find((item) => item.id === selectedHistoryId.value) || null);

const historyCode = computed(() => {
  const s = selectedHistorySubmission.value;
  if (!s) return "";
  const first = (s.answers || []).find((item) => typeof item?.answer === "string");
  return String(first?.answer || "");
});

const historyLanguage = computed<CodeLanguage>(() => {
  const s = selectedHistorySubmission.value;
  if (!s) return "python";
  const first = (s.answers || []).find((item) => typeof item?.language === "string");
  const raw = String(first?.language || "").toLowerCase();
  if (raw === "java") return "java";
  if (raw === "cpp" || raw === "c++") return "cpp";
  return "python";
});

function formatTime(value?: string | null) {
  if (!value) return "-";
  return new Date(value).toLocaleString();
}

function parseOptionValue(optionText: string) {
  const text = String(optionText || "").trim();
  const matched = text.match(/^([A-Z])\./i);
  if (matched) {
    return matched[1].toUpperCase();
  }
  return text;
}

function isSelected(questionIndex: number, value: string) {
  const current = String(answerMap.value[questionIndex] || "");
  return current.split(",").map((x) => x.trim()).filter(Boolean).includes(value);
}

function getAnswer(questionIndex: number) {
  return String(answerMap.value[questionIndex] || "");
}

function setAnswer(questionIndex: number, value: string) {
  answerMap.value[questionIndex] = value;
  if (!languageMap.value[questionIndex]) {
    languageMap.value[questionIndex] = detectLanguageFromCode(value);
  }
}

function editorLanguage(lang?: CodeLanguage) {
  if (lang === "cpp") return "cpp";
  if (lang === "java") return "java";
  return "python";
}

function detectLanguageFromCode(code: string): CodeLanguage {
  const text = String(code || "");
  const low = text.toLowerCase();
  if (text.includes("public class") || low.includes("import java") || low.includes("system.out")) return "java";
  if (text.includes("#include") || low.includes("using namespace std") || low.includes("int main(")) return "cpp";
  return "python";
}

async function onCodeFileSelected(questionIndex: number, event: Event) {
  const input = event.target as HTMLInputElement;
  const file = input.files?.[0];
  if (!file) return;

  const ext = (file.name.split(".").pop() || "").toLowerCase();
  if (ext === "py") languageMap.value[questionIndex] = "python";
  if (["cpp", "cc", "cxx"].includes(ext)) languageMap.value[questionIndex] = "cpp";
  if (ext === "java") languageMap.value[questionIndex] = "java";

  const content = await file.text();
  setAnswer(questionIndex, content);
  input.value = "";
}

function toggleChoice(questionIndex: number, value: string, checked: boolean) {
  const current = String(answerMap.value[questionIndex] || "")
    .split(",")
    .map((x) => x.trim())
    .filter(Boolean);
  const next = checked ? Array.from(new Set([...current, value])) : current.filter((x) => x !== value);
  answerMap.value[questionIndex] = next.join(",");
}

function parseJudgeReport(raw?: string): JudgeReport | null {
  const text = String(raw || "").trim();
  if (!text.startsWith("{")) {
    return null;
  }
  try {
    const parsed = JSON.parse(text) as Record<string, unknown>;
    const detailsRaw = Array.isArray(parsed.details) ? parsed.details : [];
    const details = detailsRaw
      .filter((item): item is Record<string, unknown> => typeof item === "object" && item !== null)
      .map((item) => ({
        case: Number(item.case ?? 0),
        ok: Boolean(item.ok),
        status: String(item.status ?? ""),
        input: String(item.input ?? ""),
        expected: String(item.expected ?? ""),
        actual: String(item.actual ?? ""),
        stderr: String(item.stderr ?? ""),
        weight: Number(item.weight ?? 0),
        score: Number(item.score ?? 0),
        is_file_io: Boolean(item.is_file_io),
        exit_code: Number(item.exit_code ?? 0),
        time_ms: Number(item.time_ms ?? 0),
        memory_kb: Number(item.memory_kb ?? 0),
      }));
    return {
      passed: Number(parsed.passed ?? 0),
      total: Number(parsed.total ?? 0),
      earned_score: Number(parsed.earned_score ?? 0),
      total_score: Number(parsed.total_score ?? 0),
      score_rate: Number(parsed.score_rate ?? 0),
      details,
    };
  } catch {
    return null;
  }
}

function caseVerdict(detail: JudgeCaseDetail) {
  return detail.ok ? "Passed" : "Wrong Answer";
}

async function loadDetail() {
  if (!assignmentId.value) return;
  loading.value = true;
  error.value = "";
  notice.value = "";
  try {
    const [detailRes, mySubRes] = await Promise.all([
      homeworkGetAssignment(assignmentId.value),
      homeworkListMySubmissions(assignmentId.value),
    ]);
    assignment.value = detailRes.assignment;
    submissionHistory.value = mySubRes.submissions || [];

    latestSubmission.value = submissionHistory.value[0] || null;
    selectedHistoryId.value = latestSubmission.value?.id || "";

    const nextMap: Record<number, string> = {};
    const nextLanguageMap: Record<number, CodeLanguage> = {};

    if (latestSubmission.value && Array.isArray(latestSubmission.value.answers)) {
      for (const item of latestSubmission.value.answers) {
        const idx = Number(item.question_index ?? -1);
        if (idx >= 0) {
          const answerText = String(item.answer ?? "");
          nextMap[idx] = answerText;
          const rawLang = String(item.language ?? "").toLowerCase();
          if (rawLang === "java") nextLanguageMap[idx] = "java";
          else if (rawLang === "cpp" || rawLang === "c++") nextLanguageMap[idx] = "cpp";
          else nextLanguageMap[idx] = detectLanguageFromCode(answerText);
        }
      }
    }

    for (let i = 0; i < (detailRes.assignment.questions?.length ?? 0); i += 1) {
      if (!(i in nextMap)) {
        nextMap[i] = "";
      }
      if (!(i in nextLanguageMap)) {
        nextLanguageMap[i] = "python";
      }
    }

    answerMap.value = nextMap;
    languageMap.value = nextLanguageMap;
  } catch (e) {
    error.value = e instanceof Error ? e.message : "加载作业详情失败";
  } finally {
    loading.value = false;
  }
}

async function submitAll() {
  if (!assignment.value) return;
  error.value = "";
  notice.value = "";

  const answers = assignment.value.questions.map((_, idx) => {
    const code = (answerMap.value[idx] || "").trim();
    const selected = languageMap.value[idx] || detectLanguageFromCode(code);
    return {
      question_index: idx,
      answer: code,
      language: assignment.value?.assignment_type === "code" ? selected : undefined,
    };
  });

  const emptyCount = answers.filter((item) => !item.answer).length;
  if (emptyCount > 0) {
    error.value = `还有 ${emptyCount} 道题未作答`;
    return;
  }

  submitting.value = true;
  try {
    const submitRes = await homeworkSubmitAssignment(assignment.value.id, answers);
    latestSubmission.value = submitRes.submission;
    notice.value = "作业提交成功";
    activeTab.value = "result";
    await loadDetail();
  } catch (e) {
    error.value = e instanceof Error ? e.message : "提交失败";
  } finally {
    submitting.value = false;
  }
}

onMounted(loadDetail);
</script>

<style scoped>
.homework-detail-shell {
  display: grid;
  gap: 16px;
}

.summary-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 8px 16px;
  margin-bottom: 10px;
}

.tab-row {
  display: flex;
  gap: 8px;
  margin: 10px 0 14px;
  flex-wrap: wrap;
}

.tab-btn {
  border: 1px solid #d2dbe8;
  background: #f8fbff;
  color: #1f2a44;
  border-radius: 8px;
  padding: 6px 12px;
  cursor: pointer;
}

.tab-btn.active {
  background: #254f8f;
  border-color: #254f8f;
  color: #fff;
}

.actions-row {
  display: flex;
  gap: 8px;
  justify-content: flex-end;
}

.question-card {
  border: 1px solid #e8eef6;
  border-radius: 10px;
  padding: 10px;
  margin-top: 10px;
}

.option-grid {
  display: grid;
  gap: 8px;
  margin-top: 8px;
}

.option-item {
  display: flex;
  gap: 8px;
  align-items: center;
}

.section-head.compact {
  margin-bottom: 6px;
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
}

.code-toolbar {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  align-items: flex-end;
  margin-bottom: 8px;
}

.language-select {
  min-width: 140px;
}

.upload-label {
  display: grid;
  gap: 6px;
  font-size: 13px;
}

.code-editor {
  border: 1px solid #22303f;
  border-radius: 8px;
  overflow: hidden;
  height: 320px;
  max-height: 320px;
}

.multiline {
  white-space: pre-wrap;
}

.desc {
  margin: 8px 0;
}

.verdict-chip {
  display: inline-block;
  padding: 3px 8px;
  border-radius: 999px;
  font-size: 12px;
  font-weight: 700;
}

.verdict-chip.ok {
  color: #065f46;
  background: #d1fae5;
}

.verdict-chip.fail {
  color: #991b1b;
  background: #fee2e2;
}

.oj-pre {
  white-space: pre-wrap;
  margin: 0;
}

.result-list {
  display: grid;
  gap: 10px;
  margin-top: 10px;
}

.result-item {
  border: 1px solid #dbe5ef;
  border-radius: 10px;
  padding: 10px;
  background: #f8fbff;
}

.result-title {
  font-weight: 700;
}

.result-meta {
  color: #4b5563;
  font-size: 12px;
  margin-top: 4px;
}

.result-io-grid {
  margin-top: 8px;
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 8px 12px;
}

.io-label {
  font-size: 12px;
  color: #6b7280;
  margin-bottom: 4px;
}

.history-grid {
  display: grid;
  grid-template-columns: 1.1fr 1fr;
  gap: 12px;
}

.history-list {
  overflow: auto;
}

.history-active {
  background: #eef5ff;
}

.history-detail {
  border: 1px solid #e1e8f3;
  border-radius: 8px;
  padding: 10px;
  background: #fbfdff;
}

@media (max-width: 900px) {
  .summary-grid {
    grid-template-columns: 1fr;
  }

  .code-toolbar {
    flex-direction: column;
    align-items: stretch;
  }

  .result-io-grid {
    grid-template-columns: 1fr;
  }

  .history-grid {
    grid-template-columns: 1fr;
  }
}
</style>
