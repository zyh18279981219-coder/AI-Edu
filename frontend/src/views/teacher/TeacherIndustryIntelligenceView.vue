<template>
  <div class="industry-page">
    <!-- 页面头部 -->
    <div class="student-industry-v2-header">
      <div>
        <h1>行业资讯</h1>
        <p class="student-industry-v2-desc">职位搜索与行业趋势分析</p>
      </div>
    </div>

    <div class="industry-shell">
      <aside class="industry-sidebar">
        <form class="student-industry-v2-form-card" @submit.prevent="handleAnalyze">
          <div class="student-industry-v2-form-header">
            <h2>{{ $t('student.industryIntelligence.analysisParameters') }}</h2>
            <span class="muted">配置分析参数</span>
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
              <el-checkbox v-for="source in sources" :key="source" :value="source" class="industry-source-item">
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
        <section v-if="runtimeVisible" class="student-industry-v2-runtime-card">
          <div class="student-industry-v2-runtime-header">
            <div>
              <div class="student-industry-v2-runtime-kicker">处理进度</div>
              <h2>{{ $t('student.industryIntelligence.runningProgress') }}</h2>
            </div>
            <span class="student-industry-v2-runtime-badge" :class="runtimeBadgeClass">{{ runtimeBadgeText }}</span>
          </div>
          <p class="student-industry-v2-runtime-desc">{{ runtimeText }}</p>
          <div class="student-industry-v2-step-grid">
            <article v-for="step in runtimeSteps" :key="step.key" class="student-industry-v2-step-item" :class="step.state">
              <div class="student-industry-v2-step-icon">
                <span v-if="step.state === 'done'">✓</span>
                <span v-else-if="step.state === 'active'">●</span>
                <span v-else-if="step.state === 'failed'">×</span>
                <span v-else>{{ step.index }}</span>
              </div>
              <div class="student-industry-v2-step-content">
                <strong>{{ step.title }}</strong>
                <p>{{ step.desc }}</p>
              </div>
            </article>
          </div>
        </section>

        <IndustryResultsBoard
          v-if="result"
          :result="result"
          :jobs="jobs"
          :search-terms="searchTerms"
          :is-running="isRunning"
          @download="downloadResult"
        />

        <section v-if="result" class="industry-course-import-card">
          <div class="section-head">
            <div>
              <p class="eyebrow">Course Twin Import</p>
              <h3>导入课程数字孪生</h3>
            </div>
            <RouterLink class="ghost-btn small" :to="courseTwinReviewTarget">去课程孪生审核</RouterLink>
          </div>
          <div class="industry-course-import-grid">
            <label class="field">
              <span>目标课程</span>
              <el-select v-model="courseImportForm.course_id" placeholder="选择课程底座" :disabled="!courseOptions.length">
                <el-option
                  v-for="course in courseOptions"
                  :key="course.course_id"
                  :label="`${course.course_name}（${course.lifecycle_status}）`"
                  :value="course.course_id"
                />
              </el-select>
            </label>
            <label class="field">
              <span>岗位方向</span>
              <el-input v-model.trim="courseImportForm.position_name" placeholder="如：大数据工程师" clearable />
            </label>
            <label class="field">
              <span>方向类型</span>
              <el-select v-model="courseImportForm.position_type">
                <el-option label="主要目标岗位" value="primary" />
                <el-option label="关联岗位" value="related" />
              </el-select>
            </label>
            <label class="field">
              <span>导入数量</span>
              <el-input-number v-model="courseImportForm.ability_limit" :min="3" :max="30" />
            </label>
            <label class="field toggle-field">
              <span>映射候选</span>
              <label class="toggle-inline">
                <el-switch v-model="courseImportForm.generate_mapping_candidates" />
                <span>导入后生成能力-叶子知识点草稿候选</span>
              </label>
              <small>仅生成待审核候选，不自动发布或影响学生端。</small>
            </label>
          </div>
          <div class="industry-course-skill-preview">
            <span v-for="skill in courseImportAbilities.slice(0, courseImportForm.ability_limit)" :key="skill.ability_name" class="skill-chip">
              {{ skill.ability_name }}
            </span>
            <span v-if="!courseImportAbilities.length" class="muted">当前分析结果中暂无可导入能力候选</span>
          </div>
          <div class="industry-course-import-actions">
            <el-button type="primary" :loading="isImportingCourseTwin" :disabled="!canImportToCourseTwin" @click="handleImportToCourseTwin">
              导入岗位与能力候选
            </el-button>
            <RouterLink v-if="courseImportNotice" class="ghost-btn small" :to="courseTwinReviewTarget">
              去审核映射
            </RouterLink>
            <span v-if="courseImportNotice" class="course-import-notice">{{ courseImportNotice }}</span>
          </div>
        </section>
      </section>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, defineAsyncComponent, onBeforeUnmount, onMounted, reactive, ref, watch } from "vue";
import { RouterLink } from "vue-router";
import {
  cancelIndustryTask,
  fetchCurrentIndustryTask,
  fetchIndustryStatus,
  fetchIndustryTask,
  reanalyzeIndustryJobs,
  startIndustryAnalysis,
} from "../../api/industry";
import {
  fetchCourseDigitalTwinCourses,
  importCourseDigitalTwinAbilities,
  saveCourseDigitalTwinPosition,
} from "../../api/teacher";
import {IndustryJob, IndustryResult, IndustryStatusResponse, IndustryTask} from "../../types/industry";
import type { CourseDigitalTwinSummary } from "../../types/teacher";
import i18n from "../../locale";

type StepState = "pending" | "active" | "done" | "failed";

const {t}=i18n.global;

const IndustryResultsBoard = defineAsyncComponent(() => import("../student/components/IndustryResultsBoard.vue"));

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
const isImportingCourseTwin = ref(false);
const courseOptions = ref<CourseDigitalTwinSummary[]>([]);
const courseImportNotice = ref("");

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

const courseImportForm = reactive({
  course_id: "",
  position_name: "",
  position_type: "primary",
  ability_limit: 12,
  generate_mapping_candidates: true,
});

let pollTimer: number | null = null;

const countries = computed(() => statusData.value?.countries ?? ["中国"]);
const sources = computed(() => statusData.value?.sources ?? ["linkedin", "indeed"]);
const availableCities = computed(() => {
  const cityMap = statusData.value?.city_map ?? { "中国": ["全国"] };
  return cityMap[form.country] ?? ["全国"];
});
const statusMessages = computed(() => statusData.value?.messages ?? [t('student.industryIntelligence.checkingModuleStatus')]);
const jobs = computed(() => result.value?.jobs ?? []);
const searchTerms = computed(() => result.value?.relevance_summary?.search_terms ?? []);
const courseImportAbilities = computed(() => extractAbilityCandidates(jobs.value, result.value));
const canImportToCourseTwin = computed(() =>
  Boolean(courseImportForm.course_id && courseImportForm.position_name.trim() && courseImportAbilities.value.length),
);
const courseTwinReviewTarget = computed(() => ({
  path: "/teacher/course-twin",
  query: courseImportForm.course_id ? { course_id: courseImportForm.course_id, focus: "ability-mapping" } : { focus: "ability-mapping" },
}));
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

watch(
  () => result.value,
  () => {
    if (!courseImportForm.position_name.trim()) {
      courseImportForm.position_name = inferPositionName(jobs.value, form.keyword);
    }
    courseImportNotice.value = "";
  },
);

async function loadStatus() {
  statusData.value = await fetchIndustryStatus();
  form.sources = [...(statusData.value.sources ?? ["linkedin", "indeed"])];
  if (!availableCities.value.includes(form.city)) {
    form.city = availableCities.value[0] ?? "全国";
  }
}

async function loadCourses() {
  const data = await fetchCourseDigitalTwinCourses();
  courseOptions.value = data.courses || [];
  if (!courseImportForm.course_id && courseOptions.value.length) {
    courseImportForm.course_id = courseOptions.value[0].course_id;
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
      courseImportForm.position_name = inferPositionName(task.result.jobs || [], form.keyword);
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

function inferPositionName(jobItems: IndustryJob[], fallback: string) {
  const counter = new Map<string, number>();
  jobItems.forEach((job) => {
    const title = String(job.title || "").trim();
    if (title) counter.set(title, (counter.get(title) || 0) + 1);
  });
  const [topTitle] = [...counter.entries()].sort((a, b) => b[1] - a[1])[0] || [];
  return topTitle || fallback || "行业岗位方向";
}

function extractAbilityCandidates(jobItems: IndustryJob[], industryResult: IndustryResult | null) {
  const evidenceBySkill = new Map<string, string>();
  const countBySkill = new Map<string, number>();
  jobItems.forEach((job) => {
    (job.skills || []).forEach((skill) => {
      const clean = String(skill || "").trim();
      if (!clean) return;
      countBySkill.set(clean, (countBySkill.get(clean) || 0) + 1);
    });
    (job.skill_evidence || []).forEach((item) => {
      const name = String(item.name || "").trim();
      if (name && item.evidence && !evidenceBySkill.has(name)) {
        evidenceBySkill.set(name, item.evidence);
      }
    });
  });
  (industryResult?.charts?.skill_ranking || []).forEach((item) => {
    const clean = String(item.name || "").trim();
    if (clean && !countBySkill.has(clean)) {
      countBySkill.set(clean, Number(item.value || 1));
    }
  });
  return [...countBySkill.entries()]
    .sort((a, b) => b[1] - a[1])
    .map(([name, count]) => ({
      ability_name: name,
      ability_category: "行业岗位能力",
      demand_level: count >= 5 ? "high" : count >= 2 ? "medium" : "low",
      source_evidence: {
        source: "industry_intelligence",
        job_count: count,
        evidence: evidenceBySkill.get(name) || "",
      },
    }));
}

async function handleImportToCourseTwin() {
  if (!canImportToCourseTwin.value) return;
  isImportingCourseTwin.value = true;
  courseImportNotice.value = "";
  try {
    const positionData = await saveCourseDigitalTwinPosition({
      course_id: courseImportForm.course_id,
      position_name: courseImportForm.position_name,
      position_type: courseImportForm.position_type,
      target_rank: 0,
      source_keyword: form.keyword,
    });
    const positionId = positionData.position.position_id;
    const abilities = courseImportAbilities.value.slice(0, courseImportForm.ability_limit);
    const abilityData = await importCourseDigitalTwinAbilities({
      course_id: courseImportForm.course_id,
      position_id: positionId,
      abilities,
      industry_payload: {
        keyword: form.keyword,
        imported_from: "teacher_industry_intelligence",
        job_count: jobs.value.length,
      },
      generate_mapping_candidates: courseImportForm.generate_mapping_candidates,
      max_candidates_per_ability: 3,
      min_mapping_score: 0.24,
    });
    const generatedMappings = abilityData.mapping_candidate_result?.generated ?? 0;
    const mappingNotice = courseImportForm.generate_mapping_candidates
      ? `，并生成 ${generatedMappings} 条待审核能力映射候选`
      : "";
    courseImportNotice.value = `已导入岗位「${positionData.position.position_name}」和 ${abilityData.import_result?.saved ?? abilities.length} 个能力候选${mappingNotice}，请前往课程数字孪生页审核后再发布。`;
  } catch (error) {
    courseImportNotice.value = toErrorMessage(error, "导入课程数字孪生失败");
  } finally {
    isImportingCourseTwin.value = false;
  }
}

function startPolling() {
  stopPolling();
  let pollInterval = 1500; // 初始轮询间隔 1.5 秒
  let consecutiveNoChange = 0;
  let lastStatus = currentTask.value?.status;
  let lastMessage = currentTask.value?.message;
  
  const poll = async () => {
    await fetchTaskStatus();
    
    // 检测状态是否有变化
    const currentStatus = currentTask.value?.status;
    const currentMessage = currentTask.value?.message;
    
    if (currentStatus === lastStatus && currentMessage === lastMessage) {
      consecutiveNoChange++;
      // 如果连续 3 次没有变化，逐渐增加轮询间隔（最多到 5 秒）
      if (consecutiveNoChange >= 3) {
        pollInterval = Math.min(5000, pollInterval + 500);
      }
    } else {
      // 有变化时重置为快速轮询
      consecutiveNoChange = 0;
      pollInterval = 1500;
    }
    
    lastStatus = currentStatus;
    lastMessage = currentMessage;
    
    // 如果任务还在运行，继续轮询
    if (currentStatus && !["completed", "failed", "cancelled"].includes(currentStatus)) {
      pollTimer = window.setTimeout(poll, pollInterval);
    }
  };
  
  // 立即执行第一次轮询
  void poll();
}

function stopPolling() {
  if (pollTimer) {
    window.clearTimeout(pollTimer); // 使用 clearTimeout 清理轮询定时器
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
  await loadCourses();
  await restoreLatestState();
});

onBeforeUnmount(() => {
  stopPolling();
});
</script>

<style scoped>
.industry-course-import-card {
  display: grid;
  gap: 14px;
  border: 1px solid #dbe4f0;
  border-radius: 16px;
  padding: 18px;
  background: #ffffff;
  box-shadow: 0 4px 12px rgba(15, 23, 42, 0.04);
}

.industry-course-import-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 12px;
}

.industry-course-skill-preview {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  min-height: 32px;
}

.industry-course-import-actions {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
}

.course-import-notice {
  color: #0f766e;
  font-size: 13px;
  font-weight: 700;
}

@media (max-width: 1180px) {
  .industry-course-import-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 640px) {
  .industry-course-import-grid {
    grid-template-columns: 1fr;
  }
}
</style>
