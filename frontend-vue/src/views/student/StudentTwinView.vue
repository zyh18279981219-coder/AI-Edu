<template>
  <div class="student-twin-shell">
    <PageHero
      eyebrow="Student Twin"
      :title="$t('student.studentTwin.studentTwin')"
      :description="$t('student.studentTwin.studentTwinDescription')"
      :badges="heroBadges"
      tone="default"
    >
      <template #actions>
        <el-button type="primary" size="large" round :loading="loading" @click="handleRefresh">
          {{ loading ? $t('student.studentTwin.loadingStudentPicture') : $t('student.studentTwin.reloadStudentPicture') }}
        </el-button>
      </template>
    </PageHero>

    <section v-if="error" class="state-card error-state">
      <h2>{{ $t('student.studentTwin.errorLoading') }}</h2>
      <p>{{ error }}</p>
    </section>

    <template v-else>
      <section class="metric-grid">
        <MetricStatCard
          :label="$t('student.studentTwin.overallMastery')"
          :value="formatScore(summary?.overall_mastery)"
          :description="$t('student.studentTwin.overallMasteryDescription')"
          tone="brand"
        />
        <MetricStatCard
          :label="$t('student.studentTwin.technicalLevel')"
          :value="summary?.technical_level.label ?? '-'"
          :description="summary?.technical_level.description ?? '-'"
          tone="success"
        />
        <MetricStatCard
          :label="$t('student.studentTwin.weakKnowledgeNodes')"
          :value="summary?.node_summary.weak_node_count ?? 0"
          :description="$t('student.studentTwin.weakNodesDescription')"
          tone="warning"
        />
        <MetricStatCard
          :label="$t('student.studentTwin.trendStatus')"
          :value="trendStatusText(summary?.trend.trend_status)"
          :description="summary?.trend.summary ?? '-'"
        />
      </section>

      <section class="chart-grid">
        <article class="card-panel">
          <div class="section-head">
            <h2>{{ $t('student.studentTwin.abilityRadar') }}</h2>
            <span class="muted">{{ $t('student.studentTwin.fiveDimensionAbilityPicture') }}</span>
          </div>
          <div ref="radarRef" class="chart-box"></div>
        </article>
        <article class="card-panel">
          <div class="section-head">
            <h2>{{ $t('student.studentTwin.trend') }}</h2>
            <span class="muted">{{ $t('student.studentTwin.recent30Days') }}</span>
          </div>
          <div ref="trendRef" class="chart-box"></div>
        </article>
      </section>

      <section class="detail-grid">
        <article class="card-panel">
          <div class="section-head">
            <h2>{{ $t('student.studentTwin.learningRiskWarning') }}</h2>
          </div>
          <div class="stack-list">
            <div v-for="risk in summary?.risk_alerts ?? []" :key="risk.code" class="list-card">
              <div class="list-title">{{ risk.title }}</div>
              <div class="list-meta">{{ $t('student.studentTwin.rickLevel') }}{{ riskLevelText(risk.level) }}</div>
              <div>{{ risk.detail }}</div>
            </div>
            <div v-if="!(summary?.risk_alerts?.length)" class="list-card">{{ $t('student.studentTwin.noLearningRiskWarning') }}</div>
          </div>
        </article>

        <article class="card-panel">
          <div class="section-head">
            <h2>{{ $t('student.studentTwin.weakKnowledgeNodes') }}</h2>
            <span class="muted">{{ $t('student.studentTwin.numberOfWeakNodes', { number: summary?.weak_nodes?.length ?? 0 }) }}</span>
          </div>
          <div class="stack-list">
            <div v-for="node in pagedWeakNodes" :key="node.node_id" class="list-card">
              <div class="list-title">{{ node.node_id }}</div>
              <div class="list-meta">
                {{ $t('student.studentTwin.weakNodesDetail', { mastery: formatScore(node.mastery_score), progress: formatScore(node.progress), quiz: formatScore(node.quiz_score) }) }}
              </div>
              <div>{{ node.node_path?.join(" > ") || $t('student.studentTwin.noPaths') }}</div>
            </div>
            <div v-if="!(summary?.weak_nodes?.length)" class="list-card">{{ $t('student.studentTwin.noWeakNodes') }}</div>
          </div>
          <div v-if="totalWeakPages > 1" class="pagination pagination--element">
            <el-pagination
              v-model:current-page="weakNodePage"
              :page-size="pageSize"
              layout="prev, pager, next"
              :total="summary?.weak_nodes?.length ?? 0"
              small
            />
          </div>
        </article>
      </section>
    </template>
  </div>
</template>

<script setup lang="ts">
import axios from "axios";
import {computed, nextTick, onBeforeUnmount, onMounted, ref, watch} from "vue";
import MetricStatCard from "../../components/ui/MetricStatCard.vue";
import PageHero from "../../components/ui/PageHero.vue";
import {fetchCurrentUser} from "../../api/login";
import {type ECharts, init} from "../../lib/echarts";
import {fetchStudentTwin, refreshStudentTwin} from "../../api/student";
import {StudentTwinSummary} from "../../types/student";
import i18n from "../../locale";

const { t } = i18n.global;

const loading = ref(false);
const error = ref("");
const summary = ref<StudentTwinSummary | null>(null);
const username = ref("");
const weakNodePage = ref(1);
const pageSize = 5;
const radarRef = ref<HTMLDivElement | null>(null);
const trendRef = ref<HTMLDivElement | null>(null);
let radarChart: ECharts | null = null;
let trendChart: ECharts | null = null;

const pagedWeakNodes = computed(() => {
  const items = summary.value?.weak_nodes ?? [];
  const start = (weakNodePage.value - 1) * pageSize;
  return items.slice(start, start + pageSize);
});

const totalWeakPages = computed(() => {
  const items = summary.value?.weak_nodes ?? [];
  return Math.max(1, Math.ceil(items.length / pageSize));
});

const heroBadges = computed(() => [
  `${t('student.studentTwin.weakNodes')} ${summary.value?.node_summary.weak_node_count ?? 0}`,
  `${t('student.studentTwin.advantage')} ${summary.value?.node_summary.strong_node_count ?? 0}`,
  `${t('student.studentTwin.trend')} ${trendStatusText(summary.value?.trend.trend_status)}`,
]);

watch(
  () => summary.value?.weak_nodes?.length,
  () => {
    weakNodePage.value = 1;
  },
);

watch(totalWeakPages, (value) => {
  if (weakNodePage.value > value) weakNodePage.value = value;
});

function formatScore(value?: number) {
  return Number(value ?? 0).toFixed(1);
}

function trendStatusText(status?: string) {
  const mapping: Record<string, string> = {
    upward: t('student.studentTwin.upward'),
    stable: t('student.studentTwin.stable'),
    downward: t('student.studentTwin.downward'),
  };
  return mapping[status ?? "stable"] ?? t('student.studentTwin.relativelyStable');
}

function riskLevelText(level?: string) {
  const mapping: Record<string, string> = {
    high: t('student.studentTwin.highRisk'),
    medium: t('student.studentTwin.mediumRisk'),
    low: t('student.studentTwin.lowRisk'),
  };
  return mapping[level ?? "medium"] ?? (level || t('student.studentTwin.mediumRisk'));
}

async function loadSummary() {
  loading.value = true;
  error.value = "";
  try {
    const user = await fetchCurrentUser();
    username.value = user.username;
    summary.value = await fetchStudentTwin(user.username);
    await nextTick();
    renderCharts();
  } catch (err) {
    if (axios.isAxiosError(err) && err.response?.status === 404 && username.value) {
      try {
        await refreshStudentTwin(username.value);
        summary.value = await fetchStudentTwin(username.value);
        await nextTick();
        renderCharts();
        return;
      } catch (retryErr) {
        error.value = resolveErrorMessage(retryErr);
        return;
      }
    }
    error.value = resolveErrorMessage(err);
  } finally {
    loading.value = false;
  }
}

async function handleRefresh() {
  if (!username.value) return;
  loading.value = true;
  error.value = "";
  try {
    await refreshStudentTwin(username.value);
    summary.value = await fetchStudentTwin(username.value);
    await nextTick();
    renderCharts();
  } catch (err) {
    error.value = resolveErrorMessage(err);
  } finally {
    loading.value = false;
  }
}

function resolveErrorMessage(err: unknown) {
  if (axios.isAxiosError(err)) {
    const detail = err.response?.data?.detail;
    if (typeof detail === "string" && detail.trim()) return detail;
    return err.message || t('student.studentTwin.errorLoadingStudentTwin');
  }
  return err instanceof Error ? err.message : t('student.studentTwin.errorLoadingStudentTwin');
}

function renderCharts() {
  safeRenderCharts();
}

function safeRenderCharts() {
  try {
    renderRadar();
    renderTrend();
  } catch (err) {
    console.error("StudentTwinView render failed:", err);
    error.value = err instanceof Error ? err.message : t('student.studentTwin.errorRenderingStudentPicture');
  }
}

function renderRadar() {
  if (!radarRef.value || !summary.value) return;
  radarChart ??= init(radarRef.value);
  const items = summary.value.radar ?? [];
  radarChart.setOption({
    tooltip: {
      trigger: "item",
      formatter: () => items.map((item) => `${item.name}：${formatScore(item.value)}`).join("<br/>"),
    },
    radar: {
      center: ["50%", "52%"],
      radius: "70%",
      indicator: items.map((item) => ({ name: item.name, max: 100 })),
      axisName: {
        color: "#334155",
        fontSize: 14,
        fontWeight: 700,
      },
      splitArea: {
        areaStyle: { color: ["#f8fbff", "#eef4ff"] },
      },
      axisLine: { lineStyle: { color: "rgba(148, 163, 184, 0.4)" } },
      splitLine: { lineStyle: { color: "rgba(148, 163, 184, 0.28)" } },
    },
    series: [
      {
        type: "radar",
        data: [
          {
            value: items.map((item) => item.value || 0),
            areaStyle: { color: "rgba(37, 99, 235, 0.18)" },
            lineStyle: { color: "#2563eb", width: 2 },
            itemStyle: { color: "#1d4ed8" },
          },
        ],
      },
    ],
  });
}

function renderTrend() {
  if (!trendRef.value || !summary.value) return;
  trendChart ??= init(trendRef.value);
  const points = summary.value.trend?.points ?? [];
  trendChart.setOption({
    tooltip: { trigger: "axis" },
    grid: { left: 44, right: 18, top: 24, bottom: 30 },
    xAxis: {
      type: "category",
      data: points.map((item) => item.date),
      axisLabel: { color: "#64748b" },
    },
    yAxis: {
      type: "value",
      min: 0,
      max: 100,
      axisLabel: { color: "#64748b" },
      splitLine: { lineStyle: { color: "#e2e8f0" } },
    },
    series: [
      {
        type: "line",
        smooth: true,
        data: points.map((item) => item.overall_mastery),
        lineStyle: { color: "#0f766e", width: 3 },
        itemStyle: { color: "#0f766e" },
        areaStyle: { color: "rgba(15, 118, 110, 0.12)" },
      },
    ],
  });
}

function handleResize() {
  radarChart?.resize();
  trendChart?.resize();
}

onMounted(async () => {
  await loadSummary();
  window.addEventListener("resize", handleResize);
});

onBeforeUnmount(() => {
  window.removeEventListener("resize", handleResize);
  radarChart?.dispose();
  trendChart?.dispose();
  radarChart = null;
  trendChart = null;
});
</script>
