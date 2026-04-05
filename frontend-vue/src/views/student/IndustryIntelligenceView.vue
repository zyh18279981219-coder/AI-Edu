<template>
  <div class="industry-page">
    <PageHero
      eyebrow="Career Insight"
      title="行业情报与岗位技能分析"
      description="在网页中完成岗位抓取、相关性过滤、技能提取、图表分析和结果复用，帮助学生更快理解目标岗位要求。"
      :badges="heroBadges"
      tone="industry"
    />

    <div class="industry-shell">
      <aside class="industry-sidebar">
        <section class="card-panel industry-status-card">
          <div class="section-head">
            <h2>模块状态</h2>
            <span class="industry-status-dot" :class="{ ok: statusData?.ok, error: statusData && !statusData.ok }"></span>
          </div>
          <ul class="message-list">
            <li v-for="message in statusMessages" :key="message">{{ message }}</li>
          </ul>
        </section>

        <form class="card-panel industry-form-card" @submit.prevent="handleAnalyze">
          <div class="section-head">
            <h2>分析参数</h2>
          </div>

          <label class="field">
            <span>搜索关键字</span>
            <el-input v-model="form.keyword" placeholder="例如：大数据分析、商业分析、AI 产品经理" clearable />
          </label>

          <div class="field-grid two-col">
            <label class="field">
              <span>国家 / 地区</span>
              <el-select v-model="form.country" :disabled="form.include_global" placeholder="请选择国家">
                <el-option v-for="country in countries" :key="country" :label="country" :value="country" />
              </el-select>
            </label>
            <label class="field">
              <span>城市</span>
              <el-select v-model="form.city" :disabled="form.include_global" placeholder="请选择城市">
                <el-option v-for="city in availableCities" :key="city" :label="city" :value="city" />
              </el-select>
            </label>
          </div>

          <label class="field toggle-field">
            <span>组合抓取</span>
            <label class="toggle-inline">
              <el-switch v-model="form.include_global" />
              <span>国内 + 海外并行提取</span>
            </label>
            <small>开启后会同时抓取中国、美国、新加坡，并统一进入后续分析。</small>
          </label>

          <label class="field">
            <span>每个数据源职位数</span>
            <el-input-number v-model="form.job_limit" :min="1" :max="50" />
          </label>

          <label class="field">
            <span>相关性过滤强度 <strong>{{ form.relevance_threshold }}</strong></span>
            <el-slider v-model="form.relevance_threshold" :min="0" :max="12" />
          </label>

          <div class="field">
            <span>数据源</span>
            <el-checkbox-group v-model="form.sources" class="industry-source-list">
              <el-checkbox v-for="source in sources" :key="source" :label="source" class="industry-source-item">
                {{ source }}
              </el-checkbox>
            </el-checkbox-group>
          </div>

          <div class="industry-actions">
            <el-button class="full-width" type="primary" size="large" native-type="submit" :loading="isSubmitting">
              {{ isRunning ? "任务运行中..." : "采集并分析" }}
            </el-button>
            <el-button class="full-width" type="danger" plain :disabled="!activeTaskId || !isRunning" @click="handleCancel">
              终止任务
            </el-button>
            <el-button class="full-width" plain :disabled="!jobs.length || isRunning" @click="handleReanalyze">
              重新提取技能
            </el-button>
          </div>
        </form>
      </aside>

      <section class="industry-main">
        <section v-if="runtimeVisible" class="card-panel industry-runtime-card">
          <div class="section-head">
            <div>
              <p class="eyebrow">Processing</p>
              <h2>运行进度</h2>
            </div>
            <span class="runtime-badge" :class="runtimeBadgeClass">{{ runtimeBadgeText }}</span>
          </div>
          <p class="hero-desc">{{ runtimeText }}</p>
          <div class="industry-step-grid">
            <article v-for="step in runtimeSteps" :key="step.key" class="industry-step-item" :class="step.state">
              <div class="industry-step-index">{{ step.index }}</div>
              <div>
                <strong>{{ step.title }}</strong>
                <p>{{ step.desc }}</p>
              </div>
            </article>
          </div>
        </section>

        <section v-if="!result" class="card-panel industry-empty-card">
          <div class="section-head">
            <h2>分析结果</h2>
          </div>
          <p class="hero-desc">分析开始后，这里会展示技能热力图、岗位分布、经验学历要求和职位详情。</p>
        </section>

        <IndustryResultsBoard
          v-else
          :result="result"
          :jobs="jobs"
          :search-terms="searchTerms"
          :is-running="isRunning"
          @download="downloadResult"
        />
      </section>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, defineAsyncComponent, onBeforeUnmount, onMounted, reactive, ref, watch } from "vue";
import PageHero from "../../components/ui/PageHero.vue";
import {
  cancelIndustryTask,
  fetchCurrentIndustryTask,
  fetchIndustryStatus,
  fetchIndustryTask,
  reanalyzeIndustryJobs,
  startIndustryAnalysis,
  type IndustryResult,
  type IndustryStatusResponse,
  type IndustryTask,
} from "../../api/studentTwin";

type StepState = "pending" | "active" | "done" | "failed";

const IndustryResultsBoard = defineAsyncComponent(() => import("./components/IndustryResultsBoard.vue"));

const TASK_STEPS = [
  { key: "queued", title: "准备任务", desc: "校验参数、检查模型和登录状态。", step: 0 },
  { key: "collecting", title: "抓取职位", desc: "连接招聘数据源并收集原始职位。", step: 1 },
  { key: "filtering", title: "相关筛选", desc: "按关键词相关性过滤，并继续扩大抓取范围。", step: 2 },
  { key: "analyzing", title: "技能解析", desc: "提取技能、经验、学历和任职要求。", step: 3 },
  { key: "rendering", title: "结果整理", desc: "生成图表、统计摘要和职位明细。", step: 4 },
  { key: "completed", title: "完成输出", desc: "结果已返回到页面，可继续查看或下载。", step: 5 },
];

const statusData = ref<IndustryStatusResponse | null>(null);
const result = ref<IndustryResult | null>(null);
const currentTask = ref<IndustryTask | null>(null);
const activeTaskId = ref<string | null>(null);
const isSubmitting = ref(false);

const form = reactive({
  keyword: "大数据分析",
  country: "中国",
  city: "全国",
  include_global: false,
  job_limit: 20,
  relevance_threshold: 5,
  sources: ["linkedin", "indeed"],
  fetch_desc: true,
});

let pollTimer: number | null = null;

const countries = computed(() => statusData.value?.countries ?? ["中国"]);
const sources = computed(() => statusData.value?.sources ?? ["linkedin", "indeed"]);
const availableCities = computed(() => {
  const cityMap = statusData.value?.city_map ?? { 中国: ["全国"] };
  return cityMap[form.country] ?? ["全国"];
});
const statusMessages = computed(() => statusData.value?.messages ?? ["正在检查行业情报模块状态..."]);
const jobs = computed(() => result.value?.jobs ?? []);
const searchTerms = computed(() => result.value?.relevance_summary?.search_terms ?? []);
const runtimeVisible = computed(() => {
  const status = currentTask.value?.status;
  return Boolean(currentTask.value && status !== "completed" && status !== "cancelled");
});
const isRunning = computed(() => {
  const status = currentTask.value?.status;
  return Boolean(status && !["completed", "failed", "cancelled"].includes(status));
});
const runtimeText = computed(() => currentTask.value?.message ?? "填写参数后即可开始分析。");
const runtimeBadgeText = computed(() => {
  const status = currentTask.value?.status;
  if (status === "completed") return "已完成";
  if (status === "failed" || status === "cancelled") return "失败";
  if (status) return "运行中";
  return "等待中";
});
const runtimeBadgeClass = computed(() => {
  const status = currentTask.value?.status;
  if (status === "completed") return "success";
  if (status === "failed" || status === "cancelled") return "error";
  if (status) return "running";
  return "idle";
});
const runtimeSteps = computed(() => {
  const status = currentTask.value?.status ?? "idle";
  const stepNumber = getStepNumber(currentTask.value);
  return TASK_STEPS.map((item, index) => ({
    ...item,
    index: index + 1,
    state: resolveStepState(item.step, stepNumber, status),
    desc: item.step === stepNumber && currentTask.value?.message ? currentTask.value.message : item.desc,
  }));
});
const heroBadges = ["严格阈值筛选", "支持任务恢复", "支持终止任务"];

watch(
  () => form.country,
  () => {
    if (!availableCities.value.includes(form.city)) {
      form.city = availableCities.value[0] ?? "全国";
    }
  },
);

watch(
  () => form.include_global,
  (enabled) => {
    if (enabled) {
      form.country = "中国";
      form.city = "全国";
    }
  },
);

async function loadStatus() {
  statusData.value = await fetchIndustryStatus();
  form.sources = [...(statusData.value.sources ?? ["linkedin", "indeed"])];
  if (!availableCities.value.includes(form.city)) {
    form.city = availableCities.value[0] ?? "全国";
  }
}

async function restoreLatestState() {
  const task = await fetchCurrentIndustryTask();
  if (!task) return;
  currentTask.value = task;
  activeTaskId.value = task.task_id;

  if (task.status === "completed" && task.result) {
    result.value = task.result;
    currentTask.value = null;
    activeTaskId.value = null;
    return;
  }

  if (!["failed", "cancelled"].includes(task.status)) startPolling();
}

async function handleAnalyze() {
  isSubmitting.value = true;
  try {
    const response = await startIndustryAnalysis({
      keyword: form.keyword,
      country: form.include_global ? "中国" : form.country,
      city: form.include_global ? "全国" : form.city,
      include_global: form.include_global,
      job_limit: form.job_limit,
      relevance_threshold: form.relevance_threshold,
      sources: form.sources,
      fetch_desc: true,
    });
    activeTaskId.value = response.task_id;
    result.value = null;
    currentTask.value = { task_id: response.task_id, task_type: "analyze", status: "queued", message: "正在创建分析任务..." };
    await fetchTaskStatus();
    startPolling();
  } catch (error) {
    currentTask.value = {
      task_id: "local-error",
      task_type: "analyze",
      status: "failed",
      message: toErrorMessage(error, "任务创建失败"),
      error: toErrorMessage(error, "任务创建失败"),
    };
  } finally {
    isSubmitting.value = false;
  }
}

async function handleReanalyze() {
  if (!jobs.value.length) return;
  isSubmitting.value = true;
  try {
    const response = await reanalyzeIndustryJobs(jobs.value);
    activeTaskId.value = response.task_id;
    currentTask.value = { task_id: response.task_id, task_type: "reanalyze", status: "queued", message: "正在创建重新提取任务..." };
    await fetchTaskStatus();
    startPolling();
  } catch (error) {
    currentTask.value = {
      task_id: "local-error",
      task_type: "reanalyze",
      status: "failed",
      message: toErrorMessage(error, "重新提取失败"),
      error: toErrorMessage(error, "重新提取失败"),
    };
  } finally {
    isSubmitting.value = false;
  }
}

async function handleCancel() {
  if (!activeTaskId.value) return;
  try {
    await cancelIndustryTask(activeTaskId.value);
    stopPolling();
    currentTask.value = null;
    activeTaskId.value = null;
  } catch (error) {
    currentTask.value = {
      task_id: activeTaskId.value ?? "unknown-task",
      task_type: currentTask.value?.task_type ?? "analyze",
      status: "failed",
      message: toErrorMessage(error, "终止任务失败"),
      error: toErrorMessage(error, "终止任务失败"),
    };
  }
}

async function fetchTaskStatus() {
  if (!activeTaskId.value) return;
  try {
    const task = await fetchIndustryTask(activeTaskId.value);
    currentTask.value = task;
    if (task.status === "completed" && task.result) {
      result.value = task.result;
      stopPolling();
      currentTask.value = null;
      activeTaskId.value = null;
      return;
    }
    if (task.status === "failed" || task.status === "cancelled") {
      stopPolling();
      activeTaskId.value = null;
    }
  } catch (error) {
    stopPolling();
    currentTask.value = {
      task_id: activeTaskId.value ?? "unknown-task",
      task_type: currentTask.value?.task_type ?? "analyze",
      status: "failed",
      message: toErrorMessage(error, "无法获取任务状态"),
      error: toErrorMessage(error, "无法获取任务状态"),
    };
    activeTaskId.value = null;
  }
}

function startPolling() {
  stopPolling();
  pollTimer = window.setInterval(() => {
    void fetchTaskStatus();
  }, 2000);
}

function stopPolling() {
  if (pollTimer) {
    window.clearInterval(pollTimer);
    pollTimer = null;
  }
}

function downloadResult() {
  if (!result.value) return;
  const blob = new Blob([JSON.stringify(result.value.jobs, null, 2)], { type: "application/json" });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = "industry_jobs.json";
  link.click();
  URL.revokeObjectURL(url);
}

function resolveStepState(step: number, currentStep: number, status: string): StepState {
  if ((status === "failed" || status === "cancelled") && step === currentStep) return "failed";
  if (status === "completed") return "done";
  if (step < currentStep) return "done";
  if (step === currentStep && status !== "idle") return "active";
  return "pending";
}

function getStepNumber(task: IndustryTask | null) {
  if (!task) return 0;
  if (typeof task.meta?.step === "number") return task.meta.step;
  const matched = TASK_STEPS.find((item) => item.key === task.status);
  return matched ? matched.step : 0;
}

function toErrorMessage(error: unknown, fallback: string) {
  if (typeof error === "object" && error && "response" in error) {
    const maybeResponse = error as { response?: { data?: { detail?: string } }; message?: string };
    return maybeResponse.response?.data?.detail || maybeResponse.message || fallback;
  }
  return error instanceof Error ? error.message : fallback;
}

onMounted(async () => {
  await loadStatus();
  await restoreLatestState();
});

onBeforeUnmount(() => {
  stopPolling();
});
</script>
