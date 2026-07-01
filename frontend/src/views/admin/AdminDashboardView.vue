<template>
  <div class="admin-shell">
    <PageHero
      eyebrow="管理工作台"
      title="管理端总览"
      description="统一查看教师与学生信息、LLM Token 使用情况和历史对话记录，方便后续做账号治理、成本监控和问题排查。"
      :badges="heroBadges"
      tone="admin"
    />

    <section class="admin-governance-grid">
      <article class="card-panel admin-governance-card">
        <p class="eyebrow">账号治理</p>
        <h2>教师与学生基数</h2>
        <strong>{{ teachers.length + students.length }}</strong>
        <p>先看总量，再看搜索结果和绑定关系，便于快速定位异常账号。</p>
      </article>
      <article class="card-panel admin-governance-card">
        <p class="eyebrow">模型成本</p>
        <h2>Token 统计窗口</h2>
        <strong>{{ timeRangeLabel }}</strong>
        <p>按近 7 天、近 30 天或全量切换，直接观察当前成本压力。</p>
      </article>
      <article class="card-panel admin-governance-card">
        <p class="eyebrow">对话审计</p>
        <h2>历史调用记录</h2>
        <strong>{{ logs.length }}</strong>
        <p>展开请求和响应正文，方便检查提示词、模型输出和异常上下文。</p>
      </article>
    </section>

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

const timeRangeLabel = computed(() => {
  if (timeRange.value === "week") return "近 7 天";
  if (timeRange.value === "month") return "近 30 天";
  return "全量";
});

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
