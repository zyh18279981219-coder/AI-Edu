<template>
  <div class="student-twin-shell">
    <!-- 诊断报告头部 -->
    <div class="student-diagnosis-v2-header">
      <div class="student-diagnosis-v2-header-content">
        <div class="student-diagnosis-v2-eyebrow">学生画像</div>
        <h1 class="student-diagnosis-v2-title">🔍 学生画像</h1>
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
          <div v-if="radarMetricItems.length" class="student-diagnosis-v2-metric-chips" aria-label="画像指标证据下钻">
            <button
              v-for="item in radarMetricItems"
              :key="item.name"
              class="student-diagnosis-v2-metric-chip"
              :class="{ active: evidenceFocus.type === 'metric' && evidenceFocus.metricName === item.name }"
              type="button"
              @click="focusRadarMetric(item.name)"
            >
              <span>{{ item.name }}</span>
              <strong>{{ formatScore(item.value) }}</strong>
            </button>
          </div>
        </article>
        <article class="card-panel">
          <div class="section-head">
            <h2>📈 学习趋势</h2>
            <span class="muted">近 30 天掌握度变化</span>
          </div>
          <div ref="trendRef" class="chart-box"></div>
        </article>
      </section>

      <section v-if="trendAttributionItems.length" class="card-panel student-diagnosis-v2-attribution-panel">
        <div class="section-head">
          <h2>趋势异常归因</h2>
          <span class="muted">基于画像快照与当天学习证据</span>
        </div>
        <div class="student-diagnosis-v2-attribution-grid">
          <article
            v-for="item in trendAttributionItems"
            :key="`${item.previous_date}-${item.date}`"
            class="student-diagnosis-v2-attribution-card"
            :class="{ active: evidenceFocus.type === 'snapshot' && evidenceFocus.date === item.date }"
            role="button"
            tabindex="0"
            @click="focusTrendAttribution(item)"
            @keydown.enter.prevent="focusTrendAttribution(item)"
            @keydown.space.prevent="focusTrendAttribution(item)"
          >
            <div class="list-title">
              <span>{{ item.date }}</span>
              <span class="student-diagnosis-v2-drop-pill">下降 {{ formatScore(item.drop) }} 分</span>
            </div>
            <div class="list-meta">
              {{ item.previous_date }}：{{ formatScore(item.previous_mastery) }}% → {{ formatScore(item.current_mastery) }}%
            </div>
            <div class="student-diagnosis-v2-snapshot-grid">
              <span>{{ item.evidence_status_label || evidenceLevelLabel(item.evidence_level) }}</span>
              <span>{{ item.primary_reason || "待结合证据核查" }}</span>
              <span>{{ snapshotCompareText(item) }}</span>
            </div>
            <p>{{ item.reason_summary }}</p>
            <div v-if="item.evidence_summary?.length" class="student-diagnosis-v2-attribution-summary">
              <div v-for="summaryItem in item.evidence_summary" :key="`${summaryItem.type}-${summaryItem.label}`">
                <strong>{{ summaryItem.label }}</strong>
                <span>{{ summaryItem.count }} 条</span>
                <em>{{ summaryItem.detail }}</em>
              </div>
            </div>
            <div class="student-diagnosis-v2-attribution-evidence">
              <div v-for="evidence in item.evidence" :key="`${evidence.type}-${evidence.occurred_at}-${evidence.node_id}`">
                <strong>{{ evidenceTypeLabel(evidence.type) }}</strong>
                <span>{{ evidence.node_id || "未绑定知识点" }}</span>
                <em>{{ evidence.summary }}</em>
              </div>
              <div v-if="!item.evidence.length" class="list-meta">依据不足：当天缺少可直接关联证据</div>
            </div>
            <div class="student-diagnosis-v2-action-row">
              <span v-for="action in item.suggested_actions" :key="action">{{ action }}</span>
            </div>
          </article>
        </div>
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
            <div
              v-for="node in pagedWeakNodes"
              :key="node.node_id"
              class="list-card student-diagnosis-v2-weak-node-item"
              :class="{ active: evidenceFocus.nodeId === node.node_id }"
              role="button"
              tabindex="0"
              @click="focusWeakNode(node.node_id)"
              @keydown.enter.prevent="focusWeakNode(node.node_id)"
              @keydown.space.prevent="focusWeakNode(node.node_id)"
            >
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

      <section class="detail-grid">
        <article class="card-panel">
          <div class="section-head">
            <h2>章节综合实践能力</h2>
            <span class="muted">{{ practiceSummaryText }}</span>
          </div>
          <div class="stack-list">
            <div
              v-for="item in practiceItems"
              :key="item.chapter"
              class="list-card student-diagnosis-v2-practice-item"
            >
              <div class="list-title">
                <span>{{ item.chapter }}</span>
                <span class="student-diagnosis-v2-level-text">{{ item.practice_level }}</span>
              </div>
              <div class="student-diagnosis-v2-stat-row">
                <span class="student-diagnosis-v2-stat-label">实践得分:</span>
                <span class="student-diagnosis-v2-stat-value">{{ formatScore(item.practice_score) }}%</span>
                <div class="student-diagnosis-v2-mini-progress">
                  <div class="student-diagnosis-v2-mini-progress-fill" :style="{ width: formatScore(item.practice_score) + '%' }"></div>
                </div>
              </div>
              <div class="list-meta">
                {{ item.evidence_count }} 条证据，代码题 {{ item.code_evidence_count }} 条，主观题 {{ item.subjective_evidence_count }} 条
              </div>
              <div v-if="item.latest_evidence_at" class="list-meta">最近证据：{{ formatTime(item.latest_evidence_at) }}</div>
            </div>
            <div v-if="!practiceItems.length" class="list-card student-diagnosis-v2-no-evidence">
              暂无章节主观题或代码题评分证据
            </div>
          </div>
        </article>

        <article class="card-panel">
          <div class="section-head">
            <h2>职业能力达成</h2>
            <span class="muted">{{ careerAbilitySummaryText }}</span>
          </div>
          <div v-if="careerAbilityItems.length" class="student-diagnosis-v2-career-overview">
            <div class="student-diagnosis-v2-career-score">
              <strong>{{ formatScore(careerAbilityAverage) }}</strong>
              <span>综合达成度</span>
            </div>
            <div class="student-diagnosis-v2-career-levels">
              <div
                v-for="item in careerAbilityLevelStats"
                :key="item.level"
                class="student-diagnosis-v2-career-level"
                :class="`student-diagnosis-v2-career-level-${item.code}`"
              >
                <span>{{ item.level }}</span>
                <strong>{{ item.count }}</strong>
              </div>
            </div>
          </div>
          <div class="stack-list student-diagnosis-v2-career-list">
            <div
              v-for="item in careerAbilityItems"
              :key="item.ability_id"
              class="list-card student-diagnosis-v2-career-item"
              :class="careerAbilityLevelClass(item.level)"
            >
              <div class="student-diagnosis-v2-career-main">
                <div>
                  <div class="list-title">{{ item.ability_name }}</div>
                  <div class="list-meta">{{ item.position_name || "课程目标能力" }}</div>
                </div>
                <span class="student-diagnosis-v2-career-badge">{{ item.level }}</span>
              </div>
              <div class="student-diagnosis-v2-stat-row">
                <span class="student-diagnosis-v2-stat-label">达成度:</span>
                <span class="student-diagnosis-v2-stat-value">{{ formatScore(item.attainment_score) }}%</span>
                <div class="student-diagnosis-v2-mini-progress">
                  <div class="student-diagnosis-v2-mini-progress-fill" :style="{ width: formatScore(item.attainment_score) + '%' }"></div>
                </div>
              </div>
              <div v-if="item.gap_nodes?.length" class="student-diagnosis-v2-gap-list">
                <span
                  v-for="node in item.gap_nodes.slice(0, 3)"
                  :key="`${item.ability_id}-${node.node_id}`"
                  class="student-diagnosis-v2-gap-chip"
                >
                  {{ node.node_name || node.node_id }}
                  <em>{{ formatScore(node.mastery_score) }}%</em>
                </span>
              </div>
              <div v-else class="student-diagnosis-v2-gap-clear">暂无明显缺口，可继续做拓展练习。</div>
              <div class="student-diagnosis-v2-career-action">
                {{ careerAbilityActionText(item.level, item.gap_nodes?.length ?? 0) }}
              </div>
            </div>
            <div v-if="!careerAbilityItems.length" class="list-card student-diagnosis-v2-no-evidence">
              暂无已发布的职业能力映射结果
            </div>
          </div>
        </article>
      </section>

      <section class="detail-grid">
        <article class="card-panel">
          <div class="section-head">
            <h2>作业覆盖知识点证据</h2>
            <span class="muted">教师确认后才作为叶子知识点辅助证据</span>
          </div>
          <div class="stack-list">
            <div
              v-for="item in homeworkEvidenceItems"
              :key="item.node_id"
              class="list-card student-diagnosis-v2-practice-item"
            >
              <div class="list-title">{{ item.node_id }}</div>
              <div class="student-diagnosis-v2-stat-row">
                <span class="student-diagnosis-v2-stat-label">作业辅助分:</span>
                <span class="student-diagnosis-v2-stat-value">{{ formatScore(item.auxiliary_score) }}%</span>
              </div>
              <div class="list-meta">
                {{ item.evidence_count }} 条确认覆盖证据，掌握度参考修正 {{ signedDelta(item.weighted_mastery_delta) }}
              </div>
              <div v-if="item.latest_evidence_at" class="list-meta">最近证据：{{ formatTime(item.latest_evidence_at) }}</div>
            </div>
            <div v-if="!homeworkEvidenceItems.length" class="list-card student-diagnosis-v2-no-evidence">
              暂无教师确认的作业覆盖知识点证据
            </div>
          </div>
        </article>
      </section>

      <section class="card-panel student-diagnosis-v2-evidence-panel">
        <div class="section-head">
          <h2>证据时间线</h2>
          <span class="muted">{{ evidenceTimelineTitle }}</span>
        </div>
        <div v-if="evidenceFocus.label" class="student-diagnosis-v2-evidence-focus">
          <strong>{{ evidenceFocus.label }}</strong>
          <span>{{ evidenceFocus.description }}</span>
          <button class="ghost-btn tiny" type="button" @click="clearEvidenceFocus">清除筛选</button>
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
            {{ evidenceEmptyText }}
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
import type {
  StudentDiagnosisEvidenceTimelineItem,
  StudentDiagnosisReport,
  StudentTwinSummary,
  TrendAttributionPoint,
} from "../../types/student";
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

type EvidenceFocus = {
  type: "all" | "node" | "metric" | "snapshot";
  label: string;
  description: string;
  metricName?: string;
  nodeId?: string;
  evidenceTypes?: string[];
  date?: string;
};

const evidenceFocus = ref<EvidenceFocus>({
  type: "all",
  label: "",
  description: "",
});

const pagedWeakNodes = computed(() => {
  const items = summary.value?.weak_nodes ?? [];
  const start = (weakNodePage.value - 1) * pageSize;
  return items.slice(start, start + pageSize);
});

const totalWeakPages = computed(() => {
  const items = summary.value?.weak_nodes ?? [];
  return Math.max(1, Math.ceil(items.length / pageSize));
});

const evidenceTimeline = computed<StudentDiagnosisEvidenceTimelineItem[]>(() => {
  const items = diagnosis.value?.student_view?.evidence_timeline ?? [];
  return items.filter(matchesEvidenceFocus).slice(0, 8);
});

const evidenceTimelineTitle = computed(() => {
  const total = diagnosis.value?.student_view?.evidence_timeline?.length ?? 0;
  if (!evidenceFocus.value.label) return `最近 ${evidenceTimeline.value.length} / ${total} 条学习证据`;
  return `已筛选 ${evidenceTimeline.value.length} / ${total} 条学习证据`;
});

const evidenceEmptyText = computed(() => {
  const focus = evidenceFocus.value;
  if (focus.type === "node" && focus.nodeId) {
    return `暂未追溯到“${focus.nodeId}”的测验、作业或资源学习证据，建议先完成一次小测或相关任务补齐依据。`;
  }
  if (focus.type === "snapshot" && focus.date) {
    return `该快照日期暂无可直接关联的学习证据，不能强行归因，建议补充当天测验、作业或学习记录。`;
  }
  if (focus.type === "metric" && focus.metricName) {
    return `${focus.metricName} 暂无足够可追溯证据，系统不会用 0 分替代诊断，建议补充对应测验、作业或学习记录。`;
  }
  return "暂无测验、作业或资源学习证据。";
});

const practiceItems = computed(() => (summary.value?.chapter_practice ?? []).slice(0, 5));

const careerAbilityItems = computed(() => (summary.value?.career_abilities ?? []).slice(0, 5));

const careerAbilityAverage = computed(() => {
  const items = careerAbilityItems.value;
  if (!items.length) return 0;
  return items.reduce((total, item) => total + Number(item.attainment_score ?? 0), 0) / items.length;
});

const careerAbilityLevelStats = computed(() => {
  const items = careerAbilityItems.value;
  const levels = [
    { level: "待提升", code: "need" },
    { level: "基本达成", code: "basic" },
    { level: "较好达成", code: "strong" },
  ];
  return levels.map((level) => ({
    ...level,
    count: items.filter((item) => item.level === level.level).length,
  }));
});

const careerAbilitySummaryText = computed(() => {
  const items = careerAbilityItems.value;
  if (!items.length) return "等待课程发布能力映射";
  const needImprove = items.filter((item) => item.level === "待提升").length;
  if (needImprove > 0) return `${needImprove} 项能力待提升，优先补齐缺口知识点`;
  return `已展示 ${items.length} 项课程相关职业能力`;
});

const homeworkEvidenceItems = computed(() => (summary.value?.knowledge_point_homework_evidence ?? []).slice(0, 5));

const trendAttributionItems = computed(() => (summary.value?.trend?.attribution_points ?? []).slice(0, 3));

const radarMetricItems = computed(() => summary.value?.radar ?? []);

const practiceSummaryText = computed(() => {
  const practice = summary.value?.practice_summary;
  if (!practice || practice.average_practice_score == null) return "等待章节实践证据";
  return `${practice.practice_level}，平均 ${formatScore(practice.average_practice_score)}%`;
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

function signedDelta(value?: number) {
  const numeric = Number(value ?? 0);
  if (numeric > 0) return `+${numeric.toFixed(1)}`;
  return numeric.toFixed(1);
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
    fivee_effectiveness: "5E 引导",
    intervention_completion: "干预任务",
    path_node_completion: "路径完成",
  };
  return mapping[type || ""] || "学习证据";
}

function evidenceLevelLabel(level?: string) {
  const mapping: Record<string, string> = {
    sufficient: "依据充分",
    partial: "依据一般，需要继续观察",
    insufficient: "依据不足，建议补充学习证据",
  };
  return mapping[level || ""] || "待观察";
}

function careerAbilityLevelClass(level?: string) {
  if (level === "较好达成") return "student-diagnosis-v2-career-strong";
  if (level === "基本达成") return "student-diagnosis-v2-career-basic";
  return "student-diagnosis-v2-career-need";
}

function careerAbilityActionText(level?: string, gapCount = 0) {
  if (level === "较好达成") return "建议进入综合项目或拓展任务，保持能力迁移训练。";
  if (level === "基本达成") {
    return gapCount > 0 ? "建议先复习缺口知识点，再完成一组综合练习。" : "建议通过测验或实践任务继续巩固。";
  }
  return gapCount > 0 ? "建议把这些缺口知识点加入个性化学习路径优先补强。" : "建议先完成相关测验或作业，补充诊断依据。";
}

function snapshotCompareText(item: TrendAttributionPoint) {
  const compare = item.snapshot_compare;
  if (!compare) return `下降 ${formatScore(item.drop)} 分`;
  const previous = compare.previous?.overall_mastery ?? item.previous_mastery;
  const current = compare.current?.overall_mastery ?? item.current_mastery;
  const change = compare.change ?? current - previous;
  return `快照 ${formatScore(previous)}% -> ${formatScore(current)}%，变化 ${formatScore(change)} 分`;
}

function evidenceSummary(item: StudentDiagnosisEvidenceTimelineItem) {
  if (item.summary) return item.summary;
  if (item.type === "quiz") {
    return `测验得分 ${formatScore(item.score)} / ${formatScore(item.total)}，${item.passed ? "已通过" : "需巩固"}`;
  }
  if (item.type === "homework") {
    return `${item.title || "作业"}，${item.status || "已记录"}，得分 ${formatScore(item.score)} / ${formatScore(item.total)}`;
  }
  if (item.type === "resource_learning") {
    const progress = Number(item.progress_percent ?? 0).toFixed(0);
    return `资源学习进度 ${progress}%`;
  }
  if (item.type === "fivee_effectiveness") {
    const parts = [
      item.stage ? `阶段 ${stageLabel(item.stage)}` : "",
      item.effectiveness_level ? `效果 ${item.effectiveness_level}` : "效果待观察",
      item.evidence_status === "insufficient_evidence" ? "依据不足" : "",
      item.evidence_status === "process_only" ? "目前是过程证据，需结合测验或作业继续判断" : "",
      item.mastery_update_policy === "not_updated_by_5e_effectiveness" ? "辅助证据，不直接改写掌握度" : "",
    ].filter(Boolean);
    return parts.length ? parts.join("，") : "5E 引导互动已记录";
  }
  if (item.type === "intervention_completion") {
    const completion = item.completion_rate != null ? `完成率 ${formatScore(Number(item.completion_rate) * 100)}%` : "";
    const policy = item.mastery_update_policy === "intervention_completion_is_auxiliary_evidence"
      ? "干预完成结果作为辅助证据"
      : "";
    const parts = [completion, policy].filter(Boolean);
    return parts.length ? parts.join("，") : "干预任务完成记录已同步";
  }
  if (item.type === "path_node_completion") {
    return "个性化路径节点完成记录已同步，作为后续诊断的辅助证据";
  }
  return "学习证据已记录";
}

function stageLabel(stage?: string | null) {
  const mapping: Record<string, string> = {
    engagement: "引入",
    exploration: "探究",
    explanation: "解释",
    elaboration: "迁移应用",
    evaluation: "评价",
  };
  return mapping[String(stage || "")] || String(stage || "未知阶段");
}

function matchesEvidenceFocus(item: StudentDiagnosisEvidenceTimelineItem) {
  const focus = evidenceFocus.value;
  if (focus.type === "all") return true;
  if (focus.nodeId && item.node_id !== focus.nodeId) return false;
  if (focus.evidenceTypes?.length && !focus.evidenceTypes.includes(item.type)) return false;
  if (focus.date && !sameEvidenceDate(item.occurred_at, focus.date)) return false;
  return true;
}

function sameEvidenceDate(value: string | null | undefined, targetDate: string) {
  if (!value || !targetDate) return false;
  const parsed = new Date(value);
  if (!Number.isNaN(parsed.getTime())) {
    return parsed.toISOString().slice(0, 10) === targetDate;
  }
  return String(value).slice(0, 10) === targetDate;
}

function focusWeakNode(nodeId: string) {
  evidenceFocus.value = {
    type: "node",
    nodeId,
    label: `薄弱知识点：${nodeId}`,
    description: "查看与该知识点直接相关的测验、作业、资源学习和过程证据。",
  };
}

function focusTrendAttribution(item: TrendAttributionPoint) {
  evidenceFocus.value = {
    type: "snapshot",
    date: item.date,
    label: `趋势快照：${item.previous_date} -> ${item.date}`,
    description: item.reason_summary,
  };
}

function focusRadarMetric(metricName: string) {
  const name = String(metricName || "");
  const metricMap: Array<{ keyword: string; evidenceTypes: string[]; label: string; description: string }> = [
    {
      keyword: "知识",
      evidenceTypes: ["quiz", "homework", "path_node_completion"],
      label: "知识掌握证据",
      description: "查看支撑知识掌握度的测验、作业反馈和路径节点完成记录。",
    },
    {
      keyword: "测验",
      evidenceTypes: ["quiz"],
      label: "测验表现证据",
      description: "查看支撑测验表现的在线测验记录。",
    },
    {
      keyword: "实践",
      evidenceTypes: ["homework"],
      label: "章节实践证据",
      description: "查看章节主观题、代码题和教师确认覆盖知识点的作业证据。",
    },
    {
      keyword: "投入",
      evidenceTypes: ["resource_learning", "fivee_effectiveness", "intervention_completion"],
      label: "学习投入证据",
      description: "查看资源学习、5E 引导互动和干预任务完成等过程证据。",
    },
    {
      keyword: "稳定",
      evidenceTypes: ["quiz", "homework", "resource_learning", "fivee_effectiveness", "path_node_completion"],
      label: "学习稳定证据",
      description: "查看支撑学习稳定性的近期测验、作业、资源学习、5E 过程和路径完成记录；趋势低谷可点击趋势图或异常卡查看快照。",
    },
  ];
  const matched = metricMap.find((item) => name.includes(item.keyword));
  evidenceFocus.value = matched
    ? {
        type: "metric",
        metricName: name,
        evidenceTypes: matched.evidenceTypes,
        label: matched.label,
        description: matched.description,
      }
    : {
        type: "metric",
        metricName: name,
        label: `${name || "画像指标"}相关证据`,
        description: "查看与该画像指标相关的学习证据，若证据不足则不强行下结论。",
      };
}

function clearEvidenceFocus() {
  evidenceFocus.value = {
    type: "all",
    label: "",
    description: "",
  };
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
  radarChart.off("click");
  radarChart.on("click", (params: any) => {
    const indicatorName = params?.name || params?.event?.target?.style?.text;
    if (indicatorName) {
      focusRadarMetric(String(indicatorName));
    }
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
  trendChart.off("click");
  trendChart.on("click", (params: any) => {
    const date = String(params?.name || "");
    const attribution = trendAttributionItems.value.find((item) => item.date === date);
    if (attribution) {
      focusTrendAttribution(attribution);
    } else if (date) {
      evidenceFocus.value = {
        type: "snapshot",
        date,
        label: `画像快照：${date}`,
        description: "该日期没有明显异常掉分归因，仅展示当天可追溯证据。",
      };
    }
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

<style scoped>
.student-diagnosis-v2-attribution-panel {
  margin-top: 16px;
}

.student-diagnosis-v2-metric-chips {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(116px, 1fr));
  gap: 8px;
  margin-top: 12px;
}

.student-diagnosis-v2-metric-chip {
  display: flex;
  min-width: 0;
  min-height: 42px;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  border: 1px solid #dbeafe;
  border-radius: 8px;
  padding: 8px 10px;
  background: #f8fbff;
  color: #334155;
  cursor: pointer;
  transition: border-color 0.2s, box-shadow 0.2s, background 0.2s;
}

.student-diagnosis-v2-metric-chip span {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-size: 13px;
}

.student-diagnosis-v2-metric-chip strong {
  flex: 0 0 auto;
  color: #1d4ed8;
  font-size: 15px;
}

.student-diagnosis-v2-metric-chip:hover,
.student-diagnosis-v2-metric-chip:focus-visible,
.student-diagnosis-v2-metric-chip.active {
  border-color: #2563eb;
  background: #eff6ff;
  box-shadow: 0 8px 20px rgba(37, 99, 235, 0.12);
  outline: none;
}

.student-diagnosis-v2-attribution-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
  gap: 12px;
}

.student-diagnosis-v2-attribution-card {
  display: grid;
  gap: 10px;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  padding: 12px;
  background: #fff;
  cursor: pointer;
  transition: border-color 0.2s, box-shadow 0.2s, transform 0.2s;
}

.student-diagnosis-v2-attribution-card:hover,
.student-diagnosis-v2-attribution-card:focus-visible,
.student-diagnosis-v2-attribution-card.active,
.student-diagnosis-v2-weak-node-item:hover,
.student-diagnosis-v2-weak-node-item:focus-visible,
.student-diagnosis-v2-weak-node-item.active {
  border-color: #2563eb;
  box-shadow: 0 10px 24px rgba(37, 99, 235, 0.12);
  outline: none;
}

.student-diagnosis-v2-attribution-card:hover,
.student-diagnosis-v2-weak-node-item:hover {
  transform: translateY(-1px);
}

.student-diagnosis-v2-weak-node-item {
  cursor: pointer;
  transition: border-color 0.2s, box-shadow 0.2s, transform 0.2s;
}

.student-diagnosis-v2-attribution-card p {
  margin: 0;
  color: #334155;
  line-height: 1.65;
}

.student-diagnosis-v2-drop-pill {
  border-radius: 999px;
  background: #fee2e2;
  color: #991b1b;
  padding: 3px 8px;
  font-size: 12px;
}

.student-diagnosis-v2-snapshot-grid,
.student-diagnosis-v2-attribution-summary {
  display: grid;
  gap: 6px;
}

.student-diagnosis-v2-snapshot-grid {
  grid-template-columns: repeat(auto-fit, minmax(120px, 1fr));
}

.student-diagnosis-v2-snapshot-grid span {
  border: 1px solid #dbeafe;
  border-radius: 8px;
  padding: 7px 8px;
  background: #f8fbff;
  color: #1e3a8a;
  font-size: 12px;
  line-height: 1.45;
}

.student-diagnosis-v2-attribution-summary div {
  display: grid;
  grid-template-columns: 72px 48px minmax(120px, 1fr);
  gap: 8px;
  align-items: center;
  border-radius: 8px;
  padding: 8px;
  background: #f8fafc;
  color: #475569;
  font-size: 13px;
}

.student-diagnosis-v2-attribution-summary em {
  min-width: 0;
  overflow-wrap: anywhere;
  color: #64748b;
  font-style: normal;
}

.student-diagnosis-v2-attribution-evidence {
  display: grid;
  gap: 6px;
}

.student-diagnosis-v2-attribution-evidence div {
  display: grid;
  grid-template-columns: 72px minmax(90px, 1fr) minmax(140px, 1.5fr);
  gap: 8px;
  align-items: center;
  color: #64748b;
  font-size: 13px;
}

.student-diagnosis-v2-attribution-evidence em {
  color: #0f172a;
  font-style: normal;
}

.student-diagnosis-v2-action-row {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.student-diagnosis-v2-action-row span {
  border: 1px solid #bfdbfe;
  border-radius: 999px;
  color: #1d4ed8;
  padding: 3px 8px;
  font-size: 12px;
}

.student-diagnosis-v2-career-overview {
  display: grid;
  grid-template-columns: 132px minmax(0, 1fr);
  gap: 12px;
  margin-bottom: 12px;
}

.student-diagnosis-v2-career-score {
  display: grid;
  min-height: 92px;
  align-content: center;
  justify-items: center;
  border: 1px solid #ccfbf1;
  border-radius: 8px;
  background: linear-gradient(180deg, #f0fdfa 0%, #ecfeff 100%);
  color: #0f766e;
}

.student-diagnosis-v2-career-score strong {
  font-size: 30px;
  line-height: 1;
}

.student-diagnosis-v2-career-score span {
  margin-top: 6px;
  color: #475569;
  font-size: 12px;
}

.student-diagnosis-v2-career-levels {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 8px;
}

.student-diagnosis-v2-career-level {
  display: grid;
  min-width: 0;
  min-height: 92px;
  align-content: center;
  gap: 6px;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  padding: 10px;
  background: #f8fafc;
}

.student-diagnosis-v2-career-level span {
  overflow-wrap: anywhere;
  color: #64748b;
  font-size: 12px;
}

.student-diagnosis-v2-career-level strong {
  color: #0f172a;
  font-size: 24px;
}

.student-diagnosis-v2-career-level-need {
  border-color: #fecaca;
  background: #fff7f7;
}

.student-diagnosis-v2-career-level-basic {
  border-color: #fde68a;
  background: #fffbeb;
}

.student-diagnosis-v2-career-level-strong {
  border-color: #bbf7d0;
  background: #f0fdf4;
}

.student-diagnosis-v2-career-list {
  gap: 10px;
}

.student-diagnosis-v2-career-item {
  display: grid;
  gap: 10px;
  border-left: 4px solid #94a3b8;
}

.student-diagnosis-v2-career-need {
  border-left-color: #dc2626;
}

.student-diagnosis-v2-career-basic {
  border-left-color: #d97706;
}

.student-diagnosis-v2-career-strong {
  border-left-color: #16a34a;
}

.student-diagnosis-v2-career-main {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  gap: 10px;
  align-items: start;
}

.student-diagnosis-v2-career-main .list-title {
  overflow-wrap: anywhere;
}

.student-diagnosis-v2-career-badge {
  border-radius: 999px;
  padding: 4px 9px;
  background: #eef2ff;
  color: #3730a3;
  font-size: 12px;
  white-space: nowrap;
}

.student-diagnosis-v2-gap-list {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.student-diagnosis-v2-gap-chip {
  display: inline-flex;
  max-width: 100%;
  align-items: center;
  gap: 6px;
  border: 1px solid #fed7aa;
  border-radius: 999px;
  padding: 4px 8px;
  background: #fff7ed;
  color: #9a3412;
  font-size: 12px;
  line-height: 1.35;
  overflow-wrap: anywhere;
}

.student-diagnosis-v2-gap-chip em {
  color: #c2410c;
  font-style: normal;
  white-space: nowrap;
}

.student-diagnosis-v2-gap-clear {
  border-radius: 8px;
  padding: 8px 10px;
  background: #f0fdf4;
  color: #15803d;
  font-size: 13px;
}

.student-diagnosis-v2-career-action {
  border-radius: 8px;
  padding: 8px 10px;
  background: #f8fafc;
  color: #475569;
  font-size: 13px;
  line-height: 1.6;
}

.student-diagnosis-v2-evidence-focus {
  display: grid;
  grid-template-columns: minmax(0, auto) minmax(0, 1fr) auto;
  gap: 10px;
  align-items: center;
  margin-bottom: 12px;
  border: 1px solid #bfdbfe;
  border-radius: 10px;
  padding: 10px 12px;
  background: #eff6ff;
  color: #1e3a8a;
}

.student-diagnosis-v2-evidence-focus strong {
  white-space: nowrap;
}

.student-diagnosis-v2-evidence-focus span {
  color: #1d4ed8;
  font-size: 13px;
  line-height: 1.55;
}

.ghost-btn.tiny {
  min-height: 28px;
  padding: 0 10px;
  border-radius: 999px;
  font-size: 12px;
}

@media (max-width: 720px) {
  .student-diagnosis-v2-career-overview,
  .student-diagnosis-v2-career-main {
    grid-template-columns: 1fr;
  }

  .student-diagnosis-v2-career-levels {
    grid-template-columns: 1fr;
  }

  .student-diagnosis-v2-attribution-evidence div {
    grid-template-columns: 1fr;
  }

  .student-diagnosis-v2-evidence-focus {
    grid-template-columns: 1fr;
  }
}
</style>
