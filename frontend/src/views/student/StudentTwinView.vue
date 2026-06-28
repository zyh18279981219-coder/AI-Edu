<template>
  <div class="student-twin-shell">
    <!-- 诊断报告头部 -->
    <div class="student-diagnosis-v2-header">
      <div class="student-diagnosis-v2-header-content">
        <div class="student-diagnosis-v2-eyebrow">学习诊断</div>
        <h1 class="student-diagnosis-v2-title">🔍 学习诊断报告</h1>
        <p class="student-diagnosis-v2-desc">基于数字孪生数据生成学习能力画像、薄弱知识点和风险预警</p>
      </div>
      <div class="student-diagnosis-v2-header-actions">
        <el-button type="primary" size="large" round :loading="loading" @click="handleRefresh">
          {{ loading ? '生成中...' : '重新生成诊断' }}
        </el-button>
      </div>
    </div>

    <!-- 诊断元信息 -->
    <div class="student-diagnosis-v2-meta-bar">
      <div class="student-diagnosis-v2-meta-item">
        <span class="student-diagnosis-v2-meta-label">生成时间:</span>
        <span class="student-diagnosis-v2-meta-value">{{ diagnosisTime }}</span>
      </div>
      <div class="student-diagnosis-v2-meta-item">
        <span class="student-diagnosis-v2-meta-label">风险等级:</span>
        <span class="student-diagnosis-v2-risk-badge" :class="riskLevelClass">{{ riskLevelLabel }}</span>
      </div>
      <div class="student-diagnosis-v2-meta-item">
        <span class="student-diagnosis-v2-meta-label">薄弱知识点:</span>
        <span class="student-diagnosis-v2-meta-value">{{ weakNodeCount }}个</span>
      </div>
      <div class="student-diagnosis-v2-meta-item">
        <span class="student-diagnosis-v2-meta-label">优势知识点:</span>
        <span class="student-diagnosis-v2-meta-value">{{ strongNodeCount }}个</span>
      </div>
    </div>

    <section v-if="error" class="state-card error-state">
      <h2>{{ $t('student.studentTwin.errorLoading') }}</h2>
      <p>{{ error }}</p>
    </section>

    <template v-else>
      <!-- 能力画像和学习趋势 -->
      <section class="chart-grid">
        <article class="card-panel">
          <div class="section-head">
            <h2>📊 能力画像</h2>
            <span class="muted">五维能力雷达图</span>
          </div>
          <div ref="radarRef" class="chart-box"></div>
        </article>
        <article class="card-panel">
          <div class="section-head">
            <h2>📈 学习趋势</h2>
            <span class="muted">近 30 天掌握度变化</span>
          </div>
          <div ref="trendRef" class="chart-box"></div>
        </article>
      </section>

      <!-- 学习风险预警和薄弱知识节点 -->
      <section class="detail-grid">
        <article class="card-panel">
          <div class="section-head">
            <h2>⚠️ 学习风险预警</h2>
          </div>
          <div class="stack-list">
            <div v-for="risk in summary?.risk_alerts ?? []" :key="risk.code" 
                 class="list-card student-diagnosis-v2-risk-item" 
                 :class="'student-diagnosis-v2-risk-' + (risk.level || 'medium')">
              <div class="list-title">
                <span class="student-diagnosis-v2-risk-icon">{{ riskIcon(risk.level) }}</span>
                {{ risk.title }}
              </div>
              <div class="list-meta">
                风险等级：<span class="student-diagnosis-v2-risk-level-text" :class="'student-diagnosis-v2-level-' + (risk.level || 'medium')">{{ riskLevelText(risk.level) }}</span>
              </div>
              <div>{{ risk.detail }}</div>
            </div>
            <div v-if="!(summary?.risk_alerts?.length)" class="list-card student-diagnosis-v2-no-risk">
              <div class="student-diagnosis-v2-no-risk-icon">✓</div>
              <div class="student-diagnosis-v2-no-risk-text">暂无学习风险预警</div>
            </div>
          </div>
        </article>

        <article class="card-panel">
          <div class="section-head">
            <h2>📉 薄弱知识节点</h2>
            <span class="muted">共 {{ summary?.weak_nodes?.length ?? 0 }} 个需要加强</span>
          </div>
          <div class="stack-list">
            <div v-for="node in pagedWeakNodes" :key="node.node_id" class="list-card student-diagnosis-v2-weak-node-item">
              <div class="list-title">{{ node.node_id }}</div>
              <div class="student-diagnosis-v2-weak-node-stats">
                <div class="student-diagnosis-v2-stat-row">
                  <span class="student-diagnosis-v2-stat-label">掌握度:</span>
                  <span class="student-diagnosis-v2-stat-value">{{ formatScore(node.mastery_score) }}%</span>
                  <div class="student-diagnosis-v2-mini-progress">
                    <div class="student-diagnosis-v2-mini-progress-fill" :style="{ width: formatScore(node.mastery_score) + '%' }"></div>
                  </div>
                </div>
                <div class="student-diagnosis-v2-stat-row">
                  <span class="student-diagnosis-v2-stat-label">学习进度:</span>
                  <span class="student-diagnosis-v2-stat-value">{{ formatScore(node.progress) }}%</span>
                </div>
                <div class="student-diagnosis-v2-stat-row">
                  <span class="student-diagnosis-v2-stat-label">测验分数:</span>
                  <span class="student-diagnosis-v2-stat-value">{{ formatScore(node.quiz_score) }}分</span>
                </div>
              </div>
              <div class="student-diagnosis-v2-node-path">{{ node.node_path?.join(" > ") || '暂无路径' }}</div>
            </div>
            <div v-if="!(summary?.weak_nodes?.length)" class="list-card student-diagnosis-v2-no-weak">
              <div class="student-diagnosis-v2-no-weak-icon">🎉</div>
              <div class="student-diagnosis-v2-no-weak-text">暂无薄弱知识点，继续保持！</div>
            </div>
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

      <section class="card-panel student-diagnosis-v2-evidence-panel">
        <div class="section-head">
          <h2>证据时间线</h2>
          <span class="muted">最近 {{ evidenceTimeline.length }} 条学习证据</span>
        </div>
        <div class="stack-list">
          <div
            v-for="item in evidenceTimeline"
            :key="`${item.type}-${item.node_id || ''}-${item.occurred_at || ''}-${item.resource_path || item.title || ''}`"
            class="list-card student-diagnosis-v2-evidence-item"
            :class="`student-diagnosis-v2-evidence-${item.type}`"
          >
            <div class="list-title">
              <span class="student-diagnosis-v2-evidence-type">{{ evidenceTypeLabel(item.type) }}</span>
              <span>{{ item.node_id || '未绑定知识点' }}</span>
            </div>
            <div class="list-meta">{{ formatTime(item.occurred_at) }}</div>
            <div>{{ evidenceSummary(item) }}</div>
          </div>
          <div v-if="!evidenceTimeline.length" class="list-card student-diagnosis-v2-no-evidence">
            暂无测验、作业或资源学习证据
          </div>
        </div>
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
import {fetchStudentDiagnosis, fetchStudentTwin, refreshStudentTwin} from "../../api/student";
import type {DiagnosisEvidenceTimelineItem, StudentDiagnosisReport, StudentTwinSummary} from "../../types/student";
import i18n from "../../locale";

const { t } = i18n.global;

const loading = ref(false);
const error = ref("");
const summary = ref<StudentTwinSummary | null>(null);
const diagnosis = ref<StudentDiagnosisReport | null>(null);
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

const evidenceTimeline = computed<DiagnosisEvidenceTimelineItem[]>(() => {
  const items = diagnosis.value?.teacher_view?.evidence_timeline ?? [];
  return items.slice(0, 8);
});

// 新增：诊断元信息计算属性
const diagnosisTime = computed(() => {
  // 使用后端返回的生成时间
  if (summary.value?.generated_at) {
    const date = new Date(summary.value.generated_at);
    return date.toLocaleString('zh-CN', { 
      year: 'numeric', 
      month: '2-digit', 
      day: '2-digit', 
      hour: '2-digit', 
      minute: '2-digit' 
    });
  }
  // fallback：使用当前时间
  const now = new Date();
  return now.toLocaleString('zh-CN', { 
    year: 'numeric', 
    month: '2-digit', 
    day: '2-digit', 
    hour: '2-digit', 
    minute: '2-digit' 
  });
});

const riskLevelClass = computed(() => {
  const alerts = summary.value?.risk_alerts ?? [];
  if (alerts.some(r => r.level === 'high')) return 'student-diagnosis-v2-risk-high';
  if (alerts.some(r => r.level === 'medium')) return 'student-diagnosis-v2-risk-medium';
  return 'student-diagnosis-v2-risk-low';
});

const riskLevelLabel = computed(() => {
  const alerts = summary.value?.risk_alerts ?? [];
  if (alerts.some(r => r.level === 'high')) return '高风险';
  if (alerts.some(r => r.level === 'medium')) return '中等风险';
  return '低风险';
});

const weakNodeCount = computed(() => {
  return summary.value?.weak_nodes?.length ?? 0;
});

const strongNodeCount = computed(() => {
  return summary.value?.node_summary?.strong_node_count ?? 0;
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

function formatTime(value?: string | null) {
  if (!value) return "-";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleString("zh-CN", {
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function evidenceTypeLabel(type?: string) {
  const mapping: Record<string, string> = {
    quiz: "测验",
    homework: "作业",
    resource_learning: "资源学习",
  };
  return mapping[type || ""] || "学习证据";
}

function evidenceSummary(item: DiagnosisEvidenceTimelineItem) {
  if (item.type === "quiz") {
    return `测验得分 ${formatScore(item.score)} / ${formatScore(item.total)}，${item.passed ? "已通过" : "需巩固"}`;
  }
  if (item.type === "homework") {
    return `${item.title || "作业"}：${item.status || "已提交"}，得分 ${formatScore(item.score)} / ${formatScore(item.total)}`;
  }
  if (item.type === "resource_learning") {
    const progress = Number(item.progress_percent ?? 0).toFixed(0);
    const duration = Math.round(Number(item.duration_seconds ?? 0) / 60);
    return `${item.event_type || "学习"}，进度 ${progress}%${duration > 0 ? `，约 ${duration} 分钟` : ""}`;
  }
  return "学习证据已记录";
}

async function loadDiagnosis(studentUsername: string) {
  try {
    diagnosis.value = await fetchStudentDiagnosis(studentUsername);
  } catch (err) {
    diagnosis.value = null;
    console.warn("Student diagnosis timeline unavailable:", err);
  }
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

function riskIcon(level?: string) {
  const mapping: Record<string, string> = {
    high: '🔴',
    medium: '⚠️',
    low: '🟡',
  };
  return mapping[level ?? "medium"] ?? '⚠️';
}

async function loadSummary() {
  loading.value = true;
  error.value = "";
  try {
    const user = await fetchCurrentUser();
    username.value = user.username;
    summary.value = await fetchStudentTwin(user.username);
    await loadDiagnosis(user.username);
    await nextTick();
    renderCharts();
  } catch (err) {
    if (axios.isAxiosError(err) && err.response?.status === 404 && username.value) {
      try {
        await refreshStudentTwin(username.value);
        summary.value = await fetchStudentTwin(username.value);
        await loadDiagnosis(username.value);
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
    await loadDiagnosis(username.value);
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
