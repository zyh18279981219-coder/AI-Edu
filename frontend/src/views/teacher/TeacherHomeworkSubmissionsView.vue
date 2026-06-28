<template>
  <div class="homework-submissions-shell">
    <section class="card-panel">
      <div class="section-head">
        <h3>提交列表</h3>
        <div class="actions-row">
          <button class="ghost-btn" type="button" @click="loadData">刷新</button>
          <button class="ghost-btn" type="button" @click="router.push({ name: 'teacher-homework' })">返回作业列表</button>
        </div>
      </div>

      <p v-if="assignment"><strong>作业：</strong>{{ assignment.title }} | {{ assignment.class_name || '-' }}</p>

      <div class="industry-table-wrap">
        <table class="industry-table">
          <thead>
            <tr>
              <th>学生</th>
              <th>提交时间</th>
              <th>状态</th>
              <th>AI建议分</th>
              <th>终审分</th>
              <th>操作</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="s in submissions" :key="s.id">
              <td>{{ s.student_username }}</td>
              <td>{{ formatTime(s.submitted_at) }}</td>
              <td>{{ s.status }}</td>
              <td>{{ s.ai_score ?? '-' }}</td>
              <td>{{ s.teacher_score ?? '-' }}</td>
              <td>
                <button
                  class="ghost-btn small"
                  type="button"
                  @click="router.push({ name: 'teacher-homework-grade', params: { submissionId: s.id } })"
                >
                  批改详情
                </button>
              </td>
            </tr>
            <tr v-if="!submissions.length">
              <td colspan="6">暂无提交</td>
            </tr>
          </tbody>
        </table>
      </div>
    </section>

    <section v-if="error" class="card-panel state-card error-state">{{ error }}</section>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import { useRoute, useRouter } from "vue-router";
import { homeworkGetAssignment, homeworkListSubmissions } from "../../api/homework";
import type { HomeworkAssignment, HomeworkSubmission } from "../../types/homework";

const route = useRoute();
const router = useRouter();

const assignment = ref<HomeworkAssignment | null>(null);
const submissions = ref<HomeworkSubmission[]>([]);
const error = ref("");

const assignmentId = computed(() => String(route.params.assignmentId || ""));

function formatTime(value?: string | null) {
  if (!value) return "-";
  return new Date(value).toLocaleString();
}

async function loadData() {
  if (!assignmentId.value) return;
  error.value = "";
  try {
    const [assignmentRes, submissionsRes] = await Promise.all([
      homeworkGetAssignment(assignmentId.value),
      homeworkListSubmissions(assignmentId.value),
    ]);
    assignment.value = assignmentRes.assignment;
    submissions.value = submissionsRes.submissions;
  } catch (e) {
    error.value = e instanceof Error ? e.message : "加载提交列表失败";
  }
}

onMounted(loadData);
</script>

<style scoped>
.homework-submissions-shell {
  display: grid;
  gap: 16px;
}

.actions-row {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
}

.ghost-btn.small {
  padding: 4px 8px;
}
</style>
