<template>
  <section class="industry-results">
    <div class="card-panel industry-result-head">
      <div>
        <p class="eyebrow">Analysis Result</p>
        <h2>分析结果</h2>
      </div>
      <div class="industry-head-actions">
        <el-button plain :disabled="isRunning" @click="$emit('download')">下载 JSON</el-button>
      </div>
    </div>

    <div v-if="searchTerms.length" class="info-banner">
      <strong>本次实际使用的搜索词：</strong>
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
        <h3>热力图控制</h3>
      </div>
      <div class="field-grid two-col">
        <label class="field">
          <span>显示技能数 <strong>{{ heatmapState.topSkills }}</strong></span>
          <el-slider v-model="heatmapState.topSkills" :min="5" :max="30" />
        </label>
        <label class="field">
          <span>显示岗位数 <strong>{{ heatmapState.topJobs }}</strong></span>
          <el-slider v-model="heatmapState.topJobs" :min="3" :max="15" />
        </label>
      </div>
    </section>

    <article class="card-panel industry-chart-card wide">
      <div class="section-head">
        <h3>技能热力图</h3>
      </div>
      <div ref="heatmapChartRef" class="industry-chart heatmap"></div>
    </article>

    <div class="industry-chart-grid two-up">
      <article class="card-panel industry-chart-card">
        <div class="section-head">
          <h3>技能排行</h3>
        </div>
        <div ref="skillChartRef" class="industry-chart"></div>
      </article>
      <article class="card-panel industry-chart-card">
        <div class="section-head">
          <h3>岗位分布</h3>
        </div>
        <div ref="jobChartRef" class="industry-chart"></div>
      </article>
    </div>

    <div class="industry-chart-grid two-up">
      <article class="card-panel industry-chart-card">
        <div class="section-head">
          <h3>经验要求</h3>
        </div>
        <div ref="experienceChartRef" class="industry-chart small"></div>
      </article>
      <article class="card-panel industry-chart-card">
        <div class="section-head">
          <h3>学历要求</h3>
        </div>
        <div ref="educationChartRef" class="industry-chart small"></div>
      </article>
    </div>

    <article class="card-panel industry-table-card">
      <div class="section-head">
        <h3>职位明细</h3>
        <span class="muted">{{ jobs.length }} 条</span>
      </div>
      <div class="industry-table-wrap">
        <el-table :data="jobs" stripe table-layout="auto" class="industry-el-table">
          <el-table-column prop="title" label="职位" min-width="220" />
          <el-table-column prop="company" label="公司" min-width="160" />
          <el-table-column label="相关性" width="110">
            <template #default="{ row }">
              <span class="relevance-pill">{{ row.relevance_score || 0 }}</span>
            </template>
          </el-table-column>
          <el-table-column label="薪资" min-width="120">
            <template #default="{ row }">{{ row.salary || "面议" }}</template>
          </el-table-column>
          <el-table-column label="经验" min-width="110">
            <template #default="{ row }">{{ row.experience || "不限" }}</template>
          </el-table-column>
          <el-table-column label="学历" min-width="110">
            <template #default="{ row }">{{ row.education || "不限" }}</template>
          </el-table-column>
          <el-table-column prop="location" label="地点" min-width="130" />
          <el-table-column prop="source" label="来源" width="110" />
          <el-table-column label="技能" min-width="220">
            <template #default="{ row }">
              <div class="industry-skill-list">
                <span v-for="skill in (row.skills || []).slice(0, 5)" :key="skill" class="skill-chip">{{ skill }}</span>
                <span v-if="(row.skills || []).length > 5" class="skill-chip muted-chip">+{{ row.skills.length - 5 }}</span>
              </div>
            </template>
          </el-table-column>
          <el-table-column label="详情" width="110" fixed="right">
            <template #default="{ $index }">
              <el-button plain size="small" @click="selectedJobIndex = $index">查看详情</el-button>
            </template>
          </el-table-column>
        </el-table>
      </div>
    </article>

    <el-drawer :model-value="!!selectedJob" size="38%" @close="selectedJobIndex = null">
      <template #header>
        <div>
          <p class="eyebrow">Job Detail</p>
          <h3>{{ selectedJob?.title || "职位详情" }}</h3>
        </div>
      </template>
      <div v-if="selectedJob" class="industry-drawer-body">
        <div class="industry-meta-row">
          <span v-for="item in selectedJobMeta" :key="item" class="meta-chip">{{ item }}</span>
        </div>
        <section class="industry-detail-section">
          <h4>相关性命中原因</h4>
          <ul class="message-list">
            <li v-for="reason in selectedJob.relevance_reasons || ['暂无相关性命中说明']" :key="reason">{{ reason }}</li>
          </ul>
        </section>
        <section class="industry-detail-section">
          <h4>技能证据</h4>
          <div v-if="(selectedJob.skill_evidence || []).length" class="industry-evidence-list">
            <article v-for="(item, index) in selectedJob.skill_evidence" :key="`${item.name}-${index}`" class="industry-evidence-card">
              <strong>{{ item.name || "技能" }}</strong>
              <p>{{ item.evidence || "暂无证据" }}</p>
            </article>
          </div>
          <p v-else class="muted">暂无技能证据</p>
        </section>
        <section class="industry-detail-section">
          <h4>任职要求</h4>
          <p class="industry-detail-text">{{ selectedJob.requirements || "暂无任职要求摘要" }}</p>
        </section>
        <section class="industry-detail-section">
          <h4>职位描述</h4>
          <p class="industry-detail-text pre-wrap">{{ selectedJob.description || "暂无职位描述" }}</p>
        </section>
      </div>
    </el-drawer>
  </section>
</template>

<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, reactive, ref, watch } from "vue";
import MetricStatCard from "../../../components/ui/MetricStatCard.vue";
import { type IndustryChartRow, type IndustryJob, type IndustryResult } from "../../../api/studentTwin";
import { init, type ECharts } from "../../../lib/echarts";

const props = defineProps<{
  result: IndustryResult;
  jobs: IndustryJob[];
  searchTerms: string[];
  isRunning: boolean;
}>();

defineEmits<{
  (event: "download"): void;
}>();

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
    { label: "职位总数", value: metrics?.jobs_total ?? 0, description: "最终保留并展示的职位数量。", tone: "brand" as const },
    { label: "已分析职位", value: metrics?.jobs_analyzed ?? 0, description: "完成结构化提取的职位数量。", tone: "success" as const },
    { label: "技能总数", value: metrics?.skills_total ?? 0, description: "本轮识别出的技能标签数量。", tone: "warning" as const },
    { label: "数据源数", value: metrics?.sources_total ?? 0, description: "参与本次分析的数据源数量。", tone: "default" as const },
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
    job.salary || "面议",
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
    const title = job.title || "未知岗位";
    jobCounts.set(title, (jobCounts.get(title) || 0) + 1);
    (job.skills || []).forEach((skill) => {
      const key = `${title}__${skill}`;
      pairCounts.set(key, (pairCounts.get(key) || 0) + 1);
    });
  });

  const visibleJobs = [...jobCounts.entries()].sort((a, b) => b[1] - a[1]).slice(0, topJobs).map(([name]) => name);
  const visibleSkillCounts = new Map<string, number>();
  jobItems.forEach((job) => {
    const title = job.title || "未知岗位";
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
