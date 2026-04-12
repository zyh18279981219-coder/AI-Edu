<template>
  <div class="learning-shell">
    <PageHero
        eyebrow="My Learning"
        :title="greetingTitle"
        :description="greetingDesc"
        :badges="learningHeroBadges"
        tone="learning"
    >
      <template #actions>
        <el-button type="primary" size="large" round @click="activeTab = 'create'">
          {{$t('student.myLearning.createNewPlan')}}
        </el-button>
      </template>
    </PageHero>

    <section class="metric-grid learning-metric-grid">
      <MetricStatCard :label="$t('student.myLearning.learningPlan')" :value="cleanedPlans.length" :description="$t('student.myLearning.learningPlanDescription')"
                      tone="brand"/>
      <MetricStatCard :label="$t('student.myLearning.pathNode')" :value="pathNodes.length" :description="$t('student.myLearning.pathNodeDescription')"
                      tone="warning"/>
      <MetricStatCard :label="$t('student.myLearning.optionalLanguage')" :value="languages.length" :description="$t('student.myLearning.optionalLanguageDescription')"/>
      <MetricStatCard :label="$t('student.myLearning.plansThisMonth')" :value="plansThisMonth" :description="$t('student.myLearning.plansThisMonthDescription')"
                      tone="success"/>
    </section>

    <section class="learning-grid">
      <aside class="learning-sidebar">
        <div class="card-panel sidebar-card">
          <div class="section-head">
            <h2>今日学习目标</h2>
          </div>
          <ul class="goal-list">
            <li>回顾当前课程章节与知识点位置，确认今天的学习范围。</li>
            <li>查看个性化学习路径，优先处理薄弱知识点建议。</li>
            <li>生成或更新本周学习计划，保证每天都有明确任务。</li>
          </ul>
        </div>

        <div class="card-panel sidebar-card">
          <div class="section-head">
            <h2>{{ $t('student.myLearning.calendar') }}</h2>
            <span class="muted">{{ calendarTitle }}</span>
          </div>
          <div class="calendar-grid">
            <div class="calendar-weekday" v-for="weekday in weekdays" :key="weekday">
              {{ weekday }}
            </div>
            <div
                v-for="cell in calendarCells"
                :key="`${cell.dateKey}-${cell.day}-${cell.currentMonth}`"
                class="calendar-cell"
                :class="{
                dimmed: !cell.currentMonth,
                today: cell.isToday,
                planned: cell.hasPlan,
                deadline: cell.hasDeadline,
              }"
            >
              {{ cell.day }}
            </div>
          </div>
          <p class="calendar-summary">{{ $t('student.myLearning.calendarPlans', { plansThisMonth, total: cleanedPlans.length }) }}</p>
        </div>
      </aside>

      <div class="learning-main">
        <SegmentedTabs v-model="activeTab" :tabs="tabOptions"/>

        <section v-if="activeTab === 'plans'" class="card-panel tab-panel learning-panel">
          <div class="section-head">
            <h2>{{ $t('student.myLearning.learningPlanList') }}</h2>
            <span class="muted">{{ $t('student.myLearning.reverseDisplayedLearningPlans') }}</span>
          </div>

          <div v-if="plansLoading" class="state-card">{{ $t('student.myLearning.loadingLearningPlans') }}</div>
          <div v-else-if="plansError" class="state-card error-state">{{ plansError }}</div>
          <div v-else-if="selectedPlan" class="plan-detail">
            <div class="plan-detail-header">
              <div>
                <div class="list-title">{{ selectedPlan.data[0]?.topic || $t('student.myLearning.learningPlan') }}</div>
                <div class="list-meta">
                  {{ selectedPlan.data[0]?.date || $t('student.myLearning.noDate') }}
                  <span v-if="selectedPlan.data[0]?.priority"> · {{ getLearningType(selectedPlan.data[0]?.priority) }}</span>
                </div>
              </div>
              <button type="button" class="ghost-btn" @click="selectedPlanIndex = null">{{ $t('student.myLearning.backToList') }}</button>
            </div>
            <div
                class="plan-entry"
                v-for="entry in selectedPlan.data"
                :key="`${selectedPlan.filename}-${entry.date}-${entry.topic}`"
            >
              <h3>{{ entry.date }} · {{ getLearningType(entry.topic) }}</h3>
              <p class="muted">{{ $t('student.myLearning.learningType') }}：{{ getLearningType(entry.priority) }}</p>
              <p v-if="entry.deadline" class="deadline-text">{{ $t('student.myLearning.expirationDate') }}：{{ entry.deadline }}</p>
              <ul class="material-list">
                <li v-for="material in normalizeMaterials(entry.materials)" :key="material">{{ material }}</li>
              </ul>
            </div>
          </div>
          <div v-else-if="cleanedPlans.length === 0" class="state-card">{{ $t('student.myLearning.noLearningPlans') }}</div>
          <div v-else class="stack-list">
            <button
                v-for="(plan, index) in cleanedPlans"
                :key="plan.filename"
                type="button"
                class="list-card learning-plan-card"
                @click="selectedPlanIndex = index"
            >
              <div class="plan-card-head">
                <span class="pill">{{ plan.data[0]?.date || planDate(plan.filename) }}</span>
                <span class="muted">{{ getLearningType(plan.data[0]?.priority) || $t('student.myLearning.noDate') }}</span>
              </div>
              <div class="list-title">{{ plan.data[0]?.topic || $t('student.myLearning.learningPlan') }}</div>
              <div class="list-meta">
                {{ $t('student.myLearning.numberOfPlans', { total: plan.data.length }) }}
                <span v-if="plan.data[0]?.deadline"> · {{ $t('student.myLearning.expirationDate') }} {{ plan.data[0]?.deadline }}</span>
              </div>
            </button>
          </div>
        </section>

        <section v-else-if="activeTab === 'path'" class="card-panel tab-panel learning-panel">
          <div class="section-head">
            <h2>{{ $t('student.myLearning.personalizedLearningPaths') }}</h2>
            <button type="button" class="path-action-btn" @click="handleReplan" :disabled="pathRefreshing">
              {{ pathRefreshing ? $t('student.myLearning.underPlanning') : $t('student.myLearning.replanning') }}
            </button>
          </div>

          <div v-if="pathLoading" class="state-card">{{ $t('student.myLearning.loadingLearningPaths') }}</div>
          <div v-else-if="pathError" class="state-card error-state">{{ pathError }}</div>
          <div v-else-if="pathData?.status === 'error'" class="state-card error-state">
            {{ pathData.message || $t('student.myLearning.noLearningPaths') }}
          </div>
          <div v-else-if="pathData?.status === 'no_weak_nodes'" class="state-card">
            {{ $t('student.myLearning.noWeakNodes') }}
          </div>
          <div v-else-if="pathNodes.length === 0" class="state-card">{{ $t('student.myLearning.noLearningData') }}</div>
          <div v-else class="path-panel">
            <div v-if="pathData?.llm_advice" class="advice-box">
              <div class="list-title">{{ $t('student.myLearning.personalizedLearningAdvices') }}</div>
              <p>{{ pathData.llm_advice }}</p>
            </div>
            <div v-if="pathData?.llm_order_reason" class="order-tip">
              {{ pathData.llm_order_reason }}
            </div>
            <div class="path-grid">
              <article class="path-card-vue" v-for="node in pathNodes" :key="node.node_id">
                <div class="path-card-head">
                  <div class="list-title">{{ $t('student.myLearning.learningPathPriority', { level: pathPriority(node), name: node.node_id }) }}</div>
                  <span class="muted">{{ $t('student.myLearning.learningMastery', { value: node.mastery_score }) }}</span>
                </div>
                <div class="mastery-track">
                  <span class="mastery-fill" :style="{ width: `${clampScore(node.mastery_score)}%` }"></span>
                </div>
                <div v-if="node.resources?.length" class="path-resource-list">
                  <a
                      v-for="resource in node.resources"
                      :key="resource.url"
                      :href="resource.url"
                      target="_blank"
                      rel="noopener noreferrer"
                  >
                    {{ cleanResourceLabel(resource.title || resource.url) }}
                  </a>
                </div>
              </article>
            </div>
          </div>
        </section>

        <section v-else class="card-panel tab-panel learning-panel">
          <div class="section-head">
            <h2>{{ $t('student.myLearning.createNewLearningPlan') }}</h2>
            <span class="muted">{{ $t('student.myLearning.createNewLearningPlanDescription') }}</span>
          </div>

          <form class="plan-form" @submit.prevent="submitPlan">
            <label>
              {{ $t('student.myLearning.languages') }}
              <el-select v-model="planForm.lang_choice" :placeholder="$t('student.myLearning.languagesPlaceholder')">
                <el-option v-for="lang in languages" :key="lang" :label="lang" :value="lang"/>
              </el-select>
            </label>
            <label>
              {{ $t('student.myLearning.name') }}
              <el-input v-model="planForm.name" :placeholder="$t('student.myLearning.namePlaceholder')"/>
            </label>
            <label class="wide">
              {{ $t('student.myLearning.goals') }}
              <el-input
                  v-model.trim="planForm.goals"
                  type="textarea"
                  :rows="5"
                  :placeholder="$t('student.myLearning.goalsPlaceholder')"
              />
            </label>
            <label>
              {{ $t('student.myLearning.learningType') }}
              <el-select v-model="planForm.priority" :placeholder="$t('student.myLearning.learningTypePlaceholder')">
                <el-option :label="$t('student.myLearning.basicKnowledge')" value="基础知识"/>
                <el-option :label="$t('student.myLearning.practicalApplication')" value="实践应用"/>
                <el-option :label="$t('student.myLearning.theoreticalAnalysis')" value="原理分析"/>
                <el-option :label="$t('student.myLearning.extendedInnovation')" value="拓展创新"/>
              </el-select>
            </label>
            <label>
              {{ $t('student.myLearning.deadline') }}
              <el-select v-model="planForm.deadline_days" :placeholder="$t('student.myLearning.deadlinePlaceholder')">
                <el-option :value="1" :label="$t('student.myLearning.oneDay')"/>
                <el-option :value="3" :label="$t('student.myLearning.threeDays')"/>
                <el-option :value="7" :label="$t('student.myLearning.oneWeek')"/>
                <el-option :value="14" :label="$t('student.myLearning.twoWeeks')"/>
                <el-option :value="30" :label="$t('student.myLearning.oneMonth')"/>
              </el-select>
            </label>

            <p v-if="createError" class="form-error">{{ createError }}</p>

            <el-button type="primary" size="large" class="full-width" native-type="submit" :loading="creatingPlan">
              {{ creatingPlan ? $t('student.myLearning.underCreating') : $t('student.myLearning.createLearningPlan') }}
            </el-button>
          </form>

          <div v-if="createdPlan" class="created-plan">
            <div class="section-head">
              <h2>{{ createdPlan.message }}</h2>
              <el-button plain @click="reloadPlans">{{ $t('student.myLearning.refreshLearningPlanList') }}</el-button>
            </div>
            <div class="plan-entry" v-for="entry in createdPlan.plan" :key="`${entry.date}-${entry.topic}`">
              <h3>{{ entry.date }} · {{ entry.topic }}</h3>
              <p class="muted">{{ $t('student.myLearning.learningType') }}：{{ entry.priority }}</p>
              <p v-if="entry.deadline" class="deadline-text">{{ $t('student.myLearning.expirationDate') }}：{{ entry.deadline }}</p>
              <ul class="material-list">
                <li v-for="material in normalizeMaterials(entry.materials)" :key="material">{{ material }}</li>
              </ul>
            </div>
          </div>
        </section>
      </div>
    </section>
  </div>
</template>

<script setup lang="ts">
import {computed, onMounted, reactive, ref, watch} from "vue";
import MetricStatCard from "../../components/ui/MetricStatCard.vue";
import PageHero from "../../components/ui/PageHero.vue";
import SegmentedTabs from "../../components/ui/SegmentedTabs.vue";
import {
  fetchLanguages,
} from "../../api/client";
import {
  type LearningPathNode,
  type LearningPathResponse,
  type LearningPlanEntry,
  type LearningPlanFile, TabKey,
} from "../../types/student"
import {
  createLearningPlan,
  fetchCurrentLearningPath,
  fetchLearningPlans,
  generateLearningPath
} from "../../api/student";
import {fetchCurrentUser} from "../../api/login";
import i18n from "../../locale";

const {t}=i18n.global

const weekdays = eval(t('student.myLearning.weekdays'));
const monthNames = computed<string[]>(()=> eval(t('student.myLearning.monthNames')));
const tabOptions = computed(()=>[
  {label: t('student.myLearning.myLearningPlans'), value: "plans"},
  {label: t('student.myLearning.personalizedLearningPaths'), value: "path"},
  {label: t('student.myLearning.createNewPlan'), value: "create"},
]);

const activeTab = ref<TabKey>("plans");
const currentUser = ref<{
  username: string;
  user_type: string;
  user_data: Record<string, unknown>;
} | null>(null);

const languages = ref<string[]>(["中文"]);
const plans = ref<LearningPlanFile[]>([]);
const plansLoading = ref(true);
const plansError = ref("");
const selectedPlanIndex = ref<number | null>(null);
const calendarCursor = ref(new Date());

const pathData = ref<LearningPathResponse | null>(null);
const pathLoading = ref(false);
const pathRefreshing = ref(false);
const pathError = ref("");

const creatingPlan = ref(false);
const createError = ref("");
const createdPlan = ref<{ message: string; plan: LearningPlanEntry[] } | null>(null);

const planForm = reactive({
  name: "",
  goals: "",
  lang_choice: "中文",
  priority: "基础知识",
  deadline_days: 7,
});

const displayName = computed(() => {
  const userData = currentUser.value?.user_data ?? {};
  return String(userData["stu_name"] ?? userData["name"] ?? currentUser.value?.username ?? "同学");
});

const greetingTitle = computed(() => t('student.myLearning.welcomeBack', {name: displayName.value}));
const greetingDesc = computed(() => {
  const userData = currentUser.value?.user_data ?? {};
  const goals = Array.isArray(userData["learning_goals"]) ? (userData["learning_goals"] as string[]) : [];
  return goals.length
      ? t('student.myLearning.currentGoalDesciptipn',{goals: goals.join("、")})
      : t('student.myLearning.noCurrentGoalDescription');
});

const selectedPlan = computed(() => {
  if (selectedPlanIndex.value == null) return null;
  return cleanedPlans.value[selectedPlanIndex.value] ?? null;
});

function hasMeaningfulMaterials(materials: unknown) {
  return Array.isArray(materials) && materials.some((item) => String(item ?? "").trim());
}

function isMeaningfulPlanEntry(entry: Partial<LearningPlanEntry> | undefined) {
  if (!entry || typeof entry !== "object") return false;
  return Boolean(
      String(entry.topic ?? "").trim() ||
      String(entry.date ?? "").trim() ||
      String(entry.priority ?? "").trim() ||
      String(entry.deadline ?? "").trim() ||
      hasMeaningfulMaterials(entry.materials),
  );
}

function isDisplayablePlan(plan: LearningPlanFile) {
  const filename = String(plan.filename ?? "").trim();
  const category = String(plan.category ?? "").trim().toLowerCase();

  if (!filename) return false;
  if (filename.includes("_path_")) return false;
  if (category === "path") return false;
  if (category && !["global", "user"].includes(category)) return false;
  if (!Array.isArray(plan.data) || plan.data.length === 0) return false;

  const meaningfulEntries = plan.data.filter((entry) => isMeaningfulPlanEntry(entry));
  if (meaningfulEntries.length === 0) return false;

  const firstEntry = meaningfulEntries[0];
  return Boolean(
      String(firstEntry.topic ?? "").trim() ||
      String(firstEntry.date ?? "").trim() ||
      hasMeaningfulMaterials(firstEntry.materials),
  );
}

const cleanedPlans = computed(() =>
    plans.value
        .filter((plan) => isDisplayablePlan(plan))
        .map((plan) => ({
          ...plan,
          data: plan.data.filter((entry) => isMeaningfulPlanEntry(entry)),
        })),
);

const calendarTitle = computed(() => {
  const year = calendarCursor.value.getFullYear();
  const month = calendarCursor.value.getMonth();
  return `${monthNames.value[month]} ${year}`;
});

const plansThisMonth = computed(() => {
  const year = calendarCursor.value.getFullYear();
  const month = calendarCursor.value.getMonth();
  return cleanedPlans.value.filter((plan) => {
    const raw = plan.data[0]?.date || planDate(plan.filename);
    const date = new Date(raw);
    return date.getFullYear() === year && date.getMonth() === month;
  }).length;
});

const pathNodes = computed(() => {
  const nodes = pathData.value?.weak_nodes ?? [];
  return [...nodes].sort((a, b) => pathPriority(a) - pathPriority(b));
});

const learningHeroBadges = computed(() => [
  `${t('student.myLearning.plans')} ${cleanedPlans.value.length}`,
  `${t('student.myLearning.paths')} ${pathNodes.value.length}`,
  `${t('student.myLearning.languages')} ${languages.value.length}`,
]);

const calendarCells = computed(() => {
  const cursor = calendarCursor.value;
  const year = cursor.getFullYear();
  const month = cursor.getMonth();
  const firstDay = new Date(year, month, 1);
  const lastDay = new Date(year, month + 1, 0);
  const firstWeekday = firstDay.getDay();
  const prevLastDate = new Date(year, month, 0).getDate();
  const cells: Array<{
    day: number;
    currentMonth: boolean;
    hasPlan: boolean;
    hasDeadline: boolean;
    isToday: boolean;
    dateKey: string;
  }> = [];

  for (let offset = firstWeekday - 1; offset >= 0; offset -= 1) {
    cells.push({
      day: prevLastDate - offset,
      currentMonth: false,
      hasPlan: false,
      hasDeadline: false,
      isToday: false,
      dateKey: `prev-${prevLastDate - offset}`,
    });
  }

  const today = new Date();
  for (let day = 1; day <= lastDay.getDate(); day += 1) {
    const dateKey = `${year}-${String(month + 1).padStart(2, "0")}-${String(day).padStart(2, "0")}`;
    const hasPlan = cleanedPlans.value.some((plan) => plan.data.some((entry) => entry.date === dateKey));
    const hasDeadline = cleanedPlans.value.some((plan) => plan.data.some((entry) => entry.deadline === dateKey));
    cells.push({
      day,
      currentMonth: true,
      hasPlan,
      hasDeadline,
      isToday:
          today.getFullYear() === year &&
          today.getMonth() === month &&
          today.getDate() === day,
      dateKey,
    });
  }

  const remainder = cells.length % 7;
  const extra = remainder === 0 ? 0 : 7 - remainder;
  for (let day = 1; day <= extra; day += 1) {
    cells.push({
      day,
      currentMonth: false,
      hasPlan: false,
      hasDeadline: false,
      isToday: false,
      dateKey: `next-${day}`,
    });
  }

  return cells;
});

function planDate(filename: string) {
  const match = filename.match(/(\d{8})_(\d{6})/);
  if (!match) return new Date().toISOString().split("T")[0];
  const dateText = match[1];
  return `${dateText.slice(0, 4)}-${dateText.slice(4, 6)}-${dateText.slice(6, 8)}`;
}

function clampScore(value: number) {
  return Math.max(0, Math.min(100, value || 0));
}

function pathPriority(node: LearningPathNode) {
  return node.llm_priority ?? node.priority ?? 0;
}

function cleanResourceLabel(value: string) {
  const noTags = value.replace(/<[^>]*>/g, "");
  return noTags.replace(/\s+/g, " ").trim();
}

function normalizeMaterials(materials: string[]) {
  const normalized = materials
      .flatMap((material) => splitMaterialBlock(material))
      .map((item) => item.trim())
      .filter(Boolean);

  return normalized.length ? normalized : ["暂无资料说明"];
}

function splitMaterialBlock(text: string) {
  const cleaned = text
      .replace(/\r\n/g, "\n")
      .replace(/\r/g, "\n")
      .replace(/^当然，以下是推荐的.*?资源列表[:：]?\s*/u, "")
      .replace(/^###\s*/gm, "")
      .replace(/^\*\*(.*?)\*\*$/gm, "$1")
      .replace(/\*\*(.*?)\*\*/g, "$1")
      .replace(/^-+\s*简介[:：]?\s*/gm, "简介：")
      .replace(/^-+\s*/gm, "")
      .replace(/^\d+\.\s*/gm, "")
      .trim();

  const lines = cleaned
      .split("\n")
      .map((line) => line.trim())
      .filter(Boolean)
      .filter((line) => !/^中文资源$|^英文资源$/u.test(line));

  const merged: string[] = [];
  for (const line of lines) {
    if (/^简介：/u.test(line) && merged.length) {
      merged[merged.length - 1] = `${merged[merged.length - 1]} ${line}`;
      continue;
    }
    merged.push(line);
  }

  return merged.length ? merged : [cleaned];
}

async function loadCurrentUserInfo() {
  currentUser.value = await fetchCurrentUser();
  const userData = currentUser.value.user_data ?? {};
  if (!planForm.name) {
    planForm.name = String(userData["stu_name"] ?? userData["name"] ?? currentUser.value.username ?? "");
  }
}

async function loadLanguagesList() {
  try {
    const items = await fetchLanguages();
    languages.value = items.length ? items : ["中文"];
    if (!languages.value.includes(planForm.lang_choice)) {
      planForm.lang_choice = languages.value[0];
    }
  } catch {
    languages.value = ["中文"];
  }
}

async function loadPlansList() {
  plansLoading.value = true;
  plansError.value = "";
  try {
    plans.value = await fetchLearningPlans();
    selectedPlanIndex.value = null;
  } catch (error) {
    plansError.value = error instanceof Error ? error.message : t('student.myLearning.errorLoadingLearningPlans');
  } finally {
    plansLoading.value = false;
  }
}

async function loadPath(forceGenerate = false) {
  if (!currentUser.value) return;
  pathLoading.value = !forceGenerate;
  pathRefreshing.value = forceGenerate;
  pathError.value = "";
  try {
    if (forceGenerate) {
      pathData.value = await generateLearningPath(currentUser.value.username);
    } else {
      try {
        pathData.value = await fetchCurrentLearningPath(currentUser.value.username);
      } catch (error: unknown) {
        const axiosError = error as { response?: { status?: number } };
        if (axiosError.response?.status === 404) {
          pathData.value = await generateLearningPath(currentUser.value.username);
        } else {
          throw error;
        }
      }
    }
  } catch (error) {
    pathError.value = error instanceof Error ? error.message : t('student.myLearning.errorLoadingLearningPaths');
  } finally {
    pathLoading.value = false;
    pathRefreshing.value = false;
  }
}

async function handleReplan() {
  await loadPath(true);
}

async function submitPlan() {
  createError.value = "";
  createdPlan.value = null;
  if (!planForm.name || !planForm.goals) {
    createError.value = "请先填写姓名和学习目标。";
    return;
  }
  creatingPlan.value = true;
  try {
    createdPlan.value = await createLearningPlan(planForm);
  } catch (error) {
    createError.value = error instanceof Error ? error.message : t('student.myLearning.errorCreatingLearningPlans');
  } finally {
    creatingPlan.value = false;
  }
}

async function reloadPlans() {
  await loadPlansList();
  activeTab.value = "plans";
  selectedPlanIndex.value = null;
}

function getLearningType(topic:string):string{
  switch (topic){
    case '拓展创新':
      return t('student.myLearning.extendedInnovation')
    case '原理分析':
      return t('student.myLearning.theoreticalAnalysis')
    case '实践应用':
      return t('student.myLearning.practicalApplication')
    case '基础知识':
    default:
      return t('student.myLearning.basicKnowledge');
  }
}

onMounted(async () => {
  await loadCurrentUserInfo();
  await Promise.all([loadLanguagesList(), loadPlansList()]);
  loadPath();
});

/*watch(activeTab, (tab) => {
  if (tab === "path" && !pathData.value && !pathLoading.value) {
    void loadPath();
  }
});*/

watch(cleanedPlans, (nextPlans) => {
  if (selectedPlanIndex.value == null) return;
  if (selectedPlanIndex.value >= nextPlans.length) {
    selectedPlanIndex.value = null;
  }
});
</script>
