<template>
  <div class="admin-shell">
    <PageHero
      eyebrow="Admin Workspace"
      title="管理端总览"
      description="统一查看教师与学生信息、LLM Token 使用情况和历史对话记录，方便后续做账号治理、成本监控和问题排查。"
      :badges="heroBadges"
      tone="admin"
    />

    <section v-if="error" class="info-card error-banner">
      <strong>加载失败</strong>
      <p>{{ error }}</p>
    </section>

    <SegmentedTabs v-model="activeTab" :tabs="tabs" />

    <Suspense>
      <component
        :is="activePanel"
        v-model:search="userSearch"
        v-model:time-range="timeRange"
        :teachers="teachers"
        :students="students"
        :logs="logs"
      />
      <template #fallback>
        <section class="card-panel">
          <p class="hero-desc">正在加载管理端模块...</p>
        </section>
      </template>
    </Suspense>
  </div>
</template>

<script setup lang="ts">
import { computed, defineAsyncComponent, onMounted, ref } from "vue";
import SegmentedTabs from "../../components/ui/SegmentedTabs.vue";
import PageHero from "../../components/ui/PageHero.vue";
import {
  fetchAdminLlmLogs,
  fetchAdminStudents,
  fetchAdminTeachers,
  type AdminLlmLog,
  type AdminStudentRecord,
  type AdminTeacherRecord,
} from "../../api/studentTwin";

type AdminTab = "users" | "tokens" | "conversations";
type TimeRange = "week" | "month" | "all";

const AdminUsersPanel = defineAsyncComponent(() => import("./panels/AdminUsersPanel.vue"));
const AdminTokensPanel = defineAsyncComponent(() => import("./panels/AdminTokensPanel.vue"));
const AdminConversationsPanel = defineAsyncComponent(() => import("./panels/AdminConversationsPanel.vue"));

const tabs: Array<{ label: string; value: AdminTab }> = [
  { value: "users", label: "用户管理" },
  { value: "tokens", label: "Token 统计" },
  { value: "conversations", label: "对话记录" },
];

const activeTab = ref<AdminTab>("users");
const error = ref("");
const teachers = ref<AdminTeacherRecord[]>([]);
const students = ref<AdminStudentRecord[]>([]);
const logs = ref<AdminLlmLog[]>([]);
const userSearch = ref("");
const timeRange = ref<TimeRange>("week");

const activePanel = computed(() => {
  if (activeTab.value === "tokens") return AdminTokensPanel;
  if (activeTab.value === "conversations") return AdminConversationsPanel;
  return AdminUsersPanel;
});

const heroBadges = computed(() => [
  `教师 ${teachers.value.length}`,
  `学生 ${students.value.length}`,
  `对话 ${logs.value.length}`,
]);

async function loadAdminData() {
  error.value = "";
  try {
    const [teacherRows, studentRows, logRows] = await Promise.all([
      fetchAdminTeachers(),
      fetchAdminStudents(),
      fetchAdminLlmLogs(),
    ]);
    teachers.value = teacherRows;
    students.value = studentRows;
    logs.value = logRows;
  } catch (err) {
    error.value = err instanceof Error ? err.message : "管理端数据加载失败";
  }
}

onMounted(() => {
  void loadAdminData();
});
</script>
