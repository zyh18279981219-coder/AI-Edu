<template>
  <div class="homework-student-shell">
    <section class="card-panel">
      <div class="section-head">
        <h3>我的作业列表</h3>
        <button class="ghost-btn" type="button" @click="loadAll">刷新</button>
      </div>

      <div class="industry-table-wrap">
        <table class="industry-table">
          <thead>
            <tr>
              <th>标题</th>
              <th>题型</th>
              <th>班级</th>
              <th>截止时间</th>
              <th>状态</th>
              <th>题目数</th>
              <th>操作</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="item in assignments" :key="item.id">
              <td>{{ item.title }}</td>
              <td>{{ typeLabel(item.assignment_type) }}</td>
              <td>{{ item.class_name || "-" }}</td>
              <td>{{ formatTime(item.due_at) }}</td>
              <td>{{ item.status }}</td>
              <td>{{ item.questions?.length ?? 0 }}</td>
              <td>
                <button class="ghost-btn" type="button" @click="openQuickModal(item.id)">快速作答</button>
                <button class="ghost-btn" type="button" @click="goToDetail(item.id)">查看并提交</button>
              </td>
            </tr>
            <tr v-if="!assignments.length">
              <td colspan="7">暂无作业</td>
            </tr>
          </tbody>
        </table>
      </div>
    </section>

    <section class="card-panel">
      <div class="section-head">
        <h3>我的提交记录</h3>
      </div>

      <div class="industry-table-wrap">
        <table class="industry-table">
          <thead>
            <tr>
              <th>作业ID</th>
              <th>提交时间</th>
              <th>状态</th>
              <th>AI建议分</th>
              <th>教师终审分</th>
              <th>教师评语</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="s in mySubmissions" :key="s.id">
              <td>{{ s.assignment_id }}</td>
              <td>{{ formatTime(s.submitted_at) }}</td>
              <td>{{ s.status }}</td>
              <td>{{ s.ai_score ?? "-" }}</td>
              <td>{{ s.teacher_score ?? "-" }}</td>
              <td>{{ s.teacher_comment || "-" }}</td>
            </tr>
            <tr v-if="!mySubmissions.length">
              <td colspan="6">暂无提交记录</td>
            </tr>
          </tbody>
        </table>
      </div>
    </section>

    <section v-if="notice" class="card-panel state-card">{{ notice }}</section>
    <section v-if="error" class="card-panel state-card error-state">{{ error }}</section>

    <div v-if="quickModal.visible" class="modal-mask" @click.self="quickModal.visible = false">
      <div class="modal-card">
        <div class="section-head">
          <h3>快速作答</h3>
          <button class="ghost-btn" type="button" @click="quickModal.visible = false">关闭</button>
        </div>

        <section v-if="quickModal.loading" class="state-card">加载中...</section>
        <template v-else-if="quickModal.assignment">
          <p><strong>{{ quickModal.assignment.title }}</strong></p>
          <p class="muted">{{ quickModal.assignment.description || '无简介' }}</p>

          <div v-for="(q, idx) in quickModal.assignment.questions" :key="idx" class="question-card">
            <p><strong>{{ idx + 1 }}. {{ q.title }}</strong></p>
            <p class="multiline">{{ q.prompt }}</p>

            <template v-if="quickModal.assignment.assignment_type === 'objective'">
              <div class="option-grid">
                <label v-for="opt in (q.options || ['A. 正确', 'B. 错误'])" :key="opt" class="option-item">
                  <input type="radio" :name="`quick-${idx}`" :value="parseOptionValue(opt)" v-model="quickModal.answerMap[idx]" />
                  {{ opt }}
                </label>
              </div>
            </template>
            <template v-else-if="quickModal.assignment.assignment_type === 'choice'">
              <div class="option-grid">
                <label v-for="opt in (q.options || [])" :key="opt" class="option-item">
                  <input
                    type="checkbox"
                    :value="parseOptionValue(opt)"
                    :checked="isQuickSelected(idx, parseOptionValue(opt))"
                    @change="toggleQuickChoice(idx, parseOptionValue(opt), ($event.target as HTMLInputElement).checked)"
                  />
                  {{ opt }}
                </label>
              </div>
            </template>
            <template v-else>
              <textarea
                v-model="quickModal.answerMap[idx]"
                class="input input-textarea"
                rows="6"
                :placeholder="quickModal.assignment.assignment_type === 'code' ? '请输入可运行代码' : '请输入作答'"
              />
            </template>
          </div>

          <div class="actions-row">
            <button class="ghost-btn" type="button" :disabled="quickModal.submitting" @click="submitQuickModal">
              {{ quickModal.submitting ? '提交中...' : '提交全部题目' }}
            </button>
          </div>
        </template>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from "vue";
import { useRouter } from "vue-router";
import {
  homeworkGetAssignment,
  homeworkListAssignmentsForStudent,
  homeworkListMySubmissions,
  homeworkSubmitAssignment,
} from "../../api/homework";
import type { HomeworkAssignment, HomeworkSubmission } from "../../types/homework";

const router = useRouter();
const assignments = ref<HomeworkAssignment[]>([]);
const mySubmissions = ref<HomeworkSubmission[]>([]);
const notice = ref("");
const error = ref("");
const quickModal = ref({
  visible: false,
  loading: false,
  submitting: false,
  assignment: null as HomeworkAssignment | null,
  answerMap: {} as Record<number, string>,
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

function parseOptionValue(optionText: string) {
  const text = String(optionText || "").trim();
  const matched = text.match(/^([A-Z])\./i);
  return matched ? matched[1].toUpperCase() : text;
}

function isQuickSelected(questionIndex: number, value: string) {
  const current = String(quickModal.value.answerMap[questionIndex] || "");
  return current.split(",").map((x) => x.trim()).filter(Boolean).includes(value);
}

function toggleQuickChoice(questionIndex: number, value: string, checked: boolean) {
  const current = String(quickModal.value.answerMap[questionIndex] || "")
    .split(",")
    .map((x) => x.trim())
    .filter(Boolean);
  const next = checked ? Array.from(new Set([...current, value])) : current.filter((x) => x !== value);
  quickModal.value.answerMap[questionIndex] = next.join(",");
}

function resetMessage() {
  notice.value = "";
  error.value = "";
}

async function loadAssignments() {
  const res = await homeworkListAssignmentsForStudent();
  assignments.value = res.assignments;
}

async function loadMySubmissions() {
  const res = await homeworkListMySubmissions();
  mySubmissions.value = res.submissions;
}

async function loadAll() {
  resetMessage();
  try {
    await Promise.all([loadAssignments(), loadMySubmissions()]);
  } catch (e) {
    error.value = e instanceof Error ? e.message : "加载作业失败";
  }
}

function goToDetail(assignmentId: string) {
  router.push({ name: "student-homework-detail", params: { assignmentId } });
}

async function openQuickModal(assignmentId: string) {
  quickModal.value.visible = true;
  quickModal.value.loading = true;
  quickModal.value.assignment = null;
  quickModal.value.answerMap = {};
  try {
    const [detailRes, mySubRes] = await Promise.all([
      homeworkGetAssignment(assignmentId),
      homeworkListMySubmissions(assignmentId),
    ]);
    quickModal.value.assignment = detailRes.assignment;
    const answerMap: Record<number, string> = {};
    const latest = mySubRes.submissions[0];
    if (latest && latest.status !== "graded" && Array.isArray(latest.answers)) {
      for (const ans of latest.answers) {
        const idx = Number(ans.question_index ?? -1);
        if (idx >= 0) {
          answerMap[idx] = String(ans.answer ?? "");
        }
      }
    }
    for (let i = 0; i < (detailRes.assignment.questions?.length ?? 0); i += 1) {
      if (!(i in answerMap)) {
        answerMap[i] = "";
      }
    }
    quickModal.value.answerMap = answerMap;
  } catch (e) {
    error.value = e instanceof Error ? e.message : "加载作业详情失败";
  } finally {
    quickModal.value.loading = false;
  }
}

async function submitQuickModal() {
  const assignment = quickModal.value.assignment;
  if (!assignment) return;
  const answers = assignment.questions.map((_, idx) => ({
    question_index: idx,
    answer: String(quickModal.value.answerMap[idx] || "").trim(),
  }));
  const emptyCount = answers.filter((item) => !item.answer).length;
  if (emptyCount > 0) {
    error.value = `还有 ${emptyCount} 道题未作答`;
    return;
  }

  quickModal.value.submitting = true;
  try {
    await homeworkSubmitAssignment(assignment.id, answers);
    notice.value = "提交成功";
    quickModal.value.visible = false;
    await loadMySubmissions();
  } catch (e) {
    error.value = e instanceof Error ? e.message : "提交失败";
  } finally {
    quickModal.value.submitting = false;
  }
}

onMounted(loadAll);
</script>

<style scoped>
.homework-student-shell {
  display: grid;
  gap: 16px;
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
  width: min(920px, 96vw);
  max-height: 90vh;
  overflow: auto;
  background: #fff;
  border-radius: 12px;
  padding: 14px;
}

.question-card {
  border: 1px solid #e8eef6;
  border-radius: 10px;
  padding: 10px;
  margin-top: 10px;
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

.actions-row {
  display: flex;
  justify-content: flex-end;
  margin-top: 12px;
}

.multiline {
  white-space: pre-wrap;
}
</style>
