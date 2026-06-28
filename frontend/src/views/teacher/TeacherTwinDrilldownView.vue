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
              <td>{{ row.key }}</td>
              <td>{{ row.value }}</td>
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

const subItemRows = computed(() => {
  const current = drilldown.value?.dimension.sub_items || {};
  return Object.entries(current).map(([key, value]) => ({
    key,
    value: typeof value === "object" ? JSON.stringify(value) : String(value),
  }));
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
  router.push("/teacher/dashboard");
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

@media (max-width: 900px) {
  .two-col {
    grid-template-columns: 1fr;
  }
}
</style>
