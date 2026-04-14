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
          <div><strong>类型：</strong>{{ assignment.assignment_type === "code" ? "代码实践" : "主观题" }}</div>
          <div><strong>满分：</strong>{{ assignment.total_score }}</div>
          <div><strong>截止：</strong>{{ formatTime(assignment.due_at) }}</div>
          <div><strong>逾期：</strong>{{ assignment.allow_late ? "允许" : "不允许" }}</div>
          <div><strong>状态：</strong>{{ assignment.status }}</div>
        </div>

        <p class="multiline desc">{{ assignment.description || "无作业简介" }}</p>

        <div class="question-card" v-for="(q, idx) in assignment.questions" :key="idx">
          <div class="section-head compact">
            <strong>题目 {{ idx + 1 }}：{{ q.title }}</strong>
          </div>
          <p class="multiline">{{ q.prompt }}</p>
          <template v-if="assignment.assignment_type === 'objective'">
            <div class="option-grid">
              <label v-for="opt in (q.options || ['A. 正确', 'B. 错误'])" :key="opt" class="option-item">
                <input
                  type="radio"
                  :name="`q-${idx}`"
                  :value="parseOptionValue(opt)"
                  v-model="answerMap[idx]"
                />
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
          <template v-else>
            <label class="full-width">
              你的答案（第 {{ idx + 1 }} 题）
              <textarea
                v-model="answerMap[idx]"
                class="input input-textarea"
                rows="7"
                :placeholder="assignment.assignment_type === 'code' ? '请输入可运行代码' : '请输入你的作答'"
              />
            </label>
          </template>
        </div>

        <div class="actions-row">
          <button class="ghost-btn" type="button" :disabled="submitting" @click="submitAll">
            {{ submitting ? "提交中..." : "提交全部题目" }}
          </button>
        </div>

        <section v-if="latestSubmission" class="question-card">
          <div class="section-head compact">
            <strong>最近一次提交结果</strong>
          </div>
          <p><strong>提交时间：</strong>{{ formatTime(latestSubmission.submitted_at) }}</p>
          <p><strong>状态：</strong>{{ latestSubmission.status }}</p>
          <p><strong>得分：</strong>{{ latestSubmission.teacher_score ?? latestSubmission.ai_score ?? '-' }}</p>

          <template v-if="assignment.assignment_type === 'code'">
            <p><strong>判题摘要：</strong>{{ latestSubmission.ai_feedback || latestSubmission.teacher_comment || '-' }}</p>
            <template v-if="parseJudgeReport(latestSubmission.ai_rationale)">
              <p><strong>通过率：</strong>{{ judgePassText(parseJudgeReport(latestSubmission.ai_rationale)!) }}</p>
              <div class="industry-table-wrap">
                <table class="industry-table">
                  <thead>
                    <tr>
                      <th>#</th>
                      <th>结果</th>
                      <th>输入</th>
                      <th>期望</th>
                      <th>实际</th>
                      <th>错误信息</th>
                    </tr>
                  </thead>
                  <tbody>
                    <tr v-for="detail in parseJudgeReport(latestSubmission.ai_rationale)!.details" :key="detail.case">
                      <td>{{ detail.case }}</td>
                      <td>
                        <span :class="['verdict-chip', detail.ok ? 'ok' : 'fail']">{{ caseVerdict(detail) }}</span>
                      </td>
                      <td><pre class="oj-pre">{{ detail.input }}</pre></td>
                      <td><pre class="oj-pre">{{ detail.expected }}</pre></td>
                      <td><pre class="oj-pre">{{ detail.actual }}</pre></td>
                      <td><pre class="oj-pre">{{ detail.stderr || '-' }}</pre></td>
                    </tr>
                  </tbody>
                </table>
              </div>
            </template>
          </template>
        </section>
      </template>
    </section>

    <section v-if="notice" class="card-panel state-card">{{ notice }}</section>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import { useRoute, useRouter } from "vue-router";
import {
  homeworkGetAssignment,
  homeworkListMySubmissions,
  homeworkSubmitAssignment,
} from "../../api/homework";
import type { HomeworkAssignment, HomeworkSubmission } from "../../types/homework";

const route = useRoute();
const router = useRouter();

const assignment = ref<HomeworkAssignment | null>(null);
const loading = ref(false);
const submitting = ref(false);
const error = ref("");
const notice = ref("");
const answerMap = ref<Record<number, string>>({});
const latestSubmission = ref<HomeworkSubmission | null>(null);

const assignmentId = computed(() => String(route.params.assignmentId || ""));

type JudgeCaseDetail = {
  case: number;
  ok: boolean;
  input: string;
  expected: string;
  actual: string;
  stderr?: string;
};

type JudgeReport = {
  passed: number;
  total: number;
  pass_rate: number;
  details: JudgeCaseDetail[];
};

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
        input: String(item.input ?? ""),
        expected: String(item.expected ?? ""),
        actual: String(item.actual ?? ""),
        stderr: String(item.stderr ?? ""),
      }));
    return {
      passed: Number(parsed.passed ?? 0),
      total: Number(parsed.total ?? 0),
      pass_rate: Number(parsed.pass_rate ?? 0),
      details,
    };
  } catch {
    return null;
  }
}

function judgePassText(report: JudgeReport) {
  return `${report.passed}/${report.total} (${Math.round((report.pass_rate || 0) * 100)}%)`;
}

function caseVerdict(detail: JudgeCaseDetail) {
  return detail.ok ? "Accepted" : "Wrong Answer";
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

    const latest = mySubRes.submissions[0];
    latestSubmission.value = latest || null;
    const nextMap: Record<number, string> = {};
    if (latest && latest.status !== "graded" && Array.isArray(latest.answers)) {
      for (const item of latest.answers) {
        const idx = Number(item.question_index ?? -1);
        if (idx >= 0) {
          nextMap[idx] = String(item.answer ?? "");
        }
      }
    }

    for (let i = 0; i < (detailRes.assignment.questions?.length ?? 0); i += 1) {
      if (!(i in nextMap)) {
        nextMap[i] = "";
      }
    }
    answerMap.value = nextMap;
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

  const answers = assignment.value.questions.map((_, idx) => ({
    question_index: idx,
    answer: (answerMap.value[idx] || "").trim(),
  }));

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
  max-width: 220px;
}

@media (max-width: 900px) {
  .summary-grid {
    grid-template-columns: 1fr;
  }
}
</style>
