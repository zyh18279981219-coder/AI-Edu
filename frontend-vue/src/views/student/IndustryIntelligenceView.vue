<template>
  <div class="industry-page">
    <PageHero
      eyebrow="Career Insight"
      :title="$t('student.industryIntelligence.industryInformation')"
      :description="$t('student.industryIntelligence.industryInformationDescription')"
      :badges="heroBadges"
      tone="industry"
    />

    <div class="industry-shell">
      <aside class="industry-sidebar">
        <section class="card-panel industry-status-card">
          <div class="section-head">
            <h2>{{ $t('student.industryIntelligence.moduleStatus') }}</h2>
            <span class="industry-status-dot" :class="{ ok: statusData?.ok, error: statusData && !statusData.ok }"></span>
          </div>
          <ul class="message-list">
            <li v-for="message in statusMessages" :key="message">{{ message }}</li>
          </ul>
        </section>

        <form class="card-panel industry-form-card" @submit.prevent="handleAnalyze">
          <div class="section-head">
            <h2>{{ $t('student.industryIntelligence.analysisParameters') }}</h2>
          </div>

          <label class="field">
            <span>{{ $t('student.industryIntelligence.searchKeywords') }}</span>
            <el-input v-model="form.keyword" :placeholder="$t('student.industryIntelligence.searchKeywordsPlaceholder')" clearable />
          </label>

          <div class="field-grid two-col">
            <label class="field">
              <span>{{ $t('student.industryIntelligence.countryOrDistrict') }}</span>
              <el-select v-model="form.country" :disabled="form.include_global" :placeholder="$t('student.industryIntelligence.countryOrDistrictPlaceholder')">
                <el-option v-for="country in countries" :key="country" :label="country" :value="country" />
              </el-select>
            </label>
            <label class="field">
              <span>{{ $t('student.industryIntelligence.city') }}</span>
              <el-select v-model="form.city" :disabled="form.include_global" :placeholder="$t('student.industryIntelligence.cityPlaceholder')">
                <el-option v-for="city in availableCities" :key="city" :label="city" :value="city" />
              </el-select>
            </label>
          </div>

          <label class="field toggle-field">
            <span>{{ $t('student.industryIntelligence.combinedCrawling') }}</span>
            <label class="toggle-inline">
              <el-switch v-model="form.include_global" />
              <span>{{ $t('student.industryIntelligence.combinedCrawlingDescription') }}</span>
            </label>
            <small>{{ $t('student.industryIntelligence.combinedCrawlingDetail') }}</small>
          </label>

          <label class="field">
            <span>{{ $t('student.industryIntelligence.numberOfJobs') }}</span>
            <el-input-number v-model="form.job_limit" :min="1" :max="50" />
          </label>

          <label class="field">
            <span>{{ $t('student.industryIntelligence.relativity') }} <strong>{{ form.relevance_threshold }}</strong></span>
            <el-slider v-model="form.relevance_threshold" :min="0" :max="12" />
          </label>

          <div class="field">
            <span>{{ $t('student.industryIntelligence.dataSource') }}</span>
            <el-checkbox-group v-model="form.sources" class="industry-source-list">
              <el-checkbox v-for="source in sources" :key="source" :label="source" class="industry-source-item">
                {{ source }}
              </el-checkbox>
            </el-checkbox-group>
          </div>

          <div class="industry-actions">
            <el-button class="full-width" type="primary" size="large" native-type="submit" :loading="isSubmitting">
              {{ isRunning ? $t('student.industryIntelligence.running') : $t('student.industryIntelligence.collectAndAnalyze') }}
            </el-button>
            <el-button class="full-width" type="danger" plain :disabled="!activeTaskId || !isRunning" @click="handleCancel">
              {{ $t('student.industryIntelligence.stopWork') }}
            </el-button>
            <el-button class="full-width" plain :disabled="!jobs.length || isRunning" @click="handleReanalyze">
              {{ $t('student.industryIntelligence.recollection') }}
            </el-button>
          </div>
        </form>
      </aside>

      <section class="industry-main">
        <section v-if="runtimeVisible" class="card-panel industry-runtime-card">
          <div class="section-head">
            <div>
              <p class="eyebrow">Processing</p>
              <h2>{{ $t('student.industryIntelligence.runningProgress') }}</h2>
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
            <h2>{{ $t('student.industryIntelligence.analysisResult') }}</h2>
          </div>
          <p class="hero-desc">{{ $t('student.industryIntelligence.analysisResultDescription') }}</p>
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
} from "../../api/industry";
import {IndustryResult, IndustryStatusResponse, IndustryTask} from "../../types/industry";
import i18n from "../../locale";

type StepState = "pending" | "active" | "done" | "failed";

const {t}=i18n.global;

const IndustryResultsBoard = defineAsyncComponent(() => import("./components/IndustryResultsBoard.vue"));

const TASK_STEPS = computed(() => [
  { key: "queued", title: t('student.industryIntelligence.queued'), desc: t('student.industryIntelligence.queuedDescription'), step: 0 },
  { key: "collecting", title: t('student.industryIntelligence.collecting'), desc: t('student.industryIntelligence.collectingDescription'), step: 1 },
  { key: "filtering", title: t('student.industryIntelligence.filtering'), desc: t('student.industryIntelligence.filteringDescription'), step: 2 },
  { key: "analyzing", title: t('student.industryIntelligence.analyzing'), desc: t('student.industryIntelligence.analyzingDescription'), step: 3 },
  { key: "rendering", title: t('student.industryIntelligence.rendering'), desc: t('student.industryIntelligence.renderingDescription'), step: 4 },
  { key: "completed", title: t('student.industryIntelligence.completed'), desc: t('student.industryIntelligence.completedDescription'), step: 5 },
]);

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
const statusMessages = computed(() => statusData.value?.messages ?? [t('student.industryIntelligence.checkingModuleStatus')]);
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
const runtimeText = computed(() => currentTask.value?.message ?? t('student.industryIntelligence.analysisResultDescription'));
const runtimeBadgeText = computed(() => {
  const status = currentTask.value?.status;
  if (status === "completed") return t('student.industryIntelligence.finished');
  if (status === "failed" || status === "cancelled") return t('student.industryIntelligence.failure');
  if (status) return t('student.industryIntelligence.running');
  return t('student.industryIntelligence.waiting');
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
  return TASK_STEPS.value.map((item, index) => ({
    ...item,
    index: index + 1,
    state: resolveStepState(item.step, stepNumber, status),
    desc: item.step === stepNumber && currentTask.value?.message ? currentTask.value.message : item.desc,
  }));
});
const heroBadges = computed(() => [
  t('student.industryIntelligence.strictThresholdFiltering'),
  t('student.industryIntelligence.supportsTaskResumption'),
  t('student.industryIntelligence.supportsTaskTermination')
]);

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
    currentTask.value = { task_id: response.task_id, task_type: "analyze", status: "queued", message: t('student.industryIntelligence.checkingModuleStatus') };
    await fetchTaskStatus();
    startPolling();
  } catch (error) {
    currentTask.value = {
      task_id: "local-error",
      task_type: "analyze",
      status: "failed",
      message: toErrorMessage(error, t('student.industryIntelligence.errorCreatingTask')),
      error: toErrorMessage(error, t('student.industryIntelligence.errorCreatingTask')),
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
    currentTask.value = { task_id: response.task_id, task_type: "reanalyze", status: "queued", message: t('student.industryIntelligence.checkingModuleStatus') };
    await fetchTaskStatus();
    startPolling();
  } catch (error) {
    currentTask.value = {
      task_id: "local-error",
      task_type: "reanalyze",
      status: "failed",
      message: toErrorMessage(error, t('student.industryIntelligence.errorRecollection')),
      error: toErrorMessage(error, t('student.industryIntelligence.errorRecollection')),
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
      message: toErrorMessage(error, t('student.industryIntelligence.errorTerminatingTask')),
      error: toErrorMessage(error, t('student.industryIntelligence.errorTerminatingTask')),
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
      message: toErrorMessage(error, t('student.industryIntelligence.errorGettingTaskStatus')),
      error: toErrorMessage(error, t('student.industryIntelligence.errorGettingTaskStatus')),
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
  const matched = TASK_STEPS.value.find((item) => item.key === task.status);
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
