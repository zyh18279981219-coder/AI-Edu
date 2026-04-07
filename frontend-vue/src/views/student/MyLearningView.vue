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
          创建新计划
        </el-button>
      </template>
    </PageHero>

    <section class="metric-grid learning-metric-grid">
      <MetricStatCard label="学习计划" :value="cleanedPlans.length" description="历史计划与当前计划会一起汇总。"
                      tone="brand"/>
      <MetricStatCard label="路径节点" :value="pathNodes.length" description="根据薄弱知识点生成的个性化路径节点。"
                      tone="warning"/>
      <MetricStatCard label="可选语言" :value="languages.length" description="创建新计划时可选择的输出语言数量。"/>
      <MetricStatCard label="本月计划" :value="plansThisMonth" description="当前月历中已经安排的学习任务数量。"
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
            <h2>学习日历</h2>
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
          <p class="calendar-summary">本月计划 {{ plansThisMonth }} 项 | 全部计划 {{ cleanedPlans.length }} 项</p>
        </div>
      </aside>

      <div class="learning-main">
        <SegmentedTabs v-model="activeTab" :tabs="tabOptions"/>

        <section v-if="activeTab === 'plans'" class="card-panel tab-panel learning-panel">
          <div class="section-head">
            <h2>学习计划列表</h2>
            <span class="muted">按生成时间倒序展示</span>
          </div>

          <div v-if="plansLoading" class="state-card">正在加载学习计划...</div>
          <div v-else-if="plansError" class="state-card error-state">{{ plansError }}</div>
          <div v-else-if="selectedPlan" class="plan-detail">
            <div class="plan-detail-header">
              <div>
                <div class="list-title">{{ selectedPlan.data[0]?.topic || "学习计划" }}</div>
                <div class="list-meta">
                  {{ selectedPlan.data[0]?.date || "未标注日期" }}
                  <span v-if="selectedPlan.data[0]?.priority"> · {{ selectedPlan.data[0]?.priority }}</span>
                </div>
              </div>
              <button type="button" class="ghost-btn" @click="selectedPlanIndex = null">返回列表</button>
            </div>
            <div
                class="plan-entry"
                v-for="entry in selectedPlan.data"
                :key="`${selectedPlan.filename}-${entry.date}-${entry.topic}`"
            >
              <h3>{{ entry.date }} · {{ entry.topic }}</h3>
              <p class="muted">学习类型：{{ entry.priority }}</p>
              <p v-if="entry.deadline" class="deadline-text">截止日期：{{ entry.deadline }}</p>
              <ul class="material-list">
                <li v-for="material in normalizeMaterials(entry.materials)" :key="material">{{ material }}</li>
              </ul>
            </div>
          </div>
          <div v-else-if="cleanedPlans.length === 0" class="state-card">暂无学习计划，先创建一份新的吧。</div>
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
                <span class="muted">{{ plan.data[0]?.priority || "未标注类型" }}</span>
              </div>
              <div class="list-title">{{ plan.data[0]?.topic || "学习计划" }}</div>
              <div class="list-meta">
                共 {{ plan.data.length }} 天计划
                <span v-if="plan.data[0]?.deadline"> · 截止 {{ plan.data[0]?.deadline }}</span>
              </div>
            </button>
          </div>
        </section>

        <section v-else-if="activeTab === 'path'" class="card-panel tab-panel learning-panel">
          <div class="section-head">
            <h2>个性化学习路径</h2>
            <button type="button" class="path-action-btn" @click="handleReplan" :disabled="pathRefreshing">
              {{ pathRefreshing ? "规划中..." : "重新规划" }}
            </button>
          </div>

          <div v-if="pathLoading" class="state-card">正在加载学习路径...</div>
          <div v-else-if="pathError" class="state-card error-state">{{ pathError }}</div>
          <div v-else-if="pathData?.status === 'error'" class="state-card error-state">
            {{ pathData.message || "当前暂无可用学习路径" }}
          </div>
          <div v-else-if="pathData?.status === 'no_weak_nodes'" class="state-card">
            当前暂无明显薄弱知识点，继续保持学习节奏即可。
          </div>
          <div v-else-if="pathNodes.length === 0" class="state-card">暂无学习路径数据。</div>
          <div v-else class="path-panel">
            <div v-if="pathData?.llm_advice" class="advice-box">
              <div class="list-title">AI 个性化学习建议</div>
              <p>{{ pathData.llm_advice }}</p>
            </div>
            <div v-if="pathData?.llm_order_reason" class="order-tip">
              {{ pathData.llm_order_reason }}
            </div>
            <div class="path-grid">
              <article class="path-card-vue" v-for="node in pathNodes" :key="node.node_id">
                <div class="path-card-head">
                  <div class="list-title">优先级 {{ pathPriority(node) }} · {{ node.node_id }}</div>
                  <span class="muted">掌握度 {{ node.mastery_score }}%</span>
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
            <h2>创建新的学习计划</h2>
            <span class="muted">基于你的学习目标生成一份可执行计划</span>
          </div>

          <form class="plan-form" @submit.prevent="submitPlan">
            <label>
              语言
              <el-select v-model="planForm.lang_choice" placeholder="请选择语言">
                <el-option v-for="lang in languages" :key="lang" :label="lang" :value="lang"/>
              </el-select>
            </label>
            <label>
              姓名
              <el-input v-model="planForm.name" placeholder="请输入你的姓名"/>
            </label>
            <label class="wide">
              学习目标
              <el-input
                  v-model.trim="planForm.goals"
                  type="textarea"
                  :rows="5"
                  placeholder="例如：掌握 Python 基础；学习数据分析；理解机器学习基本概念"
              />
            </label>
            <label>
              学习类型
              <el-select v-model="planForm.priority" placeholder="请选择学习类型">
                <el-option label="基础知识" value="基础知识"/>
                <el-option label="实践应用" value="实践应用"/>
                <el-option label="原理分析" value="原理分析"/>
                <el-option label="拓展创新" value="拓展创新"/>
              </el-select>
            </label>
            <label>
              完成期限
              <el-select v-model="planForm.deadline_days" placeholder="请选择期限">
                <el-option :value="1" label="1 天"/>
                <el-option :value="3" label="3 天"/>
                <el-option :value="7" label="1 周"/>
                <el-option :value="14" label="2 周"/>
                <el-option :value="30" label="1 个月"/>
              </el-select>
            </label>

            <p v-if="createError" class="form-error">{{ createError }}</p>

            <el-button type="primary" size="large" class="full-width" native-type="submit" :loading="creatingPlan">
              {{ creatingPlan ? "生成中..." : "生成学习计划" }}
            </el-button>
          </form>

          <div v-if="createdPlan" class="created-plan">
            <div class="section-head">
              <h2>{{ createdPlan.message }}</h2>
              <el-button plain @click="reloadPlans">刷新计划列表</el-button>
            </div>
            <div class="plan-entry" v-for="entry in createdPlan.plan" :key="`${entry.date}-${entry.topic}`">
              <h3>{{ entry.date }} · {{ entry.topic }}</h3>
              <p class="muted">学习类型：{{ entry.priority }}</p>
              <p v-if="entry.deadline" class="deadline-text">截止日期：{{ entry.deadline }}</p>
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
  fetchCurrentUser,
  fetchLanguages,
} from "../../api/client";
import {
  type LearningPathNode,
  type LearningPathResponse,
  type LearningPlanEntry,
  type LearningPlanFile,
} from "../../types/student"
import {
  createLearningPlan,
  fetchCurrentLearningPath,
  fetchLearningPlans,
  generateLearningPath
} from "../../api/student";

type TabKey = "plans" | "path" | "create";

const weekdays = ["日", "一", "二", "三", "四", "五", "六"];
const monthNames = ["一月", "二月", "三月", "四月", "五月", "六月", "七月", "八月", "九月", "十月", "十一月", "十二月"];
const tabOptions = [
  {label: "我的学习计划", value: "plans"},
  {label: "个性化学习路径", value: "path"},
  {label: "创建新计划", value: "create"},
];

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

const greetingTitle = computed(() => `欢迎回来，${displayName.value}`);
const greetingDesc = computed(() => {
  const userData = currentUser.value?.user_data ?? {};
  const goals = Array.isArray(userData["learning_goals"]) ? (userData["learning_goals"] as string[]) : [];
  return goals.length
      ? `当前学习目标：${goals.join("、")}。你可以在这里集中管理学习计划、查看个性化学习路径，并快速安排本周任务。`
      : "在这里集中查看学习计划、个性化学习路径和本周学习重点。";
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
  return `${monthNames[month]} ${year}`;
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
  `计划 ${cleanedPlans.value.length}`,
  `路径节点 ${pathNodes.value.length}`,
  `语言 ${languages.value.length}`,
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
    plansError.value = error instanceof Error ? error.message : "学习计划加载失败";
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
    pathError.value = error instanceof Error ? error.message : "学习路径加载失败";
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
    createError.value = error instanceof Error ? error.message : "学习计划生成失败";
  } finally {
    creatingPlan.value = false;
  }
}

async function reloadPlans() {
  await loadPlansList();
  activeTab.value = "plans";
  selectedPlanIndex.value = null;
}

onMounted(async () => {
  await loadCurrentUserInfo();
  await Promise.all([loadLanguagesList(), loadPlansList()]);
});

watch(activeTab, (tab) => {
  if (tab === "path" && !pathData.value && !pathLoading.value) {
    void loadPath();
  }
});

watch(cleanedPlans, (nextPlans) => {
  if (selectedPlanIndex.value == null) return;
  if (selectedPlanIndex.value >= nextPlans.length) {
    selectedPlanIndex.value = null;
  }
});
</script>
