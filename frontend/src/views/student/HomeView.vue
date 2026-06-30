<template>
  <div class="home-shell">
    <!-- 新增：首页欢迎横幅 -->
    <div class="student-home-v2-hero">
      <div class="student-home-v2-hero-content">
        <h1 class="student-home-v2-hero-title">你好，{{ displayName }}</h1>
        <p class="student-home-v2-hero-subtitle">{{ homeSubtitle }}</p>
      </div>
      <div class="student-home-v2-hero-stats">
        <div class="student-home-v2-stat-item">
          <div class="student-home-v2-stat-icon">%</div>
          <div class="student-home-v2-stat-info">
            <div class="student-home-v2-stat-number">{{ overallMasteryText }}</div>
            <div class="student-home-v2-stat-text">总体掌握度</div>
          </div>
        </div>
        <div class="student-home-v2-stat-item">
          <div class="student-home-v2-stat-icon">KP</div>
          <div class="student-home-v2-stat-info">
            <div class="student-home-v2-stat-number">{{ completedPointsText }}</div>
            <div class="student-home-v2-stat-text">已完成知识点</div>
          </div>
        </div>
        <div class="student-home-v2-stat-item">
          <div class="student-home-v2-stat-icon">HW</div>
          <div class="student-home-v2-stat-info">
            <div class="student-home-v2-stat-number">{{ pendingHomeworkCount }}</div>
            <div class="student-home-v2-stat-text">待完成作业</div>
          </div>
        </div>
        <div class="student-home-v2-stat-item">
          <div class="student-home-v2-stat-icon">D</div>
          <div class="student-home-v2-stat-info">
            <div class="student-home-v2-stat-number">{{ consecutiveDaysText }}</div>
            <div class="student-home-v2-stat-text">连续学习</div>
          </div>
        </div>
      </div>
    </div>

    <!-- 新增：通知横幅 -->
    <div v-if="notificationBanner" class="student-home-v2-alert-banner" :class="'student-home-v2-alert-' + notificationBanner.type">
      <div class="student-home-v2-alert-icon">{{ notificationBanner.icon }}</div>
      <div class="student-home-v2-alert-content">
        <strong>{{ notificationBanner.title }}</strong>{{ notificationBanner.message }}
      </div>
      <RouterLink :to="notificationBanner.link" class="student-home-v2-alert-btn">立即查看</RouterLink>
    </div>

    <section v-if="error" class="state-card error-state">
      <h2>{{ $t('student.home.loadingError') }}</h2>
      <p>{{ error }}</p>
    </section>

    <template v-else>
      <!-- 第三阶段：三栏布局 -->
      <div class="student-home-v2-three-column-layout">
        <!-- 左栏：今日计划 + 需要加强 + 最近通知 -->
        <aside class="student-home-v2-left-column">
          <!-- 今日计划 -->
          <article class="card-panel student-home-v2-plan-card">
            <div class="section-head">
              <h2>📅 今日计划</h2>
              <span class="student-home-v2-badge-progress">{{ todayPlanCompleted }}/{{ todayPlanTotal }}</span>
            </div>
            <div class="student-home-v2-plan-list">
              <div v-for="(task, index) in todayPlanTasks" :key="`${task.source}-${index}-${task.text}`"
                   class="student-home-v2-plan-task"
                   :class="{ 'student-home-v2-plan-task-done': task.done }">
                <div class="student-home-v2-task-check">{{ task.done ? '✓' : '○' }}</div>
                <RouterLink v-if="task.link" :to="task.link" class="student-home-v2-task-text">{{ task.text }}</RouterLink>
                <div v-else class="student-home-v2-task-text">{{ task.text }}</div>
              </div>
              <div v-if="!todayPlanTasks.length" class="student-home-v2-empty-line">
                {{ todayPlanEmptyText }}
              </div>
            </div>
            <RouterLink :to="todayPlanActionRoute" class="student-home-v2-card-action-btn">
              <span>{{ todayPlanActionText }}</span>
              <span>→</span>
            </RouterLink>
          </article>

          <!-- 需要加强 -->
          <article class="card-panel student-home-v2-weak-card">
            <div class="section-head">
              <h2>需要加强</h2>
              <span class="student-home-v2-badge-count">{{ weakPoints.length }}个</span>
            </div>
            <div class="student-home-v2-weak-list">
              <div v-for="(point, index) in weakPoints" :key="index" class="student-home-v2-weak-item">
                <div class="student-home-v2-weak-header">
                  <span class="student-home-v2-weak-name">{{ point.name }}</span>
                  <span class="student-home-v2-weak-score" :class="point.levelClass">{{ point.score }}%</span>
                </div>
                <div class="student-home-v2-progress-bar-mini">
                  <div class="student-home-v2-progress-fill-mini" :class="point.levelClass" :style="{ width: point.score + '%' }"></div>
                </div>
              </div>
              <div v-if="!weakPoints.length" class="student-home-v2-empty-line">{{ weakPointsEmptyText }}</div>
            </div>
          </article>

          <!-- 最近通知 -->
          <article class="card-panel student-home-v2-notification-card">
            <div class="section-head">
              <h2>最近通知</h2>
            </div>
            <div class="student-home-v2-notification-list">
              <RouterLink
                v-for="(notif, index) in recentNotifications"
                :key="index"
                :to="notif.link || '/student/home'"
                class="student-home-v2-notification-item"
              >
                <div class="student-home-v2-notif-icon">{{ notif.icon }}</div>
                <div class="student-home-v2-notif-content">
                  <div class="student-home-v2-notif-title">{{ notif.title }}</div>
                  <div class="student-home-v2-notif-time">{{ notif.time }}</div>
                </div>
              </RouterLink>
              <div v-if="notificationsLoading" class="student-home-v2-empty-line">通知加载中...</div>
              <div v-else-if="notificationsError" class="student-home-v2-empty-line">{{ notificationsError }}</div>
              <div v-else-if="!recentNotifications.length" class="student-home-v2-empty-line">{{ notificationsEmptyText }}</div>
            </div>
          </article>
        </aside>

        <!-- 中栏：知识图谱核心区域 -->
        <article class="card-panel student-home-v2-center-column">
          <div class="section-head home-head">
            <div>
              <h2>{{$t('student.home.knowledgeGraph')}}</h2>
              <span class="muted">{{$t('student.home.knowledgeGraphDescription')}}</span>
            </div>
            <div class="home-head-actions">
              <button type="button" class="ghost-btn" @click="focusCurrentTrack">{{ $t('student.home.focusCurrentTrack') }}</button>
              <button type="button" class="ghost-btn" @click="resetSelection">{{$t('student.home.resetSelection')}}</button>
            </div>
          </div>

          <div v-if="loading" class="state-card">{{$t('student.home.loadingLearningData')}}</div>
          <template v-else>
            <div v-if="selectedNode" class="home-root-card">
              <div>
                <div class="home-root-kicker">{{ selectedNodeLabel }}</div>
                <h3>{{ selectedNodeTitle }}</h3>
                <p>{{ selectedNodeDescription || $t('student.home.selectedNodeDescription') }}</p>
              </div>
            </div>

            <div class="home-visual-block">
              <div class="home-level-head">
                <div>
                  <h3>{{$t('student.home.knowledgeGraphView')}}</h3>
                  <span class="muted">{{$t('student.home.knowledgeGraphViewDescription')}}</span>
                </div>
                <div class="home-head-actions">
                  <div class="home-graph-legend" aria-label="知识图谱层级图例">
                    <span><i class="chapter"></i>章节</span>
                    <span><i class="section"></i>小节</span>
                    <span><i class="point"></i>知识点</span>
                  </div>
                  <button type="button" class="ghost-btn" @click="collapseToCourse">{{$t('student.home.collapseToCourse')}}</button>
                  <button type="button" class="ghost-btn" @click="collapseToChapter" :disabled="!activeChapterKey">
                    {{$t('student.home.collapseToChapter')}}
                  </button>
                </div>
              </div>
              <div class="home-graph-breadcrumb">
                <button type="button" class="home-crumb" :class="{ active: !activeChapterKey && !activeSectionKey }"
                        @click="collapseToCourse">
                  {{$t('student.home.courseOverview')}}
                </button>
                <span v-if="activeChapterKey" class="home-crumb-separator">›</span>
                <button
                    v-if="activeChapterKey"
                    type="button"
                    class="home-crumb"
                    :class="{ active: activeChapterKey && !activeSectionKey }"
                    @click="collapseToChapter"
                >
                  {{ activeChapter?.name }}
                </button>
                <span v-if="activeSectionKey" class="home-crumb-separator">›</span>
                <span v-if="activeSectionKey" class="home-crumb home-crumb--static">{{ activeSection?.name }}</span>
              </div>
              <div ref="graphChartRef" class="home-graph-canvas"></div>
            </div>

            <div class="home-level-block">
              <div class="home-level-head">
                <h3>{{$t('student.home.chapter')}}</h3>
                <span class="muted">{{$t('student.home.numberOfChapters',chapterNodes.length,{named:{number:chapterNodes.length} })}}</span>
              </div>
              <div class="home-chip-grid home-chip-grid--chapter">
                <button
                    v-for="chapter in chapterNodes"
                    :key="chapter.name"
                    type="button"
                    class="home-node-chip home-node-chip--chapter"
                    :class="{
                    active: activeChapterKey === chapter.name,
                    current: currentChapter?.name === chapter.name,
                    done: nodeFlag(chapter) === '1',
                  }"
                    @click="selectChapter(chapter)"
                >
                  <span class="home-node-title">{{ chapter.name }}</span>
                  <span class="home-node-meta">{{ nodeMeta(chapter, $t('student.home.chapter')) }}</span>
                </button>
              </div>
            </div>

            <div class="home-level-block">
              <div class="home-level-head">
                <h3>{{$t('student.home.section')}}</h3>
                <span class="muted">{{$t('student.home.numberOfSections',activeSections.length,{named:{number:activeSections.length} })}}</span>
              </div>
              <div class="home-chip-grid">
                <button
                    v-for="section in activeSections"
                    :key="section.name"
                    type="button"
                    class="home-node-chip"
                    :class="{
                    active: activeSectionKey === section.name,
                    current: currentSection?.name === section.name,
                    done: nodeFlag(section) === '1',
                  }"
                    @click="selectSection(section)"
                >
                  <span class="home-node-title">{{ section.name }}</span>
                  <span class="home-node-meta">{{ nodeMeta(section, $t('student.home.section')) }}</span>
                </button>
                <div v-if="!activeSections.length" class="list-card">{{$t('student.home.noSectionsData')}}</div>
              </div>
            </div>

            <div class="home-level-block">
              <div class="home-level-head">
                <h3>{{$t('student.home.point')}}</h3>
                <span class="muted">{{$t('student.home.numberOfPoints',activePoints.length,{named:{number:activePoints.length} })}}</span>
              </div>
              <div class="home-point-list">
                <button
                    v-for="point in activePoints"
                    :key="point.name"
                    type="button"
                    class="home-point-card"
                    :class="{
                    active: selectedNodeKey === point.name,
                    current: currentPoint?.name === point.name,
                    done: nodeFlag(point) === '1',
                  }"
                    @click="selectPoint(point)"
                >
                  <div>
                    <div class="home-node-title">{{ point.name }}</div>
                    <div class="home-node-meta">{{ nodeMeta(point, $t('student.home.point')) }}</div>
                  </div>
                  <span class="pill" :class="nodeFlag(point) === '1' ? 'mastery-high' : 'mastery-mid'">
                    {{ nodeFlag(point) === "1" ? $t('student.home.complete') : $t('student.home.inProgress') }}
                  </span>
                </button>
                <div v-if="!activePoints.length" class="list-card">{{$t('student.home.noPointsData')}}</div>
              </div>
            </div>
          </template>
        </article>

        <!-- 右栏：最新画像摘要 + 当前学习定位 + 知识点详情 + 下一步操作 -->
        <aside class="student-home-v2-right-column">
          <!-- 最新画像摘要 -->
          <article v-if="diagnosisSummary" class="card-panel student-home-v2-diagnosis-card">
            <div class="section-head">
              <h2>🔍 最新画像摘要</h2>
              <span class="student-home-v2-diagnosis-badge-new">NEW</span>
            </div>
            <div class="student-home-v2-diagnosis-summary">
              <div class="student-home-v2-diagnosis-date">{{ diagnosisGeneratedTime }}</div>
              <div class="student-home-v2-diagnosis-risk-level" :class="diagnosisRiskLevel.class">
                <span class="student-home-v2-diagnosis-risk-icon">{{ diagnosisRiskLevel.icon }}</span>
                <span class="student-home-v2-diagnosis-risk-text">{{ diagnosisRiskLevel.text }}</span>
              </div>
              <div class="student-home-v2-diagnosis-highlights">
                <div class="student-home-v2-diagnosis-highlight-item">
                  <span class="student-home-v2-diagnosis-highlight-label">薄弱知识点：</span>
                  <span class="student-home-v2-diagnosis-highlight-value">{{ diagnosisWeakNodeCount }}个</span>
                </div>
                <div class="student-home-v2-diagnosis-highlight-item">
                  <span class="student-home-v2-diagnosis-highlight-label">优势知识点：</span>
                  <span class="student-home-v2-diagnosis-highlight-value">{{ diagnosisStrongNodeCount }}个</span>
                </div>
                <div class="student-home-v2-diagnosis-highlight-item">
                  <span class="student-home-v2-diagnosis-highlight-label">学习趋势：</span>
                  <span class="student-home-v2-diagnosis-highlight-value">{{ diagnosisTrendText }}</span>
                </div>
              </div>
              <RouterLink to="/student/student-twin" class="student-home-v2-diagnosis-btn-view">
                查看完整报告 →
              </RouterLink>
            </div>
          </article>
          <article v-else class="card-panel student-home-v2-diagnosis-card">
            <div class="section-head">
              <h2>🔍 最新画像摘要</h2>
            </div>
            <div class="student-home-v2-empty-line">
              {{ diagnosisEmptyText }}
            </div>
          </article>

          <article class="card-panel home-progress-card">
            <div class="section-head">
              <h2>{{ $t('student.home.currentLearningPositioning') }}</h2>
              <span class="muted">{{ $t('student.home.incompleteNodePositioning') }}</span>
            </div>
            <div class="home-progress-stack">
              <div class="home-progress-item">
                <div class="home-progress-top">
                  <strong>{{ $t('student.home.currentChapter') }}</strong>
                  <span>{{ currentChapter?.name || $t('student.home.none') }}</span>
                </div>
                <div class="progress-line"><span :style="{ width: `${currentChapterPercent}%` }"></span></div>
                <small>{{ currentChapterProgressText }}</small>
              </div>
              <div class="home-progress-item">
                <div class="home-progress-top">
                  <strong>{{$t('student.home.currentSection')}}</strong>
                  <span>{{ currentSection?.name || $t('student.home.none') }}</span>
                </div>
                <div class="progress-line"><span :style="{ width: `${currentSectionPercent}%` }"></span></div>
                <small>{{ currentSectionProgressText }}</small>
              </div>
              <div class="home-progress-item">
                <div class="home-progress-top">
                  <strong>{{$t('student.home.currentPoint')}}</strong>
                  <span>{{ currentPoint?.name || $t('student.home.none') }}</span>
                </div>
                <div class="progress-line"><span :style="{ width: `${currentPointPercent}%` }"></span></div>
                <small>{{ currentPointProgressText }}</small>
              </div>
            </div>
          </article>

          <article class="card-panel student-home-v2-path-card">
            <div class="section-head">
              <h2>当前学习路径</h2>
              <span class="muted">{{ pathSummarySubtitle }}</span>
            </div>
            <div v-if="currentLearningPath" class="student-home-v2-path-summary">
              <div class="student-home-v2-path-meta">
                <span>v{{ currentLearningPath.version_no ?? 1 }}</span>
                <span>{{ triggerLabel(currentLearningPath.trigger_type) }}</span>
                <span>{{ pathStatusText }}</span>
              </div>
              <div class="student-home-v2-path-stats">
                <div>
                  <strong>{{ pathPendingCount }}</strong>
                  <span>待学习</span>
                </div>
                <div>
                  <strong>{{ pathInProgressCount }}</strong>
                  <span>学习中</span>
                </div>
                <div>
                  <strong>{{ pathCompletedCount }}</strong>
                  <span>已完成</span>
                </div>
              </div>
              <div class="list-card student-home-v2-path-next">
                <div class="list-title">{{ nextPathNodeTitle }}</div>
                <div class="list-meta">{{ nextPathNodeMeta }}</div>
                <RouterLink class="primary-link home-action-link" :to="nextPathNodeRoute">继续路径学习</RouterLink>
              </div>
            </div>
            <div v-else class="student-home-v2-empty-line">
              {{ pathSummaryEmptyText }}
            </div>
          </article>

          <article class="card-panel home-detail-card">
            <div class="section-head">
              <h2>{{ $t('student.home.pointDetail') }}</h2>
              <span class="muted">{{ selectedNodeLabel }}</span>
            </div>
            <div class="home-detail-body">
              <h3>{{ selectedNodeTitle }}</h3>
              <p>{{ selectedNodeDescription || $t('student.home.none') }}</p>
              <div class="home-detail-meta">
                <span class="meta-chip">{{$t('student.home.learningStatus',{status:selectedNodeFlagText})}}</span>
                <span class="meta-chip">{{$t('student.home.averageMastery',{value:selectedNodeStats.avgMastery})}}</span>
                <span class="meta-chip">{{$t('student.home.averageCompletion',{value:selectedNodeStats.avgCompletion})}}</span>
                <span class="meta-chip">{{$t('student.home.averageStudyDuration',{minutes:selectedNodeStats.avgStudyDuration})}}</span>
              </div>
            </div>
          </article>

          <article class="card-panel home-action-card">
            <div class="section-head">
              <h2>{{ $t('student.home.nextStep') }}</h2>
            </div>
            <div class="stack-list">
              <div class="list-card">
                <div class="list-title">{{ $t('student.home.prioritizeCurrentPoint') }}</div>
                <div class="list-meta">{{ currentPoint?.name || $t('student.home.noPoint') }}</div>
                <RouterLink class="primary-link home-action-link" :to="continueLearningRoute">{{$t('student.home.enterCourseContent')}}</RouterLink>
              </div>
              <div class="list-card">
                <div class="list-title">{{ $t('student.home.viewLearningPlan') }}</div>
                <div class="list-meta">{{$t('student.home.viewLearningPlanDescription')}}</div>
                <RouterLink class="ghost-btn home-action-link" to="/student/learning">{{$t('student.home.openMyLearning')}}</RouterLink>
              </div>
            </div>
          </article>
        </aside>
      </div>
    </template>
  </div>
</template>

<script setup lang="ts">
import {computed, nextTick, onBeforeUnmount, onMounted, ref, watch} from "vue";
import type {RouteLocationRaw} from "vue-router";
import {RouterLink} from "vue-router";
import MetricStatCard from "../../components/ui/MetricStatCard.vue";
import PageHero from "../../components/ui/PageHero.vue";
import {type ECharts, init} from "../../lib/echarts";
import {
  GraphVisualizationResponse,
  LearningPathNode,
  LearningPathNodeStatus,
  LearningPathResponse,
  LearningProgressResponse,
  GraphVisualizationNode,
  GraphVisualizationRelation,
} from "../../types/student";
import {fetchLearningProgress, fetchGraphVisualization, fetchStudentTwin, fetchCurrentLearningPath} from '../../api/student';
import {type CourseNode,type CurrentNodeInfo} from "../../types/knowledgeGraph";
import {fetchKnowledgeGraph} from "../../api/knowledgeGraph";
import {fetchCurrentUser} from "../../api/login";
import {homeworkListAssignmentsByFilter, homeworkListMySubmissions} from "../../api/homework";
import {fetchLearningStreak} from "../../api/learningStreak";
import {fetchRecentNotifications, type Notification} from "../../api/notification";
import {interventionStudentPackages} from "../../api/intervention";
import type {HomeworkAssignment, HomeworkSubmission} from "../../types/homework";
import type {InterventionPackage} from "../../types/intervention";
import type {StudentTwinSummary} from "../../types/student";
import i18n from "../../locale/index";

const {t}=i18n.global

// 用户信息
const currentUser = ref<{
  username: string;
  user_type: string;
  user_data: Record<string, unknown>;
} | null>(null);

const displayName = computed(() => {
  const userData = currentUser.value?.user_data ?? {};
  return String(userData.stu_name ?? userData.name ?? currentUser.value?.username ?? "同学");
});

const loading = ref(true);
const error = ref("");
const graph = ref<{ name?: string; children?: CourseNode[] } | null>(null);
const graphVisualization = ref<GraphVisualizationResponse | null>(null);
const progress = ref<LearningProgressResponse | null>(null);

// 作业数据
const assignments = ref<HomeworkAssignment[]>([]);
const mySubmissions = ref<HomeworkSubmission[]>([]);
const homeworkLoading = ref(false);

// 学习连续天数数据
const learningStreakData = ref<{ current_streak: number; longest_streak: number; last_activity_date: string | null; total_days: number } | null>(null);
const streakLoading = ref(false);

// 通知数据
const notifications = ref<Notification[]>([]);
const notificationsLoading = ref(false);
const notificationsError = ref("");

// 诊断数据
const diagnosisSummary = ref<StudentTwinSummary | null>(null);
const diagnosisLoading = ref(false);
const diagnosisError = ref("");

// 个性化学习路径：只读取学生已生成路径，首页不自动触发生成
const currentLearningPath = ref<LearningPathResponse | null>(null);
const pathLoading = ref(false);
const pathError = ref("");

// 教师已下发干预任务，只读取学生本人任务，不在首页生成新任务
const interventionPackages = ref<InterventionPackage[]>([]);
const interventionLoading = ref(false);
const interventionError = ref("");

const activeChapterKey = ref("");
const activeSectionKey = ref("");
const selectedNodeKey = ref("");

const currentChapter = ref<CurrentNodeInfo | null>(null);
const currentSection = ref<CurrentNodeInfo | null>(null);
const currentPoint = ref<CurrentNodeInfo | null>(null);

const graphChartRef = ref<HTMLDivElement | null>(null);
let graphChart: ECharts | null = null;

type HomeTask = {
  text: string;
  done: boolean;
  source: "path" | "homework" | "intervention" | "course";
  link?: RouteLocationRaw;
};

type HomeBanner = {
  icon: string;
  title: string;
  message: string;
  link: RouteLocationRaw;
  type: "warning" | "info";
};

const chapterNodes = computed(() => graph.value?.children ?? []);
const allSections = computed(() => chapterNodes.value.flatMap((item) => item.grandchildren ?? []));
const allPoints = computed(() => allSections.value.flatMap((item) => item["great-grandchildren"] ?? []));

const activeChapter = computed(
    () => chapterNodes.value.find((item) => item.name === activeChapterKey.value) ?? chapterNodes.value[0] ?? null,
);
const activeSections = computed(() => activeChapter.value?.grandchildren ?? []);
const activeSection = computed(
    () => activeSections.value.find((item) => item.name === activeSectionKey.value) ?? activeSections.value[0] ?? null,
);
const activePoints = computed(() => activeSection.value?.["great-grandchildren"] ?? []);

const selectedNode = computed(
    () =>
        chapterNodes.value.find((item) => item.name === selectedNodeKey.value) ??
        allSections.value.find((item) => item.name === selectedNodeKey.value) ??
        allPoints.value.find((item) => item.name === selectedNodeKey.value) ??
        (activeSectionKey.value ? activeSection.value : null) ??
        (activeChapterKey.value ? activeChapter.value : null) ??
        null,
);

const graphNodeMap = computed(() => {
  const map = new Map<string, GraphVisualizationNode>();
  for (const node of graphVisualization.value?.mocKgNodeDtoList ?? []) {
    if (!map.has(node.nodeName)) {
      map.set(node.nodeName, node);
    }
  }
  return map;
});

const graphStats = computed(() => {
  const nodes = graphVisualization.value?.mocKgNodeDtoList ?? [];
  const relations = graphVisualization.value?.mocKgRelationDtoList ?? [];
  return {
    totalNodes: nodes.length,
    totalRelations: relations.length,
    leafNodes: nodes.filter((item) => (item.childCount ?? 0) === 0).length,
  };
});

const selectedNodeTitle = computed(() => selectedNode.value?.name || graph.value?.name || "当前课程");
const selectedNodeDescription = computed(() => {
  if (!selectedNode.value) return "";
  return graphNodeMap.value.get(selectedNode.value.name)?.description || selectedNode.value.description || "";
});
const selectedNodeLabel = computed(() => {
  if (!selectedNode.value) return "课程节点";
  if (allPoints.value.some((item) => item.name === selectedNode.value?.name)) return t('student.home.point');
  if (allSections.value.some((item) => item.name === selectedNode.value?.name)) return t('student.home.section');
  if (chapterNodes.value.some((item) => item.name === selectedNode.value?.name)) return t('student.home.chapter');
  return "课程节点";
});
const selectedNodeFlagText = computed(() => (nodeFlag(selectedNode.value) === "1" ? t('student.home.complete') : t('student.home.inProgress')));
const selectedNodeStats = computed(() => {
  const mapped = selectedNode.value ? graphNodeMap.value.get(selectedNode.value.name) : null;
  return {
    avgMastery: mapped?.mocKgNodeAvgStatisticsDto?.avgMasteryRate ?? 0,
    avgCompletion: mapped?.mocKgNodeAvgStatisticsDto?.avgCompletionRate ?? 0,
    avgStudyDuration: mapped?.mocKgNodeAvgStatisticsDto?.avgLearnedTimeCount ?? 0,
  };
});

const currentChapterPercent = computed(() => computePercent(currentChapter.value));
const currentSectionPercent = computed(() => computePercent(currentSection.value));
const currentPointPercent = computed(() => computePercent(currentPoint.value));

const currentChapterProgressText = computed(() => currentText(currentChapter.value, t('student.home.chapter')));
const currentSectionProgressText = computed(() => currentText(currentSection.value, t('student.home.section')));
const currentPointProgressText = computed(() => currentText(currentPoint.value, t('student.home.point')));

const continueLearningRoute = computed(() => {
  const nodeName = currentPoint.value?.name || selectedNode.value?.name;
  return nodeName
      ? {path: "/student/course-content", query: {node: nodeName, continue: "true"}}
      : {path: "/student/course-content", query: {continue: "true"}};
});

// 新增：首页统计数据
const overallMasteryPercent = computed(() => {
  if (diagnosisSummary.value?.overall_mastery !== undefined) {
    return Math.round(Number(diagnosisSummary.value.overall_mastery || 0));
  }
  return null;
});

const overallMasteryText = computed(() => {
  return overallMasteryPercent.value === null ? "待生成" : `${overallMasteryPercent.value}%`;
});

const completedPointsCount = computed(() => {
  return allPoints.value.filter(point => nodeFlag(point) === "1").length;
});

const completedPointsText = computed(() => {
  if (!allPoints.value.length && loading.value) return "加载中";
  if (!allPoints.value.length) return "暂无";
  return String(completedPointsCount.value);
});

const pendingAssignments = computed(() => {
  const submittedIds = new Set(mySubmissions.value.map(s => s.assignment_id));
  return assignments.value.filter((assignment) => assignment.status === "published" && !submittedIds.has(assignment.id));
});

const pendingHomeworkCount = computed(() => {
  return pendingAssignments.value.length;
});

const consecutiveDays = computed(() => {
  // 使用真实的学习连续天数
  return learningStreakData.value?.current_streak ?? null;
});

const consecutiveDaysText = computed(() => {
  if (streakLoading.value) return "加载中";
  if (!learningStreakData.value || !learningStreakData.value.last_activity_date) return "暂无";
  return `${consecutiveDays.value ?? 0}天`;
});

const activeInterventionPackages = computed(() =>
  interventionPackages.value.filter((item) =>
    item.stage === "pushed" &&
    !["completed", "declined"].includes(String(item.student_status || "")),
  ),
);

const homeSubtitle = computed(() => {
  if (todayPlanTasks.value.length) return `当前有 ${todayPlanTasks.value.length} 项真实待办，先处理最靠前的一项。`;
  if (diagnosisSummary.value) return "画像已生成，可查看薄弱点、趋势和能力达成状态。";
  return "暂无画像结论，先完成课程学习、测验或作业来形成学习证据。";
});

const pathStatusMap = computed<Record<string, LearningPathNodeStatus>>(() => {
  const result: Record<string, LearningPathNodeStatus> = {};
  for (const item of currentLearningPath.value?.path_node_status ?? []) {
    if (!item.node_id) continue;
    result[item.node_id] = item;
  }
  return result;
});

const currentPathNodes = computed<LearningPathNode[]>(() => {
  const nodes = currentLearningPath.value?.formal_path_nodes?.length
    ? currentLearningPath.value.formal_path_nodes
    : currentLearningPath.value?.weak_nodes ?? [];
  return [...nodes].sort((a, b) => pathPriority(a) - pathPriority(b));
});

const pathNodeStatusList = computed(() =>
  currentPathNodes.value.map((node) => pathStatusMap.value[node.node_id]?.status ?? "pending"),
);

const pathPendingCount = computed(() =>
  pathNodeStatusList.value.filter((status) => status === "pending").length,
);

const pathInProgressCount = computed(() =>
  pathNodeStatusList.value.filter((status) => status === "in_progress").length,
);

const pathCompletedCount = computed(() =>
  pathNodeStatusList.value.filter((status) => status === "completed").length,
);

const nextPathNode = computed(() =>
  currentPathNodes.value.find((node) => {
    const status = pathStatusMap.value[node.node_id]?.status ?? "pending";
    return status !== "completed" && status !== "skipped";
  }) ?? currentPathNodes.value[0] ?? null,
);

const pathStatusText = computed(() => {
  if (!currentLearningPath.value) return "未生成";
  const status = String(currentLearningPath.value.lifecycle_status || "active");
  return status === "active" ? "当前生效" : status;
});

const pathSummarySubtitle = computed(() => {
  if (pathLoading.value) return "路径加载中";
  if (!currentLearningPath.value) return "暂无生效路径";
  return `${currentPathNodes.value.length} 个正式路径节点`;
});

const pathSummaryEmptyText = computed(() => {
  if (pathLoading.value) return "学习路径加载中...";
  if (pathError.value) return pathError.value;
  return "暂无已生成学习路径，可到个性化学习路径页按目标生成。";
});

const nextPathNodeTitle = computed(() => nextPathNode.value ? pathNodeTitle(nextPathNode.value) : "暂无待学习节点");

const nextPathNodeMeta = computed(() => {
  const node = nextPathNode.value;
  if (!node) return "路径节点完成后会在这里显示下一步。";
  const status = pathStatusMap.value[node.node_id]?.status ?? "pending";
  return `${pathNodeStatusLabel(status)} · 掌握度 ${formatPercent(node.mastery_score)}`;
});

const nextPathNodeRoute = computed<RouteLocationRaw>(() => {
  const node = nextPathNode.value;
  if (!node) return {path: "/student/learning"};
  return {
    path: "/student/course-content",
    query: {
      node: node.node_id || pathNodeTitle(node),
      title: pathNodeTitle(node),
      continue: "true",
    },
  };
});

const todayPlanTasks = computed(() => {
  const tasks: HomeTask[] = [];

  currentPathNodes.value
    .filter((node) => {
      const status = pathStatusMap.value[node.node_id]?.status ?? "pending";
      return status !== "completed" && status !== "skipped";
    })
    .slice(0, 3)
    .forEach((node) => {
      const status = pathStatusMap.value[node.node_id]?.status ?? "pending";
      tasks.push({
        text: `${status === "in_progress" ? "继续学习" : "学习路径"}：${pathNodeTitle(node)}`,
        done: status === "completed",
        source: "path",
        link: {
          path: "/student/course-content",
          query: {
            node: node.node_id || pathNodeTitle(node),
            title: pathNodeTitle(node),
            continue: "true",
          },
        },
      });
    });

  if (tasks.length < 3) {
    activeInterventionPackages.value.slice(0, 3 - tasks.length).forEach((pkg) => {
      tasks.push({
        text: `完成教师干预任务：${interventionTitle(pkg)}`,
        done: false,
        source: "intervention",
        link: {name: "student-intervention-detail", params: {packageId: pkg.id}},
      });
    });
  }

  if (tasks.length < 3) {
    pendingAssignments.value.slice(0, 3 - tasks.length).forEach((assignment) => {
      tasks.push({
        text: `完成作业：${assignment.title}`,
        done: false,
        source: "homework",
        link: {name: "student-homework-detail", params: {assignmentId: assignment.id}},
      });
    });
  }

  if (tasks.length < 3 && currentPoint.value?.name) {
    tasks.push({
      text: `继续当前知识点：${currentPoint.value.name}`,
      done: false,
      source: "course",
      link: continueLearningRoute.value,
    });
  }

  return tasks;
});

const todayPlanEmptyText = computed(() => {
  if (pathLoading.value || homeworkLoading.value || interventionLoading.value) return "学习任务加载中...";
  if (pathError.value) return pathError.value;
  if (interventionError.value) return interventionError.value;
  if (!currentLearningPath.value) return "暂无已生成学习路径，可到个性化学习路径页生成；首页不会自动生成路径。";
  return "当前没有待处理的路径节点、教师干预任务或作业";
});

const todayPlanActionText = computed(() => {
  if (todayPlanTasks.value[0]?.source === "intervention") return "查看干预任务";
  if (todayPlanTasks.value[0]?.source === "homework") return "查看作业";
  if (todayPlanTasks.value[0]?.source === "course") return "继续课程学习";
  if (!currentLearningPath.value) return "生成学习路径";
  return "继续学习";
});

const todayPlanActionRoute = computed(() => {
  const firstTask = todayPlanTasks.value[0];
  if (firstTask?.link) return firstTask.link;
  if (!currentLearningPath.value) return {path: "/student/learning"};
  return continueLearningRoute.value;
});

const todayPlanCompleted = computed(() => {
  return todayPlanTasks.value.filter(task => task.done).length;
});

const todayPlanTotal = computed(() => {
  return todayPlanTasks.value.length;
});

// 新增：薄弱知识点数据
const weakPoints = computed(() => {
  const twinWeakNodes = diagnosisSummary.value?.weak_nodes ?? [];
  return twinWeakNodes.slice(0, 3).map((node) => {
    const score = Math.round(Number(node.mastery_score ?? 0));
    return {
      name: node.node_id,
      score,
      levelClass: score < 50 ? 'student-home-v2-level-danger' : 'student-home-v2-level-warning',
    };
  });
});

const weakPointsEmptyText = computed(() => {
  if (diagnosisLoading.value) return "画像数据加载中...";
  if (diagnosisError.value) return diagnosisError.value;
  if (!diagnosisSummary.value) return "暂无画像结论，请先完成学习、测验或作业";
  return "暂无明确薄弱知识点";
});

// 新增：通知横幅数据（基于真实待办作业提醒）
const notificationBanner = computed<HomeBanner | null>(() => {
  if (interventionLoading.value || homeworkLoading.value) {
    return null;
  }
  if (activeInterventionPackages.value.length > 0) {
    const pkg = activeInterventionPackages.value[0];
    return {
      icon: 'TASK',
      title: '教师干预任务：',
      message: `${interventionTitle(pkg)}，请按任务包完成学习与练习`,
      link: {name: "student-intervention-detail", params: {packageId: pkg.id}},
      type: 'warning'
    };
  }
  if (assignments.value.length === 0) {
    return null;
  }
  if (pendingAssignments.value.length === 0) return null;

  // 检查是否有即将截止的作业（3天内）
  const now = new Date();
  const threeDaysLater = new Date(now.getTime() + 3 * 24 * 60 * 60 * 1000);
  const urgentAssignments = pendingAssignments.value.filter(a => {
    if (!a.due_at) return false;
    const dueDate = new Date(a.due_at);
    return dueDate <= threeDaysLater && dueDate > now;
  });

  if (urgentAssignments.length > 0) {
    const assignment = urgentAssignments[0];
    const dueDate = new Date(assignment.due_at!);
    const daysLeft = Math.ceil((dueDate.getTime() - now.getTime()) / (24 * 60 * 60 * 1000));
    return {
      icon: 'DUE',
      title: '作业即将截止：',
      message: `${assignment.title}，还有 ${daysLeft} 天截止`,
      link: '/student/homework',
      type: 'warning'
    };
  }

  // 显示最新的未完成作业
  const latestAssignment = pendingAssignments.value[0];
  return {
    icon: 'HW',
    title: '待完成作业：',
    message: `${latestAssignment.title}，请及时完成`,
    link: '/student/homework',
    type: 'info'
  };
});

// 新增：最近通知数据（使用真实数据）
const recentNotifications = computed(() => {
  return notifications.value.slice(0, 2);
});

const notificationsEmptyText = computed(() => {
  if (notificationsLoading.value) return "通知加载中...";
  if (notificationsError.value) return notificationsError.value;
  return "暂无最新通知";
});

// 新增：诊断报告相关计算属性
const diagnosisGeneratedTime = computed(() => {
  if (!diagnosisSummary.value) return '暂无数据';

  const generatedAt = diagnosisSummary.value.generated_at || diagnosisSummary.value.last_updated;
  if (!generatedAt) return '最近更新';

  const date = new Date(generatedAt);
  return date.toLocaleString('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit'
  });
});

const diagnosisRiskLevel = computed(() => {
  if (!diagnosisSummary.value) return { level: 'unknown', text: '待评估', icon: '○', class: 'student-home-v2-diagnosis-risk-unknown' };

  if (diagnosisSummary.value.overall_risk_level) {
    const level = diagnosisSummary.value.overall_risk_level;
    if (level === 'high') {
      return { level: 'high', text: '高风险', icon: '🔴', class: 'student-home-v2-diagnosis-risk-high' };
    }
    if (level === 'medium') {
      return { level: 'medium', text: '中等风险', icon: '⚠️', class: 'student-home-v2-diagnosis-risk-medium' };
    }
    return { level: 'low', text: '低风险', icon: '🟢', class: 'student-home-v2-diagnosis-risk-low' };
  }

  return { level: 'unknown', text: '待评估', icon: '○', class: 'student-home-v2-diagnosis-risk-unknown' };
});

const diagnosisEmptyText = computed(() => {
  if (diagnosisLoading.value) return "画像数据加载中...";
  if (diagnosisError.value) return diagnosisError.value;
  return "暂无画像结论，请先完成学习、测验或作业";
});

const diagnosisWeakNodeCount = computed(() => {
  return diagnosisSummary.value?.weak_nodes?.length ?? 0;
});

const diagnosisStrongNodeCount = computed(() => {
  return diagnosisSummary.value?.node_summary?.strong_node_count ?? 0;
});

const diagnosisTrendText = computed(() => {
  if (!diagnosisSummary.value) return '暂无数据';

  const status = diagnosisSummary.value.trend?.trend_status;
  const mapping: Record<string, string> = {
    upward: '上升',
    stable: '稳定',
    downward: '下降',
  };
  return mapping[status || 'stable'] || '稳定';
});

function nodeFlag(node?: CourseNode | null) {
  return node?.flag ?? "0";
}

function pathPriority(node: LearningPathNode) {
  return node.sequence_order ?? node.llm_priority ?? node.priority ?? 999;
}

function pathNodeTitle(node: LearningPathNode) {
  return String(node.title || node.node_id || "未命名知识点");
}

function pathNodeStatusLabel(status?: string | null) {
  const mapping: Record<string, string> = {
    pending: "待学习",
    in_progress: "学习中",
    completed: "已完成",
    skipped: "暂不执行",
  };
  return mapping[String(status || "pending")] || "待学习";
}

function triggerLabel(value?: string | null) {
  const mapping: Record<string, string> = {
    diagnosis: "诊断生成",
    manual_goal: "学生目标",
    node_completed: "完成后重规划",
    new_course: "新课初始化",
    intervention_completed: "干预完成后调整",
  };
  return mapping[String(value || "diagnosis")] || "学习数据生成";
}

function interventionTitle(pkg: InterventionPackage) {
  const weakNode = pkg.diagnosis?.weak_nodes?.[0]?.node_id;
  return weakNode || pkg.strategy_summary?.slice(0, 24) || `任务包 ${pkg.id}`;
}

function formatPercent(value?: number) {
  return `${Number(value ?? 0).toFixed(1)}%`;
}

function nodeMeta(node: CourseNode, label: string) {
  return `${label} · ${nodeFlag(node) === "1" ? t('student.home.complete') : t('student.home.continue')}`;
}

function computePercent(node: CurrentNodeInfo | null) {
  if (!node || !node.total) return 0;
  return Number(((node.completed / node.total) * 100).toFixed(1));
}

function currentText(node: CurrentNodeInfo | null, label: string) {
  if(!node) return t('student.home.noLearningPosition',{label:label});
  return t('student.home.completeLearningPosition',{label:label,current:node.index+1,total:node.total,completed:node.completed})
}

function selectChapter(chapter: CourseNode) {
  activeChapterKey.value = chapter.name;
  const firstSection = chapter.grandchildren?.[0];
  if (firstSection) {
    activeSectionKey.value = firstSection.name;
    selectedNodeKey.value = firstSection["great-grandchildren"]?.[0]?.name ?? firstSection.name;
  } else {
    activeSectionKey.value = "";
    selectedNodeKey.value = chapter.name;
  }
}

function selectSection(section: CourseNode) {
  activeSectionKey.value = section.name;
  selectedNodeKey.value = section["great-grandchildren"]?.[0]?.name ?? section.name;
}

function selectPoint(point: CourseNode) {
  selectedNodeKey.value = point.name;
}

function focusCurrentTrack() {
  const chapter = chapterNodes.value.find((item) => item.name === currentChapter.value?.name);
  if (!chapter) return;
  activeChapterKey.value = chapter.name;

  const section = (chapter.grandchildren ?? []).find((item) => item.name === currentSection.value?.name);
  if (section) {
    activeSectionKey.value = section.name;
  }

  const point = (section?.["great-grandchildren"] ?? []).find((item) => item.name === currentPoint.value?.name);
  selectedNodeKey.value = point?.name ?? section?.name ?? chapter.name;
}

function resetSelection() {
  collapseToCourse();
}

function handleGraphNodeClick(name: string) {
  const chapter = chapterNodes.value.find((item) => item.name === name);
  if (chapter) {
    selectChapter(chapter);
    return;
  }

  const section = allSections.value.find((item) => item.name === name);
  if (section) {
    const parentChapter = chapterNodes.value.find((chapterItem) => (chapterItem.grandchildren ?? []).some((item) => item.name === name));
    if (parentChapter) {
      activeChapterKey.value = parentChapter.name;
    }
    selectSection(section);
    return;
  }

  const point = allPoints.value.find((item) => item.name === name);
  if (point) {
    const parentChapter = chapterNodes.value.find((chapterItem) =>
        (chapterItem.grandchildren ?? []).some((sectionItem) =>
            (sectionItem["great-grandchildren"] ?? []).some((pointItem) => pointItem.name === name),
        ),
    );
    if (parentChapter) {
      activeChapterKey.value = parentChapter.name;
      const parentSection = (parentChapter.grandchildren ?? []).find((sectionItem) =>
          (sectionItem["great-grandchildren"] ?? []).some((pointItem) => pointItem.name === name),
      );
      if (parentSection) {
        activeSectionKey.value = parentSection.name;
      }
    }
    selectPoint(point);
    return;
  }

  selectedNodeKey.value = name;
}

function collapseToCourse() {
  activeChapterKey.value = "";
  activeSectionKey.value = "";
  selectedNodeKey.value = "";
}

function collapseToChapter() {
  if (!activeChapter.value) {
    collapseToCourse();
    return;
  }
  activeSectionKey.value = "";
  selectedNodeKey.value = activeChapter.value.name;
}

function renderGraphChart() {
  if (!graphChartRef.value || !graphVisualization.value) return;

  graphChart ??= init(graphChartRef.value);
  const rawNodes = graphVisualization.value.mocKgNodeDtoList ?? [];
  const rawRelations = graphVisualization.value.mocKgRelationDtoList ?? [];
  const selectedName = selectedNode.value?.name;
  const currentNames = new Set([currentChapter.value?.name, currentSection.value?.name, currentPoint.value?.name].filter(Boolean));
  const network = buildExpandableGraph(rawRelations);
  const rawNodeByName = new Map(rawNodes.map((node) => [node.nodeName, node]));
  const visibleNodeCount = network.nodes.length;

  graphChart.setOption({
    grid: {left: 0, right: 0, top: 0, bottom: 0},
    tooltip: {
      formatter: (params: { dataType?: string; data?: { name?: string; value?: string } }) => {
        if (params.dataType !== "node") return "";
        const description = params.data?.value ?? "暂无说明";
        // 限制描述长度，超过200字符时截断并添加省略号
        const truncatedDesc = description.length > 200
          ? description.substring(0, 200) + "..."
          : description;
        return `<div style="max-width: 350px; white-space: normal; word-wrap: break-word; line-height: 1.6;">
          <strong style="font-size: 14px; display: block; margin-bottom: 8px;">${params.data?.name ?? ""}</strong>
          <span style="font-size: 13px; color: #64748b; display: block;">${truncatedDesc}</span>
        </div>`;
      },
      backgroundColor: 'rgba(255, 255, 255, 0.95)',
      borderColor: '#e2e8f0',
      borderWidth: 1,
      padding: 12,
      textStyle: {
        color: '#0f172a'
      }
    },
    animationDuration: 300,
    animationDurationUpdate: 240,
    series: [
      {
        type: "graph",
        layout: "force",
        categories: [
          {name: "course"},
          {name: "chapter"},
          {name: "section"},
          {name: "point"},
        ],
        roam: true,
        draggable: true,
        edgeSymbol: ["none", "arrow"],
        edgeSymbolSize: [0, 8],
        force: {
          repulsion: visibleNodeCount > 18 ? 820 : 680,
          gravity: 0.045,
          edgeLength: [125, 220],
          friction: 0.35,
          layoutAnimation: true,
        },
        label: {
          show: true,
          position: "right",
          distance: 6,
          fontSize: 12,
          lineHeight: 15,
          color: "#233044",
          width: 124,
          overflow: "truncate",
          formatter: (params: { name: string }) => formatGraphNodeLabel(params.name),
        },
        lineStyle: {
          color: "rgba(71, 85, 105, 0.26)",
          width: 1.35,
          curveness: 0.12,
        },
        emphasis: {
          focus: "adjacency",
          scale: true,
          lineStyle: {
            width: 2,
            color: "#2563eb",
          },
        },
        data: network.nodes.map((networkNode) => {
          const raw = rawNodeByName.get(networkNode.name);
          const isSelected = networkNode.name === selectedName;
          const isCurrent = currentNames.has(networkNode.name);
          const isDone = String(raw?.flag ?? 0) === "1";
          const layoutNode = networkNode;
          const sizeMap: Record<HomeGraphNodeGroup, number> = {
            course: 0,
            chapter: 66,
            section: 48,
            point: 30,
          };
          const labelSizeMap: Record<HomeGraphNodeGroup, number> = {
            course: 12,
            chapter: 13,
            section: 12,
            point: 11,
          };
          return {
            id: networkNode.name,
            name: networkNode.name,
            value: raw?.description || layoutNode.description || "暂无说明",
            x: networkNode.x,
            y: networkNode.y,
            fixed: false,
            symbol: "circle",
            symbolSize: isSelected || isCurrent ? sizeMap[networkNode.group] + 10 : sizeMap[networkNode.group],
            itemStyle: {
              color: graphNodeColor(networkNode.group, isSelected, isCurrent, isDone),
              borderColor: isCurrent ? "#10b981" : isSelected ? "#2563eb" : graphNodeBorderColor(networkNode.group),
              borderWidth: isCurrent ? 5 : isSelected ? 4 : networkNode.group === "chapter" ? 3 : 2,
              shadowBlur: isSelected || isCurrent ? 24 : networkNode.group === "chapter" ? 14 : 8,
              shadowColor: isSelected ? "rgba(37, 99, 235, 0.24)" : graphNodeShadowColor(networkNode.group),
            },
            label: {
              show: networkNode.group !== "point" || visibleNodeCount <= 28 || isSelected || isCurrent,
              color: isSelected ? "#1d4ed8" : "#334155",
              fontWeight: isSelected || isCurrent ? 700 : 500,
              fontSize: labelSizeMap[networkNode.group],
            },
          };
        }),
        links: network.links,
      },
    ],
  }, true);

  graphChart.off("click");
  graphChart.on("click", (params: any) => {
    if (params.dataType === "node" && params.data?.name) {
      handleGraphNodeClick(params.data.name);
    }
  });

  graphChart.resize();
}

type HomeGraphNodeGroup = "course" | "chapter" | "section" | "point";

type HomeGraphNetworkNode = {
  name: string;
  x: number;
  y: number;
  group: HomeGraphNodeGroup;
  description?: string;
};

type HomeGraphNetworkLink = {
  source: string;
  target: string;
  lineStyle?: Record<string, unknown>;
};

function buildExpandableGraph(relations: GraphVisualizationRelation[]) {
  const nodes: HomeGraphNetworkNode[] = [];
  const links: HomeGraphNetworkLink[] = [];
  const seen = new Set<string>();

  const addNode = (
      node: CourseNode | { name?: string; description?: string } | null | undefined,
      group: HomeGraphNodeGroup,
      x: number,
      y: number,
  ) => {
    if (!node?.name || seen.has(node.name)) return;
    seen.add(node.name);
    nodes.push({name: node.name, description: node.description, group, x, y});
  };

  const addLink = (source?: string, target?: string, subtle = false) => {
    if (!source || !target || source === target) return;
    if (!seen.has(source) || !seen.has(target)) return;
    const key = `${source}->${target}`;
    const reverseKey = `${target}->${source}`;
    if (links.some((item) => `${item.source}->${item.target}` === key || `${item.source}->${item.target}` === reverseKey)) return;
    links.push({
      source,
      target,
      lineStyle: subtle
          ? {opacity: 0.13, width: 0.9, type: "dashed"}
          : {opacity: 0.28, width: 1.25},
    });
  };

  const selectedChapter = activeChapter.value;
  const selectedSectionNode = activeSection.value;
  const chapters = chapterNodes.value;

  if (!activeChapterKey.value) {
    const chapterPositions = radialPositions(chapters.length, 520, 345, 250, -165, 165);
    chapters.forEach((chapter, index) => {
      const position = chapterPositions[index];
      addNode(chapter, "chapter", position.x, position.y);
      if (index > 0) addLink(chapters[index - 1]?.name, chapter.name, true);
    });
  } else if (selectedChapter) {
    addNode(selectedChapter, "chapter", 300, 345);

    const sections = selectedChapter.grandchildren ?? [];
    const sectionPositions = radialPositions(sections.length, selectedSectionNode ? 560 : 620, 345, selectedSectionNode ? 185 : 230, -125, 125);
    sections.forEach((section, index) => {
      const position = sectionPositions[index];
      addNode(section, "section", position.x, position.y);
      addLink(selectedChapter.name, section.name);
    });

    if (selectedSectionNode) {
      const points = selectedSectionNode["great-grandchildren"] ?? [];
      const pointPositions = radialPositions(points.length, 850, 345, 205, -82, 82);
      points.forEach((point, index) => {
        const position = pointPositions[index];
        addNode(point, "point", position.x, position.y);
        addLink(selectedSectionNode.name, point.name);
      });
    }
  }

  addVisibleRelationLinks(relations, nodes, links);
  return {nodes, links};
}

function addVisibleRelationLinks(
    relations: GraphVisualizationRelation[],
    nodes: HomeGraphNetworkNode[],
    links: HomeGraphNetworkLink[],
) {
  if (!relations.length) return;
  const rawNodeById = new Map((graphVisualization.value?.mocKgNodeDtoList ?? []).map((node) => [node.id, node]));
  const visibleNames = new Set(nodes.map((node) => node.name));
  const existing = new Set(links.map((link) => `${link.source}->${link.target}`));
  let relationCount = 0;

  for (const relation of relations) {
    if (relationCount >= 12) return;
    const source = rawNodeById.get(relation.fromNodeId)?.nodeName;
    const target = rawNodeById.get(relation.toNodeId)?.nodeName;
    if (!source || !target || source === target) continue;
    if (!visibleNames.has(source) || !visibleNames.has(target)) continue;
    const key = `${source}->${target}`;
    const reverseKey = `${target}->${source}`;
    if (existing.has(key) || existing.has(reverseKey)) continue;
    links.push({
      source,
      target,
      lineStyle: {opacity: 0.12, width: 0.9, type: "dashed"},
    });
    existing.add(key);
    relationCount += 1;
  }
}

function radialPositions(count: number, centerX: number, centerY: number, radius: number, startAngle = -140, endAngle = 140) {
  if (count <= 0) return [];
  if (count === 1) return [{x: centerX, y: centerY}];
  const step = (endAngle - startAngle) / Math.max(count - 1, 1);
  return Array.from({length: count}, (_item, index) => {
    const angle = ((startAngle + step * index) * Math.PI) / 180;
    return {
      x: centerX + Math.cos(angle) * radius,
      y: centerY + Math.sin(angle) * radius,
    };
  });
}

function graphNodeColor(group: HomeGraphNodeGroup, isSelected: boolean, isCurrent: boolean, isDone: boolean) {
  if (isSelected) return "#2563eb";
  if (isCurrent) return "#dcfce7";
  if (isDone) return "#e0f2fe";
  const colorMap: Record<HomeGraphNodeGroup, string> = {
    course: "#ffffff",
    chapter: "#10b981",
    section: "#60a5fa",
    point: "#f8fafc",
  };
  return colorMap[group];
}

function graphNodeBorderColor(group: HomeGraphNodeGroup) {
  const colorMap: Record<HomeGraphNodeGroup, string> = {
    course: "#ffffff",
    chapter: "#059669",
    section: "#2563eb",
    point: "#94a3b8",
  };
  return colorMap[group];
}

function graphNodeShadowColor(group: HomeGraphNodeGroup) {
  const colorMap: Record<HomeGraphNodeGroup, string> = {
    course: "rgba(15, 23, 42, 0)",
    chapter: "rgba(16, 185, 129, 0.24)",
    section: "rgba(37, 99, 235, 0.18)",
    point: "rgba(15, 23, 42, 0.08)",
  };
  return colorMap[group];
}

function formatGraphNodeLabel(name: string) {
  if (!name) return "";
  return name.length > 12 ? `${name.slice(0, 12)}...` : name;
}

function handleResize() {
  graphChart?.resize();
}

function safeRenderGraph() {
  try {
    renderGraphChart();
  } catch (err) {
    console.error("HomeView graph render failed:", err);
    error.value = err instanceof Error ? err.message : "首页知识图谱渲染失败";
  }
}

function findCurrentNodes(graphData: { children?: CourseNode[] }, progressData?: LearningProgressResponse | null) {
  let foundChapter: CurrentNodeInfo | null = null;
  let foundSection: CurrentNodeInfo | null = null;
  let foundPoint: CurrentNodeInfo | null = null;
  const children = graphData.children ?? [];

  // 使用 progress API 返回的真实完成数量
  const completedChapters = progressData?.chapters?.completed ?? 0;
  const completedSections = progressData?.sections?.completed ?? 0;
  const completedPoints = progressData?.points?.completed ?? 0;

  for (let i = 0; i < children.length; i += 1) {
    const chapter = children[i];
    if (!foundChapter && chapter.flag === "0") {
      foundChapter = {name: chapter.name, index: i, total: children.length, completed: completedChapters};
    }

    const sections = chapter.grandchildren ?? [];
    for (let j = 0; j < sections.length; j += 1) {
      const section = sections[j];
      if (!foundSection && section.flag === "0" && (!foundChapter || foundChapter.index === i)) {
        foundSection = {name: section.name, index: j, total: sections.length, completed: completedSections};
      }

      const points = section["great-grandchildren"] ?? [];
      for (let k = 0; k < points.length; k += 1) {
        const point = points[k];
        if (!foundPoint && point.flag === "0" && (!foundSection || foundSection.index === j)) {
          foundPoint = {name: point.name, index: k, total: points.length, completed: completedPoints};
          break;
        }
      }

      if (foundPoint) break;
    }

    if (foundPoint) break;
  }

  if (!foundChapter && children.length) {
    foundChapter = {name: children[0].name, index: 0, total: children.length, completed: completedChapters};
  }

  if (!foundSection && foundChapter) {
    const chapter = children[foundChapter.index];
    const firstSection = chapter?.grandchildren?.[0];
    if (firstSection) {
      foundSection = {name: firstSection.name, index: 0, total: chapter.grandchildren?.length ?? 0, completed: completedSections};
    }
  }

  if (!foundPoint && foundSection && foundChapter) {
    const chapter = children[foundChapter.index];
    const section = chapter?.grandchildren?.[foundSection.index];
    const firstPoint = section?.["great-grandchildren"]?.[0];
    if (firstPoint) {
      foundPoint = {name: firstPoint.name, index: 0, total: section["great-grandchildren"]?.length ?? 0, completed: completedPoints};
    }
  }

  return {currentChapter: foundChapter, currentSection: foundSection, currentPoint: foundPoint};
}

async function loadHome() {
  loading.value = true;
  error.value = "";
  try {
    const [knowledgeGraph, visualGraph, learningProgress, user] = await Promise.all([
      fetchKnowledgeGraph(),
      fetchGraphVisualization(),
      fetchLearningProgress(),
      fetchCurrentUser().catch(() => null),
    ]);

    graph.value = knowledgeGraph;
    graphVisualization.value = visualGraph;
    progress.value = learningProgress;
    currentUser.value = user;

    const currentNodes = findCurrentNodes(knowledgeGraph, learningProgress);
    currentChapter.value = currentNodes.currentChapter;
    currentSection.value = currentNodes.currentSection;
    currentPoint.value = currentNodes.currentPoint;

    focusCurrentTrack();
    if (!selectedNodeKey.value) {
      resetSelection();
    }

    // 加载作业数据（不阻塞主流程）
    loadHomeworkData().catch(err => {
      console.warn('作业数据加载失败:', err);
    });

    // 加载学习连续天数（不阻塞主流程）
    loadLearningStreak().catch(err => {
      console.warn('学习连续天数加载失败:', err);
    });

    // 加载通知数据（不阻塞主流程）
    loadNotifications().catch(err => {
      console.warn('通知数据加载失败:', err);
    });

    // 加载教师已下发干预任务（不阻塞主流程）
    loadInterventionPackages().catch(err => {
      console.warn('干预任务加载失败:', err);
    });

    // 加载诊断数据（不阻塞主流程）
    loadDiagnosisSummary().catch(err => {
      console.warn('诊断数据加载失败:', err);
    });

    // 加载学生已生成的个性化学习路径（不自动生成，避免首页产生隐式状态变更）
    loadCurrentLearningPath().catch(err => {
      console.warn('个性化学习路径加载失败:', err);
    });
  } catch (err) {
    error.value = err instanceof Error ? err.message : "学习首页加载失败";
  } finally {
    loading.value = false;
    await nextTick();
    safeRenderGraph();
  }
}

async function loadHomeworkData() {
  homeworkLoading.value = true;
  try {
    const [assignmentsRes, submissionsRes] = await Promise.all([
      homeworkListAssignmentsByFilter({ only_mine: false }),
      homeworkListMySubmissions(),
    ]);
    assignments.value = assignmentsRes.assignments || [];
    mySubmissions.value = submissionsRes.submissions || [];
  } catch (err) {
    console.error('作业数据加载失败:', err);
    assignments.value = [];
    mySubmissions.value = [];
  } finally {
    homeworkLoading.value = false;
  }
}

async function loadLearningStreak() {
  streakLoading.value = true;
  try {
    learningStreakData.value = await fetchLearningStreak();
  } catch (err) {
    console.error('学习连续天数加载失败:', err);
    learningStreakData.value = null;
  } finally {
    streakLoading.value = false;
  }
}

async function loadNotifications() {
  notificationsLoading.value = true;
  notificationsError.value = "";
  try {
    const response = await fetchRecentNotifications(10);
    notifications.value = response.notifications || [];
  } catch (err) {
    console.error('通知数据加载失败:', err);
    notifications.value = [];
    notificationsError.value = "通知数据暂不可用";
  } finally {
    notificationsLoading.value = false;
  }
}

async function loadInterventionPackages() {
  interventionLoading.value = true;
  interventionError.value = "";
  try {
    const response = await interventionStudentPackages();
    interventionPackages.value = response.packages || [];
  } catch (err) {
    console.error('干预任务加载失败:', err);
    interventionPackages.value = [];
    interventionError.value = "教师干预任务暂不可用";
  } finally {
    interventionLoading.value = false;
  }
}

async function loadDiagnosisSummary() {
  if (!currentUser.value?.username) return;

  diagnosisLoading.value = true;
  diagnosisError.value = "";
  try {
    diagnosisSummary.value = await fetchStudentTwin(currentUser.value.username);
  } catch (err) {
    console.error('诊断数据加载失败:', err);
    diagnosisSummary.value = null;
    diagnosisError.value = "诊断数据暂不可用";
  } finally {
    diagnosisLoading.value = false;
  }
}

async function loadCurrentLearningPath() {
  if (!currentUser.value?.username) return;

  pathLoading.value = true;
  pathError.value = "";
  try {
    currentLearningPath.value = await fetchCurrentLearningPath(currentUser.value.username);
  } catch (err) {
    currentLearningPath.value = null;
    const message = err instanceof Error ? err.message : "";
    if (!message.includes("No learning path found")) {
      console.error('个性化学习路径加载失败:', err);
      pathError.value = "个性化学习路径暂不可用";
    }
  } finally {
    pathLoading.value = false;
  }
}

watch([selectedNodeKey, activeChapterKey, activeSectionKey], async () => {
  await nextTick();
  safeRenderGraph();
});

onMounted(async () => {
  await loadHome();
  window.addEventListener("resize", handleResize);
});

onBeforeUnmount(() => {
  window.removeEventListener("resize", handleResize);
  graphChart?.dispose();
  graphChart = null;
});
</script>
