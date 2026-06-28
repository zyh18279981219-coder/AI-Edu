<template>
  <div class="learning-shell">
    <PageHero
        eyebrow="My Learning"
        :title="greetingTitle"
        :description="greetingDesc"
        tone="learning"
    >
      <template #actions>
        <el-button type="primary" size="large" round @click="activeTab = 'create'">
          {{$t('student.myLearning.createNewPlan')}}
        </el-button>
      </template>
    </PageHero>

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
                <li 
                  v-for="material in normalizeMaterials(entry.materials)" 
                  :key="material"
                  :class="{ 'material-category': isMaterialCategory(material) }"
                >
                  {{ material }}
                </li>
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
            <div>
              <h2>{{ $t('student.myLearning.personalizedLearningPaths') }}</h2>
            </div>
            <div style="display: flex; gap: 10px;">
              <button 
                v-if="pathNodes.length > 0" 
                type="button" 
                class="ghost-btn" 
                @click="togglePathSort"
              >
                {{ pathSortMode === 'mastery' ? '按掌握度排序' : '按优先级排序' }}
              </button>
              <button type="button" class="path-action-btn" @click="handleReplan" :disabled="pathRefreshing">
                {{ pathRefreshing ? $t('student.myLearning.underPlanning') : $t('student.myLearning.replanning') }}
              </button>
            </div>
          </div>

          <div v-if="pathLoading" class="state-card">{{ $t('student.myLearning.loadingLearningPaths') }}</div>
          <div v-else-if="pathError" class="state-card error-state">{{ pathError }}</div>
          <div v-else-if="pathData?.status === 'error'" class="state-card error-state path-empty-state">
            <div>{{ pathData.message || $t('student.myLearning.noLearningPaths') }}</div>
            <button type="button" class="path-action-btn" @click="handleReplan" :disabled="pathRefreshing">
              {{ pathRefreshing ? '正在生成...' : '生成个性化路径' }}
            </button>
          </div>
          <div v-else-if="pathData?.status === 'no_weak_nodes'" class="state-card">
            {{ $t('student.myLearning.noWeakNodes') }}
          </div>
          <div v-else-if="pathNodes.length === 0" class="state-card path-empty-state">
            <div>{{ $t('student.myLearning.noLearningData') }}</div>
            <button type="button" class="path-action-btn" @click="handleReplan" :disabled="pathRefreshing">
              {{ pathRefreshing ? '正在生成...' : '生成个性化路径' }}
            </button>
          </div>
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
                  <div>
                    <div class="list-title">{{ $t('student.myLearning.learningPathPriority', { level: pathPriority(node), name: node.node_id }) }}</div>
                    <div class="path-status-row">
                      <span class="path-status-pill" :class="`is-${pathNodeStatus(node.node_id).status}`">
                        {{ pathStatusLabel(pathNodeStatus(node.node_id).status) }}
                      </span>
                      <span v-if="pathNodeStatus(node.node_id).completed_at" class="muted">
                        完成于 {{ formatPathTime(pathNodeStatus(node.node_id).completed_at) }}
                      </span>
                      <span v-else-if="pathNodeStatus(node.node_id).started_at" class="muted">
                        开始于 {{ formatPathTime(pathNodeStatus(node.node_id).started_at) }}
                      </span>
                    </div>
                  </div>
                  <span class="muted">{{ $t('student.myLearning.learningMastery', { value: node.mastery_score }) }}</span>
                </div>
                <div class="mastery-track">
                  <span class="mastery-fill" :style="{ width: `${clampScore(node.mastery_score)}%` }"></span>
                </div>
                <div v-if="node.suggested_actions?.length" class="path-suggestion-list">
                  <span v-for="action in node.suggested_actions.slice(0, 3)" :key="action">{{ action }}</span>
                </div>
                <div v-if="node.resources?.length" class="path-resource-grid">
                  <article
                      v-for="resource in node.resources"
                      :key="resource.url"
                      class="resource-card-vue"
                  >
                    <div class="resource-card-top">
                      <span class="resource-kind">{{ resourceTypeLabel(resource) }}</span>
                      <span v-if="resource.score != null" class="resource-score">
                        {{ Math.round(resource.score * 100) }}%
                      </span>
                    </div>
                    <h3>{{ cleanResourceLabel(resource.title || resource.url) }}</h3>
                    <p v-if="resource.reason" class="resource-reason">{{ resource.reason }}</p>
                    <div class="resource-actions">
                      <button
                          v-if="resource.embed_url"
                          type="button"
                          class="resource-primary-btn"
                          @click="openVideo(resource)"
                      >
                        观看视频
                      </button>
                      <a
                          :href="resource.url"
                          target="_blank"
                          rel="noopener noreferrer"
                      >
                        打开原链接
                      </a>
                    </div>
                  </article>
                </div>
                <div class="path-node-actions">
                  <button
                      type="button"
                      class="ghost-btn"
                      :disabled="isPathStatusBusy(node.node_id) || pathNodeStatus(node.node_id).status === 'completed'"
                      @click="handlePathStatusUpdate(node.node_id, 'in_progress')"
                  >
                    {{ pathNodeStatus(node.node_id).status === 'in_progress' ? '学习中' : '开始学习' }}
                  </button>
                  <button
                      type="button"
                      class="path-action-btn"
                      :disabled="isPathStatusBusy(node.node_id) || pathNodeStatus(node.node_id).status === 'completed'"
                      @click="handlePathStatusUpdate(node.node_id, 'completed', node.mastery_score)"
                  >
                    {{ pathNodeStatus(node.node_id).status === 'completed' ? '已完成' : '标记完成' }}
                  </button>
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
                <li 
                  v-for="material in normalizeMaterials(entry.materials)" 
                  :key="material"
                  :class="{ 'material-category': isMaterialCategory(material) }"
                >
                  {{ material }}
                </li>
              </ul>
            </div>
          </div>
        </section>
      </div>
    </section>

    <div v-if="activeVideoResource" class="video-modal-mask" @click.self="closeVideo">
      <section class="video-modal">
        <div class="video-modal-head">
          <h2>{{ cleanResourceLabel(activeVideoResource.title || '推荐视频') }}</h2>
          <button type="button" class="ghost-btn" @click="closeVideo">关闭</button>
        </div>
        <iframe
            :src="activeVideoResource.embed_url || ''"
            allowfullscreen
            scrolling="no"
            referrerpolicy="no-referrer-when-downgrade"
        ></iframe>
      </section>
    </div>
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
  type LearningPathNodeStatus,
  type LearningPathNodeStatusValue,
  type LearningPathResponse,
  type LearningPlanEntry,
  type LearningPlanFile,
} from "../../types/student"
import {
  createLearningPlan,
  fetchCurrentLearningPath,
  fetchLearningPlans,
  generateLearningPath,
  updateLearningPathNodeStatus
} from "../../api/student";
import type { LearningPathResource } from "../../types/student";
import {fetchCurrentUser} from "../../api/login";
import i18n from "../../locale";

const {t}=i18n.global
type TabKey = "plans" | "path" | "create";

// 安全解析 i18n 数组，避免使用 eval
function safeParseI18nArray(value: string): string[] {
  try {
    // 尝试 JSON.parse
    return JSON.parse(value);
  } catch {
    // 如果失败，提供安全的 fallback
    return [];
  }
}

const weekdays = safeParseI18nArray(t('student.myLearning.weekdays'));
const monthNames = computed<string[]>(() => safeParseI18nArray(t('student.myLearning.monthNames')));
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
const pathSortMode = ref<'priority' | 'mastery'>('priority');
const activeVideoResource = ref<LearningPathResource | null>(null);
const pathStatusUpdating = ref<Record<string, boolean>>({});

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
  const nodes = pathData.value?.formal_path_nodes?.length
      ? pathData.value.formal_path_nodes
      : pathData.value?.weak_nodes ?? [];
  if (pathSortMode.value === 'mastery') {
    // 按掌握度排序：从低到高
    return [...nodes].sort((a, b) => a.mastery_score - b.mastery_score);
  }
  // 按优先级排序（默认）
  return [...nodes].sort((a, b) => pathPriority(a) - pathPriority(b));
});

const pathStatusMap = computed<Record<string, LearningPathNodeStatus>>(() => {
  const result: Record<string, LearningPathNodeStatus> = {};
  for (const item of pathData.value?.path_node_status ?? []) {
    if (!item.node_id) continue;
    result[item.node_id] = item;
  }
  return result;
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
  return node.sequence_order ?? node.llm_priority ?? node.priority ?? 0;
}

function defaultPathNodeStatus(nodeId: string): LearningPathNodeStatus {
  return {
    status_id: 0,
    plan_id: 0,
    username: currentUser.value?.username ?? "",
    node_id: nodeId,
    item_type: "course_knowledge_point",
    source_type: "published_course_graph",
    status: "pending",
  };
}

function pathNodeStatus(nodeId: string): LearningPathNodeStatus {
  return pathStatusMap.value[nodeId] ?? defaultPathNodeStatus(nodeId);
}

function pathStatusLabel(status: LearningPathNodeStatusValue) {
  switch (status) {
    case "in_progress":
      return "学习中";
    case "completed":
      return "已完成";
    case "skipped":
      return "暂不执行";
    case "pending":
    default:
      return "待学习";
  }
}

function formatPathTime(value?: string | null) {
  if (!value) return "";
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) return value;
  return `${parsed.getMonth() + 1}/${parsed.getDate()} ${String(parsed.getHours()).padStart(2, "0")}:${String(parsed.getMinutes()).padStart(2, "0")}`;
}

function isPathStatusBusy(nodeId: string) {
  return Boolean(pathStatusUpdating.value[nodeId]);
}

function mergePathNodeStatus(updated: LearningPathNodeStatus) {
  if (!pathData.value) return;
  const existing = pathData.value.path_node_status ?? [];
  const next = existing.filter((item) => item.status_id !== updated.status_id && item.node_id !== updated.node_id);
  pathData.value = {
    ...pathData.value,
    path_node_status: [...next, updated],
  };
}

function cleanResourceLabel(value: string) {
  const noTags = value.replace(/<[^>]*>/g, "");
  return noTags.replace(/\s+/g, " ").trim();
}

function resourceTypeLabel(resource: LearningPathResource) {
  const provider = resource.provider || resource.source || "资源";
  switch (resource.type) {
    case "video":
      return `${provider} · 视频`;
    case "article":
    case "blog":
      return `${provider} · 文章`;
    case "document":
      return `${provider} · 讲义`;
    default:
      return `${provider} · 资料`;
  }
}

function openVideo(resource: LearningPathResource) {
  activeVideoResource.value = resource;
}

function closeVideo() {
  activeVideoResource.value = null;
}

async function handlePathStatusUpdate(
    nodeId: string,
    status: "pending" | "in_progress" | "completed" | "skipped",
    masteryScore?: number,
) {
  if (!currentUser.value) return;
  const current = pathNodeStatus(nodeId);
  pathStatusUpdating.value = {...pathStatusUpdating.value, [nodeId]: true};
  pathError.value = "";
  try {
    const updated = await updateLearningPathNodeStatus(currentUser.value.username, nodeId, {
      status,
      plan_id: current.plan_id || null,
      mastery_after: status === "completed" ? Math.max(Number(masteryScore ?? current.mastery_before ?? 0), 60) : null,
      payload: {
        source: "student_learning_page",
      },
    });
    mergePathNodeStatus(updated);
  } catch (error) {
    pathError.value = error instanceof Error ? error.message : "学习路径状态更新失败";
  } finally {
    const next = {...pathStatusUpdating.value};
    delete next[nodeId];
    pathStatusUpdating.value = next;
  }
}

function normalizeMaterials(materials: string[]) {
  const normalized = materials
      .flatMap((material) => splitMaterialBlock(material))
      .map((item) => item.trim())
      .filter(Boolean);

  return normalized.length ? normalized : ["暂无资料说明"];
}

function isMaterialCategory(text: string): boolean {
  // 判断是否为资源分类标题
  const trimmed = text.trim();
  
  // 1. 明确的资源分类标题
  const categoryPatterns = [
    /^中文资源$/,
    /^英文资源$/,
    /^中文资料$/,
    /^英文资料$/,
    /^Chinese Resources?$/i,
    /^English Resources?$/i,
    /^资源列表$/,
    /^推荐资源$/,
  ];
  
  if (categoryPatterns.some(pattern => pattern.test(trimmed))) {
    return true;
  }
  
  // 2. 包含"资源"、"课程"、"教程"等关键词的短标题（少于15个字符）
  const shortTitlePatterns = [
    /^在线课程$/,
    /^视频课程$/,
    /^视频资源$/,
    /^视频教程$/,
    /^博客文章$/,
    /^博客和文章$/,
    /^技术博客$/,
    /^书籍推荐$/,
    /^推荐书籍$/,
    /^在线文档$/,
    /^官方文档$/,
    /^学习资料$/,
    /^参考资料$/,
    /^实践项目$/,
    /^练习资源$/,
    /^社区资源$/,
    /^工具推荐$/,
    /^Online Courses?$/i,
    /^Video Tutorials?$/i,
    /^Blog Posts?$/i,
    /^Books?$/i,
    /^Documentation$/i,
    /^Practice Projects?$/i,
    /^Community Resources?$/i,
  ];
  
  if (shortTitlePatterns.some(pattern => pattern.test(trimmed))) {
    return true;
  }
  
  // 3. 短文本（少于20字符）且包含关键词
  if (trimmed.length < 20) {
    const keywords = ['资源', '课程', '教程', '文章', '博客', '书籍', '文档', '项目', '工具', 'Resources', 'Courses', 'Tutorials', 'Articles', 'Books', 'Documentation'];
    if (keywords.some(keyword => trimmed.includes(keyword))) {
      // 排除包含冒号、破折号、网址等的内容（这些通常是具体资源）
      if (!trimmed.includes(':') && !trimmed.includes('：') && !trimmed.includes('-') && !trimmed.includes('http') && !trimmed.includes('.com')) {
        return true;
      }
    }
  }
  
  return false;
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
  const user = await fetchCurrentUser();
  currentUser.value = user;
  const userData = user.user_data ?? {};
  if (!planForm.name) {
    planForm.name = String(userData["stu_name"] ?? userData["name"] ?? user.username ?? "");
  }
}

function cleanLanguageLabel(label: string): string {
  // 移除 Unicode 表情符号（国旗等），但保留其他字符
  let cleaned = label
    .replace(/[\u{1F1E0}-\u{1F1FF}]/gu, '') // 移除国旗表情
    .replace(/[\u{1F300}-\u{1F9FF}]/gu, '') // 移除其他表情
    .replace(/[\u{2600}-\u{26FF}]/gu, '')   // 移除杂项符号
    .replace(/[\u{2700}-\u{27BF}]/gu, '')   // 移除装饰符号
    .trim();
  
  // 如果清理后还有内容，直接返回
  if (cleaned.length >= 2) {
    return cleaned;
  }
  
  // 如果清理后为空，尝试从原标签提取语言代码并映射
  const match = label.match(/\b(ZH|EN|PL|CS|SK|DE|FR|ES|IT|PT|RU|UK|NL|SV|FI|NO|DA|TR|JA|KO|AR|HE)\b/i);
  if (match) {
    const code = match[1].toLowerCase();
    const languageMap: Record<string, string> = {
      'zh': '中文',
      'en': '英语',
      'pl': '波兰语',
      'cs': '捷克语',
      'sk': '斯洛伐克语',
      'de': '德语',
      'fr': '法语',
      'es': '西班牙语',
      'it': '意大利语',
      'pt': '葡萄牙语',
      'ru': '俄语',
      'uk': '乌克兰语',
      'nl': '荷兰语',
      'sv': '瑞典语',
      'fi': '芬兰语',
      'no': '挪威语',
      'da': '丹麦语',
      'tr': '土耳其语',
      'ja': '日语',
      'ko': '韩语',
      'ar': '阿拉伯语',
      'he': '希伯来语',
    };
    return languageMap[code] || label;
  }
  
  // 如果都失败了，返回原标签
  return label;
}

async function loadLanguagesList() {
  try {
    const response = await fetchLanguages();
    console.log('API 返回的原始数据:', response); // 调试日志
    console.log('数据类型:', typeof response, '是否为数组:', Array.isArray(response));
    
    // 处理不同的响应格式
    let items: string[] = [];
    if (Array.isArray(response)) {
      items = response;
    } else if (response && typeof response === 'object' && 'data' in response) {
      // 如果响应被包装在 data 字段中
      const dataField = (response as any).data;
      items = Array.isArray(dataField) ? dataField : [];
    } else if (typeof response === 'string') {
      // 如果返回的是单个字符串
      items = [response];
    }
    
    console.log('提取的语言列表:', items);
    
    if (items.length === 0) {
      console.warn('语言列表为空，使用默认值');
      languages.value = ["中文"];
      return;
    }
    
    // 清理语言标签，移除表情符号
    const cleanedItems = items.map(cleanLanguageLabel);
    console.log('清理后语言列表:', cleanedItems);
    
    languages.value = cleanedItems;
    if (!languages.value.includes(planForm.lang_choice)) {
      planForm.lang_choice = languages.value[0];
    }
  } catch (error) {
    console.error('加载语言列表失败:', error);
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
        const message = error instanceof Error ? error.message : "";
        if (axiosError.response?.status === 404 || message.includes("No learning path found")) {
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

function togglePathSort() {
  pathSortMode.value = pathSortMode.value === 'priority' ? 'mastery' : 'priority';
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

<style scoped>
.path-status-row {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px;
  margin-top: 8px;
}

.path-status-pill {
  display: inline-flex;
  align-items: center;
  min-height: 24px;
  padding: 3px 9px;
  border-radius: 999px;
  font-size: 12px;
  font-weight: 700;
  background: #eef2ff;
  color: #4338ca;
}

.path-status-pill.is-in_progress {
  background: #e0f2fe;
  color: #0369a1;
}

.path-status-pill.is-completed {
  background: #dcfce7;
  color: #15803d;
}

.path-status-pill.is-skipped {
  background: #f1f5f9;
  color: #475569;
}

.path-suggestion-list {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 12px;
}

.path-suggestion-list span {
  display: inline-flex;
  align-items: center;
  min-height: 26px;
  padding: 4px 10px;
  border-radius: 999px;
  background: #f8fafc;
  color: #475569;
  font-size: 12px;
  font-weight: 700;
}

.path-node-actions {
  display: flex;
  flex-wrap: wrap;
  justify-content: flex-end;
  gap: 10px;
  margin-top: 14px;
}
</style>
