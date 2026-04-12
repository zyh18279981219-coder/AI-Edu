<template>
  <section class="industry-results">
    <div class="card-panel industry-result-head">
      <div>
        <p class="eyebrow">Analysis Result</p>
        <h2>{{ $t('student.industryIntelligence.resultBoard.analyzeResult') }}</h2>
      </div>
      <div class="industry-head-actions">
        <el-button plain :disabled="isRunning" @click="$emit('download')">{{ $t('student.industryIntelligence.resultBoard.downloadJson') }}</el-button>
      </div>
    </div>

    <div v-if="searchTerms.length" class="info-banner">
      <strong>{{ $t('student.industryIntelligence.resultBoard.searchKeywords') }}</strong>
      <span v-for="term in searchTerms" :key="term" class="skill-chip">{{ term }}</span>
    </div>

    <div v-if="result.relevance_message" class="info-banner">
      {{ result.relevance_message }}
    </div>

    <section class="metric-grid">
      <MetricStatCard
        v-for="card in metricCards"
        :key="card.label"
        :label="card.label"
        :value="card.value"
        :description="card.description"
        :tone="card.tone"
      />
    </section>

    <section class="card-panel industry-control-card">
      <div class="section-head">
        <h3>{{ $t('student.industryIntelligence.resultBoard.heatmapControl') }}</h3>
      </div>
      <div class="field-grid two-col">
        <label class="field">
          <span>{{ $t('student.industryIntelligence.resultBoard.displayedNumberOfSkills') }} <strong>{{ heatmapState.topSkills }}</strong></span>
          <el-slider v-model="heatmapState.topSkills" :min="5" :max="30" />
        </label>
        <label class="field">
          <span>{{ $t('student.industryIntelligence.resultBoard.displayedNumberOfJobs') }} <strong>{{ heatmapState.topJobs }}</strong></span>
          <el-slider v-model="heatmapState.topJobs" :min="3" :max="15" />
        </label>
      </div>
    </section>

    <article class="card-panel industry-chart-card wide">
      <div class="section-head">
        <h3>{{ $t('student.industryIntelligence.resultBoard.skillsHeatmap') }}</h3>
      </div>
      <div ref="heatmapChartRef" class="industry-chart heatmap"></div>
    </article>

    <div class="industry-chart-grid two-up">
      <article class="card-panel industry-chart-card">
        <div class="section-head">
          <h3>{{ $t('student.industryIntelligence.resultBoard.skillsRanking') }}</h3>
        </div>
        <div ref="skillChartRef" class="industry-chart"></div>
      </article>
      <article class="card-panel industry-chart-card">
        <div class="section-head">
          <h3>{{ $t('student.industryIntelligence.resultBoard.jobsDistribution') || '岗位分布' }}</h3>
        </div>
        <div ref="jobChartRef" class="industry-chart"></div>
      </article>
    </div>

    <div class="industry-chart-grid two-up">
      <article class="card-panel industry-chart-card">
        <div class="section-head">
          <h3>{{ $t('student.industryIntelligence.resultBoard.experienceRequirements') }}</h3>
        </div>
        <div ref="experienceChartRef" class="industry-chart small"></div>
      </article>
      <article class="card-panel industry-chart-card">
        <div class="section-head">
          <h3>{{ $t('student.industryIntelligence.resultBoard.educationalRequirements') }}</h3>
        </div>
        <div ref="educationChartRef" class="industry-chart small"></div>
      </article>
    </div>

    <article class="card-panel industry-table-card">
      <div class="section-head">
        <h3>{{ $t('student.industryIntelligence.resultBoard.jobDetails') }}</h3>
        <span class="muted">{{ jobs.length }} 条</span>
      </div>
      <div class="industry-table-wrap">
        <el-table :data="jobs" stripe table-layout="auto" class="industry-el-table">
          <el-table-column prop="title" :label="$t('student.industryIntelligence.resultBoard.job')" min-width="220" />
          <el-table-column prop="company" :label="$t('student.industryIntelligence.resultBoard.company')" min-width="160" />
          <el-table-column :label="$t('student.industryIntelligence.resultBoard.relativity')" width="110">
            <template #default="{ row }">
              <span class="relevance-pill">{{ row.relevance_score || 0 }}</span>
            </template>
          </el-table-column>
          <el-table-column :label="$t('student.industryIntelligence.resultBoard.salary')" min-width="120">
            <template #default="{ row }">{{ row.salary || $t('student.industryIntelligence.resultBoard.negotiable') }}</template>
          </el-table-column>
          <el-table-column :label="$t('student.industryIntelligence.resultBoard.experience')" min-width="110">
            <template #default="{ row }">{{ row.experience || $t('student.industryIntelligence.resultBoard.any') }}</template>
          </el-table-column>
          <el-table-column :label="$t('student.industryIntelligence.resultBoard.educationalBackground')" min-width="110">
            <template #default="{ row }">{{ row.education || $t('student.industryIntelligence.resultBoard.any') }}</template>
          </el-table-column>
          <el-table-column prop="location" :label="$t('student.industryIntelligence.resultBoard.location')" min-width="130" />
          <el-table-column prop="source" :label="$t('student.industryIntelligence.resultBoard.source')" width="110" />
          <el-table-column :label="$t('student.industryIntelligence.resultBoard.skills')" min-width="220">
            <template #default="{ row }">
              <div class="industry-skill-list">
                <span v-for="skill in (row.skills || []).slice(0, 5)" :key="skill" class="skill-chip">{{ skill }}</span>
                <span v-if="(row.skills || []).length > 5" class="skill-chip muted-chip">+{{ row.skills.length - 5 }}</span>
              </div>
            </template>
          </el-table-column>
          <el-table-column :label="$t('student.industryIntelligence.resultBoard.details')" width="110" fixed="right">
            <template #default="{ $index }">
              <el-button plain size="small" @click="selectedJobIndex = $index">{{ $t('student.industryIntelligence.resultBoard.showDetails') }}</el-button>
            </template>
          </el-table-column>
        </el-table>
      </div>
    </article>

    <el-drawer :model-value="!!selectedJob" size="38%" @close="selectedJobIndex = null">
      <template #header>
        <div>
          <p class="eyebrow">Job Detail</p>
          <h3>{{ selectedJob?.title || $t('student.industryIntelligence.resultBoard.jobDetails') }}</h3>
        </div>
      </template>
      <div v-if="selectedJob" class="industry-drawer-body">
        <div class="industry-meta-row">
          <span v-for="item in selectedJobMeta" :key="item" class="meta-chip">{{ item }}</span>
        </div>
        <section class="industry-detail-section">
          <h4>{{ $t('student.industryIntelligence.resultBoard.hitReason') }}</h4>
          <ul class="message-list">
            <li v-for="reason in selectedJob.relevance_reasons || [$t('student.industryIntelligence.resultBoard.noHitReason')]" :key="reason">{{ reason }}</li>
          </ul>
        </section>
        <section class="industry-detail-section">
          <h4>{{ $t('student.industryIntelligence.resultBoard.skillEvidence') }}</h4>
          <div v-if="(selectedJob.skill_evidence || []).length" class="industry-evidence-list">
            <article v-for="(item, index) in selectedJob.skill_evidence" :key="`${item.name}-${index}`" class="industry-evidence-card">
              <strong>{{ item.name || $t('student.industryIntelligence.resultBoard.skills') }}</strong>
              <p>{{ item.evidence || $t('student.industryIntelligence.resultBoard.noEvidence') }}</p>
            </article>
          </div>
          <p v-else class="muted">{{ $t('student.industryIntelligence.resultBoard.noEvidence') }}</p>
        </section>
        <section class="industry-detail-section">
          <h4>{{ $t('student.industryIntelligence.resultBoard.jobRequirements') }}</h4>
          <p class="industry-detail-text">{{ selectedJob.requirements || $t('student.industryIntelligence.resultBoard.noJobRequirements') }}</p>
        </section>
        <section class="industry-detail-section">
          <h4>{{ $t('student.industryIntelligence.resultBoard.jobDescription') }}</h4>
          <div class="industry-detail-text pre-wrap">
            <Markdown v-if="selectedJob.description" :content="selectedJob.description" />
            <p v-else>
              {{ $t('student.industryIntelligence.resultBoard.noJobDescription') }}
            </p>
          </div>
        </section>
      </div>
    </el-drawer>
  </section>
</template>

<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, reactive, ref, watch } from "vue";
import MetricStatCard from "../../../components/ui/MetricStatCard.vue";
import { type IndustryChartRow, type IndustryJob, type IndustryResult } from "../../../types/industry"
import { init, type ECharts } from "../../../lib/echarts";
import i18n from "../../../locale";

const props = defineProps<{
  result: IndustryResult;
  jobs: IndustryJob[];
  searchTerms: string[];
  isRunning: boolean;
}>();

defineEmits<{
  (event: "download"): void;
}>();

const {t}=i18n.global;

const selectedJobIndex = ref<number | null>(null);
const heatmapState = reactive({
  topSkills: 30,
  topJobs: 15,
});

const skillChartRef = ref<HTMLDivElement | null>(null);
const jobChartRef = ref<HTMLDivElement | null>(null);
const heatmapChartRef = ref<HTMLDivElement | null>(null);
const experienceChartRef = ref<HTMLDivElement | null>(null);
const educationChartRef = ref<HTMLDivElement | null>(null);

let resizeTimer: number | null = null;
let skillChart: ECharts | null = null;
let jobChart: ECharts | null = null;
let heatmapChart: ECharts | null = null;
let experienceChart: ECharts | null = null;
let educationChart: ECharts | null = null;

const metricCards = computed(() => {
  const metrics = props.result.metrics;
  return [
    { label: t('student.industryIntelligence.resultBoard.totalNumberOfPositions'), value: metrics?.jobs_total ?? 0, description: t('student.industryIntelligence.resultBoard.totalNumberOfPositionsDescription'), tone: "brand" as const },
    { label: t('student.industryIntelligence.resultBoard.analyzedJobs'), value: metrics?.jobs_analyzed ?? 0, description: t('student.industryIntelligence.resultBoard.analyzedJobsDescription'), tone: "success" as const },
    { label: t('student.industryIntelligence.resultBoard.totalNumberOfSkills'), value: metrics?.skills_total ?? 0, description: t('student.industryIntelligence.resultBoard.totalNumberOfSkillsDescription'), tone: "warning" as const },
    { label: t('student.industryIntelligence.resultBoard.totalNumberOfDataSource'), value: metrics?.sources_total ?? 0, description: t('student.industryIntelligence.resultBoard.totalNumberOfDataSourceDescription'), tone: "default" as const },
  ];
});

const selectedJob = computed<IndustryJob | null>(() => {
  if (selectedJobIndex.value == null) return null;
  return props.jobs[selectedJobIndex.value] ?? null;
});

const selectedJobMeta = computed(() => {
  const job = selectedJob.value;
  if (!job) return [];
  return [
    job.company,
    job.salary || t('student.industryIntelligence.resultBoard.negotiable'),
    job.location,
    job.source,
    job.experience,
    job.education,
    `相关性 ${job.relevance_score || 0}`,
  ].filter(Boolean) as string[];
});

watch(
  () => props.result,
  async () => {
    await nextTick();
    renderCharts();
  },
  { deep: true, immediate: true },
);

watch(
  () => [heatmapState.topSkills, heatmapState.topJobs, props.jobs.length],
  async () => {
    await nextTick();
    renderHeatmapFromJobs(props.jobs);
  },
);

function renderCharts() {
  renderSkillChart(props.result.charts?.skill_ranking ?? []);
  renderJobChart(props.result.charts?.job_distribution ?? []);
  renderHeatmapFromJobs(props.jobs ?? []);
  renderHorizontalBar(experienceChartRef.value, "experience", props.result.charts?.experience_distribution ?? []);
  renderHorizontalBar(educationChartRef.value, "education", props.result.charts?.education_distribution ?? []);
}

function renderSkillChart(data: IndustryChartRow[]) {
  if (!skillChartRef.value) return;
  skillChart ??= init(skillChartRef.value);
  skillChart.setOption({
    animationDuration: 280,
    tooltip: { trigger: "axis" },
    grid: { left: 110, right: 24, top: 12, bottom: 16 },
    xAxis: { type: "value", splitLine: { lineStyle: { color: "#e5edf8" } } },
    yAxis: { type: "category", inverse: true, data: data.map((item) => item.name), axisLabel: { width: 120, overflow: "truncate", fontSize: 12 } },
    series: [{ type: "bar", data: data.map((item) => item.value), itemStyle: { color: "#4f7cff", borderRadius: [0, 10, 10, 0] }, label: { show: true, position: "right", color: "#475569" } }],
  });
}

function renderJobChart(data: IndustryChartRow[]) {
  if (!jobChartRef.value) return;
  jobChart ??= init(jobChartRef.value);
  jobChart.setOption({
    animationDuration: 280,
    tooltip: { trigger: "item" },
    series: [{ type: "pie", radius: ["34%", "68%"], center: ["50%", "52%"], data, label: { formatter: "{b}\n{c}", color: "#334155" } }],
  });
}

function renderHeatmapFromJobs(jobItems: IndustryJob[]) {
  if (!heatmapChartRef.value) return;
  const heatmap = buildHeatmapData(jobItems, heatmapState.topSkills, heatmapState.topJobs);
  heatmapChart ??= init(heatmapChartRef.value);
  heatmapChart.setOption({
    animationDuration: 280,
    tooltip: {
      position: "top",
      formatter: (params: { value: [number, number, number] }) => {
        const skill = heatmap.skills[params.value[0]] ?? "";
        const job = heatmap.jobs[params.value[1]] ?? "";
        return `${job}<br/>${skill}: ${params.value[2]}`;
      },
    },
    grid: { left: 160, right: 22, top: 16, bottom: 72 },
    xAxis: { type: "category", data: heatmap.skills, splitArea: { show: true }, axisTick: { show: false }, axisLabel: { rotate: 34, interval: 0, fontSize: 12, color: "#475569" } },
    yAxis: { type: "category", data: heatmap.jobs, splitArea: { show: true }, axisTick: { show: false }, axisLabel: { width: 140, overflow: "truncate", fontSize: 12, color: "#475569" } },
    visualMap: { show: false, min: 0, max: getHeatmapMax(heatmap.matrix), inRange: { color: ["#fff7bc", "#fec44f", "#fe9929", "#ec7014", "#cc4c02"] } },
    series: [{ type: "heatmap", data: heatmap.matrix, label: { show: true, color: "#374151", fontSize: 12 }, emphasis: { itemStyle: { shadowBlur: 10, shadowColor: "rgba(204, 76, 2, 0.28)" } } }],
  });
}

function renderHorizontalBar(target: HTMLDivElement | null, type: "experience" | "education", data: IndustryChartRow[]) {
  if (!target) return;
  const chart = type === "experience" ? (experienceChart ??= init(target)) : (educationChart ??= init(target));
  chart.setOption({
    animationDuration: 280,
    tooltip: { trigger: "axis" },
    grid: { left: 110, right: 24, top: 12, bottom: 12 },
    xAxis: { type: "value", splitLine: { lineStyle: { color: "#e5edf8" } } },
    yAxis: { type: "category", inverse: true, data: data.map((item) => item.name), axisLabel: { width: 100, overflow: "truncate", fontSize: 12 } },
    series: [{ type: "bar", data: data.map((item) => item.value), itemStyle: { color: "#14b8a6", borderRadius: [0, 10, 10, 0] }, label: { show: true, position: "right", color: "#475569" } }],
  });
}

function buildHeatmapData(jobItems: IndustryJob[], topSkills: number, topJobs: number) {
  const jobCounts = new Map<string, number>();
  const pairCounts = new Map<string, number>();
  jobItems.forEach((job) => {
    const title = job.title || t('student.industryIntelligence.resultBoard.unknownJobs');
    jobCounts.set(title, (jobCounts.get(title) || 0) + 1);
    (job.skills || []).forEach((skill) => {
      const key = `${title}__${skill}`;
      pairCounts.set(key, (pairCounts.get(key) || 0) + 1);
    });
  });

  const visibleJobs = [...jobCounts.entries()].sort((a, b) => b[1] - a[1]).slice(0, topJobs).map(([name]) => name);
  const visibleSkillCounts = new Map<string, number>();
  jobItems.forEach((job) => {
    const title = job.title || t('student.industryIntelligence.resultBoard.unknownJobs');
    if (!visibleJobs.includes(title)) return;
    (job.skills || []).forEach((skill) => {
      visibleSkillCounts.set(skill, (visibleSkillCounts.get(skill) || 0) + 1);
    });
  });

  const visibleSkills = [...visibleSkillCounts.entries()].sort((a, b) => b[1] - a[1]).slice(0, topSkills).map(([name]) => name);
  const matrix: Array<[number, number, number]> = [];
  visibleJobs.forEach((jobName, jobIndex) => {
    visibleSkills.forEach((skillName, skillIndex) => {
      const value = pairCounts.get(`${jobName}__${skillName}`) || 0;
      if (value > 0) matrix.push([skillIndex, jobIndex, value]);
    });
  });

  const usedSkillIndexes = new Set(matrix.map((item) => item[0]));
  const filteredSkills = visibleSkills.filter((_, index) => usedSkillIndexes.has(index));
  const indexMap = new Map(filteredSkills.map((skill, index) => [skill, index]));
  const reindexedMatrix = matrix
    .map(([skillIndex, jobIndex, value]) => [indexMap.get(visibleSkills[skillIndex]), jobIndex, value] as [number | undefined, number, number])
    .filter((item): item is [number, number, number] => typeof item[0] === "number");

  return { skills: filteredSkills, jobs: visibleJobs, matrix: reindexedMatrix };
}

function getHeatmapMax(matrix: Array<[number, number, number]>) {
  if (!matrix.length) return 1;
  return Math.max(...matrix.map((item) => item[2] || 0), 1);
}

function handleResize() {
  if (resizeTimer) window.clearTimeout(resizeTimer);
  resizeTimer = window.setTimeout(() => {
    [skillChart, jobChart, heatmapChart, experienceChart, educationChart].forEach((chart) => chart?.resize());
  }, 120);
}

onMounted(() => {
  window.addEventListener("resize", handleResize);
});

onBeforeUnmount(() => {
  window.removeEventListener("resize", handleResize);
  [skillChart, jobChart, heatmapChart, experienceChart, educationChart].forEach((chart) => chart?.dispose());
});
</script>
