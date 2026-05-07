<template>
  <div class="homework-student-shell">
    <!-- 页面头部 -->
    <div class="student-homework-v2-header">
      <div>
        <h1>📝 我的作业</h1>
        <p class="student-homework-v2-desc">查看和提交课程作业</p>
      </div>
      <button class="ghost-btn" type="button" @click="loadAll">刷新</button>
    </div>

    <!-- 统计概览 -->
    <div class="student-homework-v2-stats">
      <div class="student-homework-v2-stat-item">
        <div class="student-homework-v2-stat-value">{{ totalAssignments }}</div>
        <div class="student-homework-v2-stat-label">全部作业</div>
      </div>
      <div class="student-homework-v2-stat-item">
        <div class="student-homework-v2-stat-value">{{ pendingCount }}</div>
        <div class="student-homework-v2-stat-label">待完成</div>
      </div>
      <div class="student-homework-v2-stat-item">
        <div class="student-homework-v2-stat-value">{{ submittedCount }}</div>
        <div class="student-homework-v2-stat-label">已提交</div>
      </div>
      <div class="student-homework-v2-stat-item">
        <div class="student-homework-v2-stat-value">{{ gradedCount }}</div>
        <div class="student-homework-v2-stat-label">已评分</div>
      </div>
      <div class="student-homework-v2-stat-item student-homework-v2-stat-item-overdue">
        <div class="student-homework-v2-stat-value">{{ overdueCount }}</div>
        <div class="student-homework-v2-stat-label">已逾期</div>
      </div>
    </div>

    <!-- 筛选器 -->
    <div class="student-homework-v2-filters">
      <input v-model.trim="filters.course_id" class="input input-inline" type="text" placeholder="课程ID筛选" />
      <input v-model.trim="filters.node_name" class="input input-inline" type="text" placeholder="章节筛选" />
    </div>

    <!-- 作业标签 -->
    <div class="student-homework-v2-tabs">
      <button
        class="student-homework-v2-tab"
        :class="{ active: activeTab === 'all' }"
        @click="activeTab = 'all'"
      >
        全部
      </button>
      <button
        class="student-homework-v2-tab"
        :class="{ active: activeTab === 'pending' }"
        @click="activeTab = 'pending'"
      >
        待完成
      </button>
      <button
        class="student-homework-v2-tab"
        :class="{ active: activeTab === 'submitted' }"
        @click="activeTab = 'submitted'"
      >
        已提交
      </button>
      <button
        class="student-homework-v2-tab"
        :class="{ active: activeTab === 'graded' }"
        @click="activeTab = 'graded'"
      >
        已评分
      </button>
      <button
        class="student-homework-v2-tab"
        :class="{ active: activeTab === 'overdue' }"
        @click="activeTab = 'overdue'"
      >
        已逾期
      </button>
    </div>

    <!-- 作业卡片列表 -->
    <div class="student-homework-v2-list">
      <div
        v-for="item in filteredAssignments"
        :key="item.id"
        class="student-homework-v2-card"
      >
        <div class="student-homework-v2-card-header">
          <div>
            <div class="student-homework-v2-card-title">{{ item.title }}</div>
            <div class="student-homework-v2-card-meta">
              <span class="student-homework-v2-meta-item">
                <span class="student-homework-v2-meta-label">题型：</span>
                {{ typeLabel(item.assignment_type) }}
              </span>
              <span class="student-homework-v2-meta-item">
                <span class="student-homework-v2-meta-label">课程：</span>
                {{ item.course_id || "-" }}
              </span>
              <span class="student-homework-v2-meta-item">
                <span class="student-homework-v2-meta-label">章节：</span>
                {{ item.node_name || "-" }}
              </span>
              <span v-if="item.class_name" class="student-homework-v2-meta-item">
                <span class="student-homework-v2-meta-label">班级：</span>
                {{ item.class_name }}
              </span>
              <span class="student-homework-v2-meta-item">
                <span class="student-homework-v2-meta-label">截止：</span>
                {{ formatTime(item.due_at) }}
              </span>
              <span class="student-homework-v2-meta-item">
                <span class="student-homework-v2-meta-label">题目数：</span>
                {{ item.questions?.length ?? 0 }}
              </span>
            </div>
          </div>
          <div class="student-homework-v2-card-actions">
            <span
              class="student-homework-v2-status"
              :class="getStatusClass(item.id)"
            >
              {{ getStatusLabel(item.id) }}
            </span>
            <button class="ghost-btn" type="button" @click="openQuickModal(item.id)">快速作答</button>
            <button class="ghost-btn" type="button" @click="goToDetail(item.id)">查看并提交</button>
          </div>
        </div>
      </div>

      <div v-if="!filteredAssignments.length" class="student-homework-v2-empty">
        <div class="student-homework-v2-empty-icon">📭</div>
        <div class="student-homework-v2-empty-text">暂无作业</div>
      </div>
    </div>

    <!-- 我的提交记录 -->
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
import { computed, onMounted, ref } from "vue";
import { useRoute, useRouter } from "vue-router";
import {
  homeworkGetAssignment,
  homeworkListAssignmentsByFilter,
  homeworkListMySubmissions,
  homeworkSubmitAssignment,
} from "../../api/homework";
import type { HomeworkAssignment, HomeworkSubmission } from "../../types/homework";

const router = useRouter();
const route = useRoute();
const assignments = ref<HomeworkAssignment[]>([]);
const mySubmissions = ref<HomeworkSubmission[]>([]);
const notice = ref("");
const error = ref("");
const filters = ref({
  course_id: "",
  node_name: "",
});
const activeTab = ref<"all" | "pending" | "submitted" | "graded" | "overdue">("all");
const quickModal = ref({
  visible: false,
  loading: false,
  submitting: false,
  assignment: null as HomeworkAssignment | null,
  answerMap: {} as Record<number, string>,
});

// 统计数据
const totalAssignments = computed(() => assignments.value.length);

const pendingCount = computed(() => {
  return assignments.value.filter((item) => {
    const submission = mySubmissions.value.find((s) => s.assignment_id === item.id);
    return !submission;
  }).length;
});

const submittedCount = computed(() => {
  return assignments.value.filter((item) => {
    const submission = mySubmissions.value.find((s) => s.assignment_id === item.id);
    return submission && submission.status !== "graded";
  }).length;
});

const gradedCount = computed(() => {
  return assignments.value.filter((item) => {
    const submission = mySubmissions.value.find((s) => s.assignment_id === item.id);
    return submission && submission.status === "graded";
  }).length;
});

// 已逾期作业数量
const overdueCount = computed(() => {
  const now = new Date();
  return assignments.value.filter((item) => {
    // 必须有截止时间
    if (!item.due_at) return false;
    
    // 检查是否已提交或已评分
    const submission = mySubmissions.value.find((s) => s.assignment_id === item.id);
    if (submission) return false; // 已提交或已评分，不计入逾期
    
    // 检查是否已过期
    const dueDate = new Date(item.due_at);
    return now > dueDate;
  }).length;
});

// 根据标签筛选作业
const filteredAssignments = computed(() => {
  let filtered = assignments.value;

  if (activeTab.value === "pending") {
    filtered = filtered.filter((item) => {
      const submission = mySubmissions.value.find((s) => s.assignment_id === item.id);
      return !submission;
    });
  } else if (activeTab.value === "submitted") {
    filtered = filtered.filter((item) => {
      const submission = mySubmissions.value.find((s) => s.assignment_id === item.id);
      return submission && submission.status !== "graded";
    });
  } else if (activeTab.value === "graded") {
    filtered = filtered.filter((item) => {
      const submission = mySubmissions.value.find((s) => s.assignment_id === item.id);
      return submission && submission.status === "graded";
    });
  } else if (activeTab.value === "overdue") {
    const now = new Date();
    filtered = filtered.filter((item) => {
      // 必须有截止时间
      if (!item.due_at) return false;
      
      // 检查是否已提交或已评分
      const submission = mySubmissions.value.find((s) => s.assignment_id === item.id);
      if (submission) return false; // 已提交或已评分，不显示为逾期
      
      // 检查是否已过期
      const dueDate = new Date(item.due_at);
      return now > dueDate;
    });
  }

  return filtered;
});

// 获取作业状态
function getStatusLabel(assignmentId: string): string {
  const assignment = assignments.value.find((a) => a.id === assignmentId);
  const submission = mySubmissions.value.find((s) => s.assignment_id === assignmentId);
  
  // 检查是否逾期（未提交且已过截止时间）
  if (!submission && assignment?.due_at) {
    const now = new Date();
    const dueDate = new Date(assignment.due_at);
    if (now > dueDate) {
      return "已逾期";
    }
  }
  
  if (!submission) return "待提交";
  if (submission.status === "graded") return "已评分";
  return "已提交";
}

function getStatusClass(assignmentId: string): string {
  const assignment = assignments.value.find((a) => a.id === assignmentId);
  const submission = mySubmissions.value.find((s) => s.assignment_id === assignmentId);
  
  // 检查是否逾期（未提交且已过截止时间）
  if (!submission && assignment?.due_at) {
    const now = new Date();
    const dueDate = new Date(assignment.due_at);
    if (now > dueDate) {
      return "status-overdue";
    }
  }
  
  if (!submission) return "status-pending";
  if (submission.status === "graded") return "status-graded";
  return "status-submitted";
}

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
  const res = await homeworkListAssignmentsByFilter({
    only_mine: false,
    course_id: filters.value.course_id || undefined,
    node_name: filters.value.node_name || undefined,
  });
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

onMounted(() => {
  if (typeof route.query.course_id === "string") {
    filters.value.course_id = route.query.course_id;
  }
  if (typeof route.query.node_name === "string") {
    filters.value.node_name = route.query.node_name;
  }
  loadAll();
});
</script>

<style scoped>
.homework-student-shell {
  display: grid;
  gap: 20px;
}

/* 页面头部 */
.student-homework-v2-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  padding: 24px 32px;
  border-radius: 16px;
  background: linear-gradient(135deg, #ffffff 0%, #f8fbff 100%);
  border: 1px solid #e2e8f0;
  box-shadow: 0 4px 12px rgba(15, 23, 42, 0.04);
}

.student-homework-v2-header h1 {
  margin: 0 0 8px 0;
  font-size: 32px;
  line-height: 1.2;
  color: #0f172a;
}

.student-homework-v2-desc {
  margin: 0;
  color: #64748b;
  font-size: 15px;
  line-height: 1.6;
}

/* 统计概览 */
.student-homework-v2-stats {
  display: grid;
  grid-template-columns: repeat(5, 1fr);
  gap: 16px;
}

.student-homework-v2-stat-item {
  padding: 20px;
  border-radius: 12px;
  background: linear-gradient(135deg, #ffffff 0%, #f8fbff 100%);
  border: 1px solid #e2e8f0;
  text-align: center;
  transition: all 0.2s;
}

.student-homework-v2-stat-item:hover {
  transform: translateY(-2px);
  box-shadow: 0 8px 16px rgba(37, 99, 235, 0.12);
}

.student-homework-v2-stat-item-overdue {
  background: linear-gradient(135deg, #fff5f5 0%, #ffe4e6 100%);
  border-color: #fecaca;
}

.student-homework-v2-stat-item-overdue:hover {
  box-shadow: 0 8px 16px rgba(239, 68, 68, 0.12);
}

.student-homework-v2-stat-item-overdue .student-homework-v2-stat-value {
  color: #dc2626;
}

.student-homework-v2-stat-value {
  font-size: 32px;
  font-weight: 700;
  color: #2563eb;
  line-height: 1.2;
  margin-bottom: 8px;
}

.student-homework-v2-stat-label {
  font-size: 14px;
  color: #64748b;
  font-weight: 500;
}

/* 筛选器 */
.student-homework-v2-filters {
  display: flex;
  gap: 12px;
  align-items: center;
}

/* 作业标签 */
.student-homework-v2-tabs {
  display: flex;
  gap: 8px;
  padding: 8px;
  background: #f8fafc;
  border-radius: 12px;
  border: 1px solid #e2e8f0;
}

.student-homework-v2-tab {
  flex: 1;
  padding: 10px 20px;
  border: none;
  background: transparent;
  color: #64748b;
  font-size: 14px;
  font-weight: 600;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.2s;
}

.student-homework-v2-tab:hover {
  background: #ffffff;
  color: #2563eb;
}

.student-homework-v2-tab.active {
  background: linear-gradient(135deg, #2563eb 0%, #1d4ed8 100%);
  color: #ffffff;
  box-shadow: 0 4px 8px rgba(37, 99, 235, 0.24);
}

/* 作业卡片列表 */
.student-homework-v2-list {
  display: grid;
  gap: 16px;
}

.student-homework-v2-card {
  padding: 20px;
  border-radius: 12px;
  background: #ffffff;
  border: 1px solid #e2e8f0;
  transition: all 0.2s;
}

.student-homework-v2-card:hover {
  border-color: #bfdbfe;
  box-shadow: 0 8px 16px rgba(37, 99, 235, 0.12);
  transform: translateY(-2px);
}

.student-homework-v2-card-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 20px;
}

.student-homework-v2-card-title {
  font-size: 18px;
  font-weight: 700;
  color: #0f172a;
  margin-bottom: 12px;
  line-height: 1.4;
}

.student-homework-v2-card-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 16px;
  font-size: 14px;
  color: #64748b;
}

.student-homework-v2-meta-item {
  display: inline-flex;
  align-items: center;
  gap: 4px;
}

.student-homework-v2-meta-label {
  font-weight: 600;
  color: #475569;
}

.student-homework-v2-card-actions {
  display: flex;
  flex-direction: column;
  gap: 8px;
  align-items: flex-end;
}

.student-homework-v2-status {
  padding: 6px 14px;
  border-radius: 999px;
  font-size: 13px;
  font-weight: 600;
  white-space: nowrap;
}

.student-homework-v2-status.status-pending {
  background: #fef3c7;
  color: #92400e;
}

.student-homework-v2-status.status-submitted {
  background: #dbeafe;
  color: #1e40af;
}

.student-homework-v2-status.status-graded {
  background: #d1fae5;
  color: #065f46;
}

.student-homework-v2-status.status-overdue {
  background: #fee2e2;
  color: #991b1b;
  border: 1px solid #fca5a5;
}

/* 空状态 */
.student-homework-v2-empty {
  padding: 60px 20px;
  text-align: center;
  background: #f8fafc;
  border-radius: 12px;
  border: 1px dashed #cbd5e1;
}

.student-homework-v2-empty-icon {
  font-size: 64px;
  margin-bottom: 16px;
}

.student-homework-v2-empty-text {
  font-size: 16px;
  color: #64748b;
  font-weight: 500;
}

/* 响应式设计 */
@media (max-width: 1024px) {
  .student-homework-v2-header {
    flex-direction: column;
    gap: 16px;
  }

  .student-homework-v2-stats {
    grid-template-columns: repeat(3, 1fr);
  }

  .student-homework-v2-card-header {
    flex-direction: column;
  }

  .student-homework-v2-card-actions {
    width: 100%;
    flex-direction: row;
    justify-content: flex-start;
  }
}

@media (max-width: 640px) {
  .student-homework-v2-stats {
    grid-template-columns: 1fr;
  }

  .student-homework-v2-tabs {
    flex-direction: column;
  }

  .student-homework-v2-filters {
    flex-direction: column;
    width: 100%;
  }

  .student-homework-v2-card-meta {
    flex-direction: column;
    gap: 8px;
  }

  .student-homework-v2-card-actions {
    flex-direction: column;
    align-items: stretch;
  }
}

.actions-row {
  display: flex;
  gap: 8px;
  align-items: center;
}

.input-inline {
  width: 180px;
  margin-top: 0;
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
