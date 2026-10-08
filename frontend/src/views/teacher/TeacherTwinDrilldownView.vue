<template>
  <div class="drilldown-shell">
    <section class="hero-panel app-hero app-hero--teacher">
      <div class="app-hero-copy">
        <p class="eyebrow">Teacher Twin Drilldown</p>
        <h1>教师六维钻取分析</h1>
        <p class="hero-desc">查看维度分数、子项明细与原始证据，区分内部闭环事件与外部兜底数据。</p>
      </div>
      <div class="app-hero-actions">
        <button class="ghost-btn" type="button" @click="goBack">返回教师展板</button>
      </div>
    </section>

    <section class="card-panel filters">
      <div class="two-col">
        <label class="field">
          <span>维度</span>
          <select v-model="selectedDimension" class="input" @change="loadDrilldown">
            <option v-for="item in dimensionOptions" :key="item.code" :value="item.code">
              {{ item.name }}
            </option>
          </select>
        </label>
        <label class="field">
          <span>时间窗口</span>
          <select v-model.number="windowDays" class="input" @change="loadDrilldown">
            <option :value="30">近30天</option>
            <option :value="90">近90天</option>
            <option :value="180">近180天</option>
          </select>
        </label>
      </div>
    </section>

    <section v-if="loading" class="card-panel state-card">正在加载钻取数据...</section>
    <section v-else-if="error" class="card-panel state-card error-state">{{ error }}</section>

    <template v-else-if="drilldown">
      <section class="metrics-grid-vue teacher-metrics-grid">
        <article class="card-panel metric-card-vue">
          <span class="metric-label">维度分数</span>
          <div class="metric-value">{{ drilldown.dimension.score }}</div>
        </article>
        <article class="card-panel metric-card-vue">
          <span class="metric-label">证据条数</span>
          <div class="metric-value">{{ drilldown.evidence_count }}</div>
        </article>
        <article class="card-panel metric-card-vue">
          <span class="metric-label">覆盖率</span>
          <div class="metric-value">{{ Math.round(drilldown.coverage_ratio * 100) }}%</div>
        </article>
      </section>

      <section class="card-panel">
        <div class="section-head">
          <h3>子项明细</h3>
          <span class="muted">当前值按子项内部指标展开，鼠标悬停可查看计算方式</span>
        </div>
        <div class="industry-table-wrap">
          <table class="industry-table">
            <thead>
            <tr>
              <th>子项</th>
              <th>当前值</th>
            </tr>
            </thead>
            <tbody>
            <tr v-for="row in subItemRows" :key="row.key">
              <td>
                <span class="sub-item-name">{{ row.name }}</span>
                <span class="sub-item-key">{{ row.key }}</span>
              </td>
              <td :title="row.method">{{ row.value }}</td>
            </tr>
            <tr v-if="!subItemRows.length">
              <td colspan="2">当前维度暂无子项数据。</td>
            </tr>
            </tbody>
          </table>
        </div>
      </section>

      <section class="card-panel">
        <div class="section-head">
          <h3>原始证据</h3>
        </div>
        <div class="industry-table-wrap">
          <table class="industry-table">
            <thead>
            <tr>
              <th>时间</th>
              <th>事件类型</th>
              <th>关联对象</th>
              <th>摘要</th>
            </tr>
            </thead>
            <tbody>
            <tr v-for="item in drilldown.evidence_items" :key="`${item.event_type}-${item.created_at}-${item.target_id || ''}`">
              <td>{{ formatTime(item.created_at) }}</td>
              <td>{{ item.event_type }}</td>
              <td>{{ item.student_username || item.target_id || "-" }}</td>
              <td>{{ item.summary }}</td>
            </tr>
            <tr v-if="!drilldown.evidence_items.length">
              <td colspan="4">当前时间窗口内暂无内部证据，可能仍在使用外部兜底数据。</td>
            </tr>
            </tbody>
          </table>
        </div>
      </section>
    </template>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import { useRoute, useRouter } from "vue-router";
import { fetchTeacherTwinDrilldown } from "../../api/teacher";
import type { TeacherTwinDrilldownResponse } from "../../types/teacher";

const route = useRoute();
const router = useRouter();
const loading = ref(false);
const error = ref("");
const drilldown = ref<TeacherTwinDrilldownResponse | null>(null);
const selectedDimension = ref(String(route.query.dimension || "professional_engagement"));
const windowDays = ref(Number(route.query.window_days || 30));

const dimensionOptions = [
  { code: "professional_engagement", name: "专业投入" },
  { code: "digital_resources", name: "数字资源" },
  { code: "teaching_learning", name: "教学与学习" },
  { code: "assessment", name: "评估" },
  { code: "empowering_learners", name: "赋能学习者" },
  { code: "facilitating_digital_competence", name: "促进学习者数字能力" },
];

const subItemExplainMeta: Record<string, { name: string; source: string; method: string }> = {
  platform_activity: { name: "平台活跃度", source: "sessions", method: "统计近 7 天会话时长与登录频次" },
  teaching_research_collaboration: { name: "教研协作行为", source: "user_states.teacher_ext", method: "读取 external-sync 注入的教研帖、共享课件、联合备课计数" },
  feature_exploration: { name: "系统功能探索度", source: "llm_logs.metadata.feature", method: "统计高级功能 feature 命中次数" },
  resource_diversity_index: { name: "资源多样性指数", source: "learning_plans.filename", method: "统计文件后缀格式数" },
  resource_iteration_frequency: { name: "资源迭代频率", source: "learning_plans.data.revision_count", method: "汇总 revision_count，无则按资源条目数估算" },
  resource_reuse_and_sharing: { name: "资源复用与共享", source: "user_states.teacher_ext", method: "读取 external-sync 注入的被引用次数" },
  online_interaction_frequency: { name: "在线互动频次", source: "llm_logs.metadata + user_states.teacher_ext", method: "统计公告/讨论并结合回复率与响应时长" },
  teaching_rhythm_control: { name: "教学节奏控制", source: "user_states.teacher_ext.on_time_release_ratio", method: "读取按时发布率，缺失时用默认值" },
  human_ai_collaboration: { name: "人机协同度", source: "llm_logs.metadata.ai_recommendation/ai_executed", method: "执行率=执行动作数/推荐动作数" },
  assessment_diversification: { name: "评估方式多元化", source: "llm_logs.metadata.assessment_type", method: "统计评估类型去重数" },
  feedback_timeliness_and_depth: { name: "反馈及时性与深度", source: "llm_logs.metadata.feedback_text/grading_minutes", method: "计算平均反馈长度与平均批改耗时" },
  data_driven_adjustment: { name: "数据驱动调整", source: "llm_logs.metadata.action", method: "统计补救讲解/公告动作次数" },
  personalized_path_dispatch_rate: { name: "个性化路径下发率", source: "user_states.teacher_ext + users(student)", method: "下发率=个性化推送次数/覆盖学生数" },
  intervention_strategy_execution: { name: "干预策略实施", source: "user_states.teacher_ext + twin_profiles", method: "执行率=干预次数/风险学生数" },
  student_initiative_feedback: { name: "学生学习主动性反哺", source: "llm_logs.metadata.student_username/initiated_by_student", method: "统计学生主动触发互动占比" },
  digital_task_ratio: { name: "数字化任务占比", source: "teacher_ext 或 llm_logs.metadata.task_mode", method: "数字化任务数/总任务数" },
  collaborative_task_design: { name: "协作任务设计", source: "teacher_ext 或 llm_logs.metadata.task_group_mode", method: "协作任务数/总任务数" },
  inquiry_learning_configuration: { name: "探究式学习配置", source: "teacher_ext 或 llm_logs.metadata.task_type", method: "探究学习时长/总教学时长" },
};

/** 子项内部的原子指标中文名，用于把对象值渲染成「名称 数值」。 */
const metricLabels: Record<string, string> = {
  weekly_online_hours: "周在线小时",
  weekly_login_frequency: "周登录次数",
  posts: "教研发帖数",
  shared_courseware: "共享课件数",
  co_preparation_frequency: "集体备课次数",
  advanced_feature_usage_count: "高级功能使用次数",
  format_count: "资源格式种类数",
  formats: "资源格式",
  revision_count: "资源迭代次数",
  resource_count: "资源条目数",
  referenced_by_other_teachers: "被其他教师引用次数",
  announcement_count: "公告数",
  topic_count: "讨论话题数",
  reply_rate: "回复率",
  avg_response_minutes: "平均响应分钟",
  on_time_release_ratio: "按时发布率",
  ai_recommendation_count: "AI 推荐次数",
  ai_executed_count: "AI 执行次数",
  execution_rate: "执行率",
  assessment_types: "评估类型",
  type_count: "评估类型数",
  subjective_feedback_count: "主观题反馈条数",
  avg_feedback_length: "平均反馈字数",
  avg_grading_minutes: "平均批改分钟",
  remediation_actions: "补救动作次数",
  student_count: "覆盖学生数",
  personalized_push_count: "个性化推送次数",
  dispatch_rate: "下发率",
  risk_student_count: "风险学生数",
  intervention_count: "干预次数",
  execution_count: "执行次数",
  student_initiated_count: "学生主动触发次数",
  initiative_rate: "主动反哺占比",
  digital_task_count: "数字化任务数",
  total_task_count: "任务总数",
  digital_ratio: "数字化占比",
  collaborative_task_count: "协作任务数",
  collaborative_ratio: "协作占比",
  inquiry_minutes: "探究学习时长",
  total_minutes: "总教学时长",
  inquiry_ratio: "探究占比",
};

function labelFor(key: string) {
  return metricLabels[key] || key;
}

function formatMetricValue(value: unknown): string {
  if (value === null || value === undefined || value === "") return "-";
  if (Array.isArray(value)) return value.length ? value.map((item) => String(item)).join("、") : "-";
  if (typeof value === "number") return Number.isInteger(value) ? String(value) : String(Math.round(value * 100) / 100);
  if (typeof value === "object") return JSON.stringify(value);
  return String(value);
}

function formatSubItemValue(value: unknown): { text: string; detail: boolean } {
  if (value !== null && typeof value === "object" && !Array.isArray(value)) {
    const parts = Object.entries(value as Record<string, unknown>)
      .map(([key, item]) => `${labelFor(key)} ${formatMetricValue(item)}`);
    return { text: parts.length ? parts.join(" · ") : "-", detail: true };
  }
  return { text: formatMetricValue(value), detail: false };
}

const subItemRows = computed(() => {
  const current = drilldown.value?.dimension.sub_items || {};
  return Object.entries(current).map(([key, value]) => {
    const formatted = formatSubItemValue(value);
    const meta = subItemExplainMeta[key];
    return {
      key,
      name: meta?.name || key,
      method: meta?.method || "",
      value: formatted.text,
      isDetail: formatted.detail,
    };
  });
});

async function loadDrilldown() {
  loading.value = true;
  error.value = "";
  try {
    drilldown.value = await fetchTeacherTwinDrilldown(selectedDimension.value, windowDays.value);
    await router.replace({
      query: {
        dimension: selectedDimension.value,
        window_days: String(windowDays.value),
      },
    });
  } catch (err) {
    error.value = err instanceof Error ? err.message : "钻取数据加载失败";
  } finally {
    loading.value = false;
  }
}

function formatTime(value: string) {
  return value ? new Date(value).toLocaleString() : "-";
}

function goBack() {
  router.push({ path: "/teacher/dashboard", query: { tab: "teacher-twin" } });
}

onMounted(loadDrilldown);
</script>

<style scoped>
.two-col {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 16px;
}

.field {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.sub-item-name {
  display: block;
  font-weight: 600;
}

.sub-item-key {
  display: block;
  margin-top: 2px;
  font-size: 12px;
  color: #8a919b;
  font-family: Consolas, "Courier New", monospace;
}

@media (max-width: 900px) {
  .two-col {
    grid-template-columns: 1fr;
  }
}
</style>
