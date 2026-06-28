<template>
  <section class="admin-tokens">
    <div class="metric-grid">
      <article class="metric-card">
        <span class="metric-label">近 7 天 Token</span>
        <strong>{{ formatCount(tokenStats.weekly) }}</strong>
        <small>统计最近一周的总调用量。</small>
      </article>
      <article class="metric-card">
        <span class="metric-label">近 30 天 Token</span>
        <strong>{{ formatCount(tokenStats.monthly) }}</strong>
        <small>统计最近一个月的总调用量。</small>
      </article>
      <article class="metric-card">
        <span class="metric-label">累计 Token</span>
        <strong>{{ formatCount(tokenStats.total) }}</strong>
        <small>历史全量 LLM 消耗。</small>
      </article>
      <article class="metric-card">
        <span class="metric-label">平均单次消耗</span>
        <strong>{{ formatCount(tokenStats.average) }}</strong>
        <small>按总对话记录平均得到。</small>
      </article>
    </div>

    <div class="detail-grid">
      <section class="card-panel">
        <div class="section-head">
          <h2>每日 Token 趋势</h2>
          <div class="admin-inline-tabs">
            <el-segmented v-model="currentRange" :options="timeRangeOptions" />
          </div>
        </div>
        <div ref="tokenChartRef" class="chart-box admin-chart"></div>
      </section>

      <section class="card-panel">
        <div class="section-head">
          <h2>模型分布</h2>
          <span class="muted">{{ modelRows.length }} 个模型</span>
        </div>
        <div ref="modelChartRef" class="chart-box admin-chart"></div>
      </section>
    </div>

    <div class="detail-grid">
      <section class="card-panel">
        <div class="section-head">
          <h2>模块调用统计</h2>
          <span class="muted">展示调用次数最多的模块</span>
        </div>
        <div ref="moduleChartRef" class="chart-box admin-chart"></div>
      </section>

      <section class="card-panel">
        <div class="section-head">
          <h2>模块 Token 明细</h2>
          <span class="muted">按总消耗排序</span>
        </div>
        <div class="industry-table-wrap">
          <el-table :data="moduleRows" stripe table-layout="auto">
            <el-table-column prop="moduleLabel" label="模块" min-width="180" />
            <el-table-column prop="count" label="调用次数" width="110" />
            <el-table-column label="Prompt" width="110">
              <template #default="{ row }">{{ formatCount(row.promptTokens) }}</template>
            </el-table-column>
            <el-table-column label="Completion" width="130">
              <template #default="{ row }">{{ formatCount(row.completionTokens) }}</template>
            </el-table-column>
            <el-table-column label="Total" width="110">
              <template #default="{ row }">{{ formatCount(row.totalTokens) }}</template>
            </el-table-column>
          </el-table>
        </div>
      </section>
    </div>
  </section>
</template>

<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from "vue";
import type { AdminLlmLog } from "../../../api/studentTwin";
import { init, type ECharts } from "../../../lib/echarts";

type TimeRange = "week" | "month" | "all";

const currentRange = defineModel<TimeRange>("timeRange", { default: "week" });

const props = defineProps<{
  logs: AdminLlmLog[];
}>();

const timeRangeOptions = [
  { label: "近 7 天", value: "week" },
  { label: "近 30 天", value: "month" },
  { label: "全部", value: "all" },
];

const tokenChartRef = ref<HTMLDivElement | null>(null);
const modelChartRef = ref<HTMLDivElement | null>(null);
const moduleChartRef = ref<HTMLDivElement | null>(null);

let tokenChart: ECharts | null = null;
let modelChart: ECharts | null = null;
let moduleChart: ECharts | null = null;

const tokenStats = computed(() => {
  const now = Date.now();
  const weekStart = now - 7 * 24 * 60 * 60 * 1000;
  const monthStart = now - 30 * 24 * 60 * 60 * 1000;
  let weekly = 0;
  let monthly = 0;
  let total = 0;

  props.logs.forEach((log) => {
    const tokens = log.response?.usage?.total_tokens ?? 0;
    const timestamp = new Date(log.timestamp).getTime();
    total += tokens;
    if (timestamp >= weekStart) weekly += tokens;
    if (timestamp >= monthStart) monthly += tokens;
  });

  return {
    weekly,
    monthly,
    total,
    average: props.logs.length ? Math.round(total / props.logs.length) : 0,
  };
});

const modelRows = computed(() => {
  const map = new Map<string, { count: number; tokens: number }>();
  props.logs.forEach((log) => {
    const model = log.request?.model || "Unknown";
    const current = map.get(model) ?? { count: 0, tokens: 0 };
    current.count += 1;
    current.tokens += log.response?.usage?.total_tokens ?? 0;
    map.set(model, current);
  });
  return Array.from(map.entries())
    .map(([name, value]) => ({ name, ...value }))
    .sort((a, b) => b.count - a.count);
});

const moduleRows = computed(() => {
  const map = new Map<
    string,
    {
      count: number;
      promptTokens: number;
      completionTokens: number;
      totalTokens: number;
    }
  >();
  props.logs.forEach((log) => {
    const module = log.module || "Unknown";
    const usage = log.response?.usage;
    const current = map.get(module) ?? {
      count: 0,
      promptTokens: 0,
      completionTokens: 0,
      totalTokens: 0,
    };
    current.count += 1;
    current.promptTokens += usage?.prompt_tokens ?? 0;
    current.completionTokens += usage?.completion_tokens ?? 0;
    current.totalTokens += usage?.total_tokens ?? 0;
    map.set(module, current);
  });
  return Array.from(map.entries())
    .map(([module, value]) => ({
      module,
      moduleLabel: getModuleLabel(module),
      ...value,
    }))
    .sort((a, b) => b.totalTokens - a.totalTokens);
});

watch(
  () => [props.logs.length, currentRange.value],
  async () => {
    await nextTick();
    safeRenderCharts();
  },
  { immediate: true },
);

function safeRenderCharts() {
  try {
    renderTokenChart();
    renderModelChart();
    renderModuleChart();
  } catch (err) {
    console.error("AdminTokensPanel render failed:", err);
  }
}

function formatCount(value: number) {
  if (value >= 1_000_000) return `${(value / 1_000_000).toFixed(1)}M`;
  if (value >= 1_000) return `${(value / 1_000).toFixed(1)}K`;
  return String(Math.round(value));
}

function getModuleLabel(module: string) {
  const map: Record<string, string> = {
    "AgentModule.edu_agent": "AI 助教",
    "QuizModule.quiz_operations": "测验生成",
    "SummaryModule.summary_generator": "知识总结",
    "LearningPlanModule.learning_plan": "学习计划",
    "frontend.quizpage": "前端测验",
  };
  return map[module] || module;
}

function getSeriesDataByRange(range: TimeRange) {
  const now = Date.now();
  const days = range === "week" ? 7 : range === "month" ? 30 : 365;
  const start = now - days * 24 * 60 * 60 * 1000;
  const bucket = new Map<string, { prompt: number; completion: number; total: number }>();

  props.logs.forEach((log) => {
    const time = new Date(log.timestamp).getTime();
    if (time < start) return;
    const dateKey = new Date(log.timestamp).toISOString().slice(0, 10);
    const current = bucket.get(dateKey) ?? { prompt: 0, completion: 0, total: 0 };
    current.prompt += log.response?.usage?.prompt_tokens ?? 0;
    current.completion += log.response?.usage?.completion_tokens ?? 0;
    current.total += log.response?.usage?.total_tokens ?? 0;
    bucket.set(dateKey, current);
  });

  const labels = Array.from(bucket.keys()).sort();
  return {
    labels,
    prompt: labels.map((label) => bucket.get(label)?.prompt ?? 0),
    completion: labels.map((label) => bucket.get(label)?.completion ?? 0),
    total: labels.map((label) => bucket.get(label)?.total ?? 0),
  };
}

function ensureCharts() {
  if (tokenChartRef.value && !tokenChart) tokenChart = init(tokenChartRef.value);
  if (modelChartRef.value && !modelChart) modelChart = init(modelChartRef.value);
  if (moduleChartRef.value && !moduleChart) moduleChart = init(moduleChartRef.value);
}

function renderTokenChart() {
  if (!tokenChartRef.value) return;
  ensureCharts();
  if (!tokenChart) return;
  const seriesData = getSeriesDataByRange(currentRange.value);
  tokenChart.setOption({
    color: ["#2563eb", "#22c55e", "#f97316"],
    tooltip: { trigger: "axis" },
    legend: { top: 10, data: ["Prompt Tokens", "Completion Tokens", "Total Tokens"] },
    grid: { left: 36, right: 18, top: 58, bottom: 28, containLabel: true },
    xAxis: {
      type: "category",
      data: seriesData.labels,
      axisLabel: {
        formatter: (value: string) => value.slice(5).replace("-", "/"),
      },
    },
    yAxis: { type: "value", name: "Tokens" },
    series: [
      { name: "Prompt Tokens", type: "line", smooth: true, data: seriesData.prompt },
      { name: "Completion Tokens", type: "line", smooth: true, data: seriesData.completion },
      { name: "Total Tokens", type: "line", smooth: true, data: seriesData.total },
    ],
  });
}

function renderModelChart() {
  if (!modelChartRef.value) return;
  ensureCharts();
  if (!modelChart) return;
  modelChart.setOption({
    tooltip: {
      trigger: "item",
      formatter: (params: { name: string; value: number; data: { tokens: number } }) =>
        `${params.name}<br/>调用次数：${params.value}<br/>总 Token：${formatCount(params.data.tokens)}`,
    },
    legend: { orient: "vertical", left: 12, top: "middle" },
    series: [
      {
        type: "pie",
        radius: ["42%", "72%"],
        center: ["64%", "50%"],
        data: modelRows.value.map((row) => ({ name: row.name, value: row.count, tokens: row.tokens })),
        label: { formatter: "{b}: {d}%" },
      },
    ],
  });
}

function renderModuleChart() {
  if (!moduleChartRef.value) return;
  ensureCharts();
  if (!moduleChart) return;
  moduleChart.setOption({
    tooltip: {
      trigger: "axis",
      axisPointer: { type: "shadow" },
    },
    grid: { left: 36, right: 12, top: 24, bottom: 80, containLabel: true },
    xAxis: {
      type: "category",
      data: moduleRows.value.map((row) => row.moduleLabel),
      axisLabel: { rotate: 28 },
    },
    yAxis: { type: "value", name: "调用次数" },
    series: [
      {
        type: "bar",
        data: moduleRows.value.map((row) => row.count),
        itemStyle: {
          color: "#7a6ad8",
          borderRadius: [10, 10, 0, 0],
        },
      },
    ],
  });
}

function resizeCharts() {
  tokenChart?.resize();
  modelChart?.resize();
  moduleChart?.resize();
}

onMounted(() => {
  window.addEventListener("resize", resizeCharts);
});

onBeforeUnmount(() => {
  window.removeEventListener("resize", resizeCharts);
  tokenChart?.dispose();
  modelChart?.dispose();
  moduleChart?.dispose();
  tokenChart = null;
  modelChart = null;
  moduleChart = null;
});
</script>
