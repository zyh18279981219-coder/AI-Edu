<template>
  <div class="teacher-intervention-detail-shell">
    <section class="card-panel">
      <div class="section-head">
        <h3>任务包完成详情与判题</h3>
        <div class="actions-row">
          <button class="ghost-btn" type="button" @click="loadDetail">刷新</button>
          <button class="ghost-btn" type="button" @click="router.push({ name: 'teacher-intervention' })">返回列表</button>
        </div>
      </div>

      <section v-if="loading" class="state-card">加载中...</section>
      <section v-else-if="error" class="state-card error-state">{{ error }}</section>
      <template v-else-if="pkg">
        <div class="summary-grid">
          <div><strong>包ID：</strong>{{ pkg.id }}</div>
          <div><strong>学生：</strong>{{ pkg.student_username }}</div>
          <div><strong>状态：</strong>{{ statusLabel(pkg.student_status) }}</div>
          <div><strong>自动进度：</strong>{{ progressText }}</div>
          <div><strong>AI均分：</strong>{{ pkg.score_summary?.average_ai_score ?? "-" }}</div>
          <div><strong>教师均分：</strong>{{ pkg.score_summary?.average_teacher_score ?? "-" }}</div>
          <div><strong>最终均分：</strong>{{ pkg.score_summary?.average_final_score ?? "-" }}</div>
          <div><strong>学生总体备注：</strong>{{ pkg.student_note || "-" }}</div>
        </div>

        <div class="industry-table-wrap">
          <table class="industry-table">
            <thead>
              <tr>
                <th>#</th>
                <th>题目</th>
                <th>学生答案</th>
                <th>本题备注</th>
                <th>AI判题</th>
                <th>教师评分</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="(q, idx) in pkg.questions" :key="q.id">
                <td>{{ idx + 1 }}</td>
                <td>
                  <p><strong>{{ q.title }}</strong></p>
                  <p class="muted">题型：{{ questionTypeLabel(q.question_type) }}</p>
                  <p class="multiline">{{ q.prompt }}</p>
                </td>
                <td>
                  <pre class="answer-pre">{{ answerRow(q.id)?.answer || "未作答" }}</pre>
                </td>
                <td>
                  <pre class="answer-pre">{{ answerRow(q.id)?.note || "-" }}</pre>
                </td>
                <td>
                  <div>分数：{{ gradeRow(q.id)?.ai_score ?? "-" }}</div>
                  <div class="muted multiline">{{ gradeRow(q.id)?.ai_feedback || "-" }}</div>
                  <div v-if="gradeRow(q.id)?.ai_detail?.criteria?.length" class="criteria-list">
                    <div v-for="(item, cIdx) in gradeRow(q.id)?.ai_detail?.criteria || []" :key="`${q.id}-criteria-${cIdx}`">
                      {{ item.name }}：{{ item.score }}/{{ item.full_score }}（{{ item.reason }}）
                    </div>
                  </div>
                  <div v-if="gradeRow(q.id)?.ai_detail?.match" class="muted">
                    匹配：{{ gradeRow(q.id)?.ai_detail?.match?.is_correct ? "正确" : "未完全匹配" }}
                    （期望 {{ gradeRow(q.id)?.ai_detail?.match?.expected || "-" }}，提交 {{ gradeRow(q.id)?.ai_detail?.match?.normalized_answer || "-" }}）
                  </div>
                  <div v-if="gradeRow(q.id)?.ai_detail?.code" class="muted">
                    测试点：{{ gradeRow(q.id)?.ai_detail?.code?.case_passed }}/{{ gradeRow(q.id)?.ai_detail?.code?.case_total }}
                  </div>
                </td>
                <td>
                  <label class="field">
                    <span>教师分(0-100)</span>
                    <input v-model.number="gradeDraft[q.id].teacher_score" type="number" min="0" max="100" step="1" class="input" />
                  </label>
                  <label class="field">
                    <span>评语</span>
                    <textarea v-model="gradeDraft[q.id].teacher_comment" rows="3" class="input input-textarea" />
                  </label>
                  <div class="actions-row">
                    <button class="ghost-btn" type="button" :disabled="busyQuestionId === q.id" @click="saveGrade(q.id)">
                      {{ busyQuestionId === q.id ? "提交中..." : "提交教师评分" }}
                    </button>
                  </div>
                  <div class="muted">当前教师分：{{ gradeRow(q.id)?.teacher_score ?? "-" }}</div>
                </td>
              </tr>
              <tr v-if="!pkg.questions?.length">
                <td colspan="6">暂无题目</td>
              </tr>
            </tbody>
          </table>
        </div>
      </template>
    </section>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import { useRoute, useRouter } from "vue-router";
import { interventionTeacherGradeQuestion, interventionTeacherPackageDetail } from "../../api/intervention";
import type { InterventionPackage, InterventionQuestionAnswer, InterventionQuestionGrade } from "../../types/intervention";

const route = useRoute();
const router = useRouter();
const loading = ref(false);
const error = ref("");
const pkg = ref<InterventionPackage | null>(null);
const busyQuestionId = ref("");
const gradeDraft = ref<Record<string, { teacher_score: number; teacher_comment: string }>>({});

const packageId = computed(() => String(route.params.packageId || ""));

const progressText = computed(() => {
  if (!pkg.value) return "-";
  const rate = Math.round((pkg.value.progress?.completion_rate || 0) * 100);
  const answered = pkg.value.progress?.answered_questions ?? 0;
  const total = pkg.value.progress?.total_questions ?? (pkg.value.questions?.length || 0);
  return `${rate}% (${answered}/${total})`;
});

function statusLabel(status: string) {
  if (status === "accepted") return "已接受";
  if (status === "declined") return "暂不做";
  if (status === "in_progress") return "进行中";
  if (status === "completed") return "已完成";
  return "待处理";
}

function questionTypeLabel(type?: string) {
  if (type === "fill_blank") return "填空题";
  if (type === "single_choice") return "单选题";
  if (type === "multiple_choice") return "多选题";
  if (type === "code") return "编程题";
  return "主观题";
}

function answerRow(questionId: string): InterventionQuestionAnswer | null {
  return (pkg.value?.answers || []).find((item) => item.question_id === questionId) || null;
}

function gradeRow(questionId: string): InterventionQuestionGrade | null {
  return (pkg.value?.grades || []).find((item) => item.question_id === questionId) || null;
}

function ensureDraft() {
  for (const question of pkg.value?.questions || []) {
    if (gradeDraft.value[question.id]) continue;
    const row = gradeRow(question.id);
    gradeDraft.value[question.id] = {
      teacher_score: Number(row?.teacher_score ?? row?.ai_score ?? 60),
      teacher_comment: row?.teacher_comment || "",
    };
  }
}

async function loadDetail() {
  if (!packageId.value) return;
  loading.value = true;
  error.value = "";
  try {
    const res = await interventionTeacherPackageDetail(packageId.value);
    pkg.value = res.package;
    ensureDraft();
  } catch (e) {
    error.value = e instanceof Error ? e.message : "加载详情失败";
  } finally {
    loading.value = false;
  }
}

async function saveGrade(questionId: string) {
  if (!pkg.value) return;
  const draft = gradeDraft.value[questionId];
  if (!draft) return;
  busyQuestionId.value = questionId;
  error.value = "";
  try {
    await interventionTeacherGradeQuestion(pkg.value.id, {
      question_id: questionId,
      teacher_score: Number(draft.teacher_score),
      teacher_comment: draft.teacher_comment,
    });
    await loadDetail();
  } catch (e) {
    error.value = e instanceof Error ? e.message : "提交评分失败";
  } finally {
    busyQuestionId.value = "";
  }
}

onMounted(loadDetail);
</script>

<style scoped>
.teacher-intervention-detail-shell {
  display: grid;
  gap: 16px;
}

.summary-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
  gap: 8px;
  margin-bottom: 12px;
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

.answer-pre {
  white-space: pre-wrap;
  margin: 0;
  max-width: 320px;
}

.criteria-list {
  margin-top: 6px;
  display: grid;
  gap: 4px;
  font-size: 12px;
}
</style>

