<template>
  <div class="home-shell">
    <!-- 新增：首页欢迎横幅 -->
    <div class="student-home-v2-hero">
      <div class="student-home-v2-hero-content">
        <h1 class="student-home-v2-hero-title">你好，{{ displayName }} 👋</h1>
        <p class="student-home-v2-hero-subtitle">今天也要加油学习哦！</p>
      </div>
      <div class="student-home-v2-hero-stats">
        <div class="student-home-v2-stat-item">
          <div class="student-home-v2-stat-icon">📊</div>
          <div class="student-home-v2-stat-info">
            <div class="student-home-v2-stat-number">{{ overallMasteryPercent }}%</div>
            <div class="student-home-v2-stat-text">总体掌握度</div>
          </div>
        </div>
        <div class="student-home-v2-stat-item">
          <div class="student-home-v2-stat-icon">✅</div>
          <div class="student-home-v2-stat-info">
            <div class="student-home-v2-stat-number">{{ completedPointsCount }}</div>
            <div class="student-home-v2-stat-text">已完成知识点</div>
          </div>
        </div>
        <div class="student-home-v2-stat-item">
          <div class="student-home-v2-stat-icon">📝</div>
          <div class="student-home-v2-stat-info">
            <div class="student-home-v2-stat-number">{{ pendingHomeworkCount }}</div>
            <div class="student-home-v2-stat-text">待完成作业</div>
          </div>
        </div>
        <div class="student-home-v2-stat-item">
          <div class="student-home-v2-stat-icon">🔥</div>
          <div class="student-home-v2-stat-info">
            <div class="student-home-v2-stat-number">{{ consecutiveDays }}天</div>
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
              <div v-for="(task, index) in todayPlanTasks" :key="index" 
                   class="student-home-v2-plan-task" 
                   :class="{ 'student-home-v2-plan-task-done': task.done }">
                <div class="student-home-v2-task-check">{{ task.done ? '✓' : '○' }}</div>
                <div class="student-home-v2-task-text">{{ task.text }}</div>
              </div>
            </div>
            <RouterLink :to="continueLearningRoute" class="student-home-v2-card-action-btn">
              <span>继续学习</span>
              <span>→</span>
            </RouterLink>
          </article>

          <!-- 需要加强 -->
          <article class="card-panel student-home-v2-weak-card">
            <div class="section-head">
              <h2>⚠️ 需要加强</h2>
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
            </div>
          </article>

          <!-- 最近通知 -->
          <article class="card-panel student-home-v2-notification-card">
            <div class="section-head">
              <h2>🔔 最近通知</h2>
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
            <div class="home-root-card">
              <div>
                <div class="home-root-kicker">{{$t('student.home.courseOverview')}}</div>
                <h3>{{ graph?.name || $t('student.home.currentCourse') }}</h3>
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

        <!-- 右栏：最新诊断报告 + 当前学习定位 + 知识点详情 + 下一步操作 -->
        <aside class="student-home-v2-right-column">
          <!-- 最新诊断报告 -->
          <article v-if="diagnosisSummary" class="card-panel student-home-v2-diagnosis-card">
            <div class="section-head">
              <h2>🔍 最新诊断报告</h2>
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
import {RouterLink} from "vue-router";
import MetricStatCard from "../../components/ui/MetricStatCard.vue";
import PageHero from "../../components/ui/PageHero.vue";
import {type ECharts, init} from "../../lib/echarts";
import {GraphVisualizationResponse, LearningProgressResponse, GraphVisualizationNode} from "../../types/student";
import {fetchLearningProgress, fetchGraphVisualization, fetchStudentTwin} from '../../api/student';
import {type CourseNode,type CurrentNodeInfo} from "../../types/knowledgeGraph";
import {fetchKnowledgeGraph} from "../../api/knowledgeGraph";
import {fetchCurrentUser} from "../../api/login";
import {homeworkListAssignmentsByFilter, homeworkListMySubmissions} from "../../api/homework";
import {fetchLearningStreak} from "../../api/learningStreak";
import {fetchRecentNotifications, type Notification} from "../../api/notification";
import type {HomeworkAssignment, HomeworkSubmission} from "../../types/homework";
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

// 诊断数据
const diagnosisSummary = ref<StudentTwinSummary | null>(null);
const diagnosisLoading = ref(false);

const activeChapterKey = ref("");
const activeSectionKey = ref("");
const selectedNodeKey = ref("");

const currentChapter = ref<CurrentNodeInfo | null>(null);
const currentSection = ref<CurrentNodeInfo | null>(null);
const currentPoint = ref<CurrentNodeInfo | null>(null);

const graphChartRef = ref<HTMLDivElement | null>(null);
let graphChart: ECharts | null = null;

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
        activeSection.value ??
        activeChapter.value ??
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
  if (allSections.value.some((item) => item.name === selectedNode.value?.name)) return t('studetn.home.section');
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
  const nodes = graphVisualization.value?.mocKgNodeDtoList ?? [];
  if (nodes.length === 0) return 0;
  const totalMastery = nodes.reduce((sum, node) => sum + (node.mocKgNodeAvgStatisticsDto?.avgMasteryRate ?? 0), 0);
  return Math.round(totalMastery / nodes.length);
});

const completedPointsCount = computed(() => {
  return allPoints.value.filter(point => nodeFlag(point) === "1").length;
});

const pendingHomeworkCount = computed(() => {
  // 从作业列表中筛选出未提交的作业
  if (assignments.value.length === 0) return 0;
  
  const submittedIds = new Set(mySubmissions.value.map(s => s.assignment_id));
  const pendingAssignments = assignments.value.filter(a => !submittedIds.has(a.id));
  
  return pendingAssignments.length;
});

const consecutiveDays = computed(() => {
  // 使用真实的学习连续天数
  return learningStreakData.value?.current_streak ?? 0;
});

// 新增：今日计划数据
const todayPlanTasks = computed(() => {
  // 使用安全 fallback 静态数据
  const currentChapterName = currentChapter.value?.name || '';
  const currentSectionName = currentSection.value?.name || '';
  const currentPointName = currentPoint.value?.name || '';
  
  return [
    { text: currentChapterName ? `学习 ${currentChapterName}` : '开始今日学习', done: true },
    { text: currentSectionName ? `复习 ${currentSectionName}` : '复习已学内容', done: true },
    { text: currentPointName ? `掌握 ${currentPointName}` : '完成知识点学习', done: false },
    { text: '完成课后练习', done: false },
    { text: '提交今日作业', done: false },
  ];
});

const todayPlanCompleted = computed(() => {
  return todayPlanTasks.value.filter(task => task.done).length;
});

const todayPlanTotal = computed(() => {
  return todayPlanTasks.value.length;
});

// 新增：薄弱知识点数据
const weakPoints = computed(() => {
  const nodes = graphVisualization.value?.mocKgNodeDtoList ?? [];
  
  // 筛选出掌握度较低的知识点（小于60%）
  const weakNodes = nodes
    .filter(node => {
      const mastery = node.mocKgNodeAvgStatisticsDto?.avgMasteryRate ?? 0;
      return mastery > 0 && mastery < 60;
    })
    .sort((a, b) => {
      const masteryA = a.mocKgNodeAvgStatisticsDto?.avgMasteryRate ?? 0;
      const masteryB = b.mocKgNodeAvgStatisticsDto?.avgMasteryRate ?? 0;
      return masteryA - masteryB;
    })
    .slice(0, 3);
  
  // 如果没有薄弱知识点，使用 fallback
  if (weakNodes.length === 0) {
    return [
      { name: '暂无薄弱知识点', score: 100, levelClass: 'student-home-v2-level-good' },
    ];
  }
  
  return weakNodes.map(node => {
    const score = Math.round(node.mocKgNodeAvgStatisticsDto?.avgMasteryRate ?? 0);
    let levelClass = 'student-home-v2-level-good';
    if (score < 50) {
      levelClass = 'student-home-v2-level-danger';
    } else if (score < 60) {
      levelClass = 'student-home-v2-level-warning';
    }
    return {
      name: node.nodeName,
      score,
      levelClass,
    };
  });
});

// 新增：通知横幅数据（基于作业动态生成）
const notificationBanner = computed(() => {
  if (homeworkLoading.value || assignments.value.length === 0) {
    return null;
  }
  
  const submittedIds = new Set(mySubmissions.value.map(s => s.assignment_id));
  const pendingAssignments = assignments.value.filter(a => !submittedIds.has(a.id));
  
  if (pendingAssignments.length === 0) {
    return {
      icon: '🎉',
      title: '太棒了！',
      message: '当前没有待完成的作业，继续保持学习节奏！',
      link: '/student/homework',
      type: 'success'
    };
  }
  
  // 检查是否有即将截止的作业（3天内）
  const now = new Date();
  const threeDaysLater = new Date(now.getTime() + 3 * 24 * 60 * 60 * 1000);
  const urgentAssignments = pendingAssignments.filter(a => {
    if (!a.due_at) return false;
    const dueDate = new Date(a.due_at);
    return dueDate <= threeDaysLater && dueDate > now;
  });
  
  if (urgentAssignments.length > 0) {
    const assignment = urgentAssignments[0];
    const dueDate = new Date(assignment.due_at!);
    const daysLeft = Math.ceil((dueDate.getTime() - now.getTime()) / (24 * 60 * 60 * 1000));
    return {
      icon: '⚠️',
      title: '作业即将截止：',
      message: `${assignment.title}，还有 ${daysLeft} 天截止`,
      link: '/student/homework',
      type: 'warning'
    };
  }
  
  // 显示最新的未完成作业
  const latestAssignment = pendingAssignments[0];
  return {
    icon: '📝',
    title: '老师布置了新作业：',
    message: `${latestAssignment.title}，请及时完成`,
    link: '/student/homework',
    type: 'info'
  };
});

// 新增：最近通知数据（使用真实数据）
const recentNotifications = computed(() => {
  // 如果有真实通知数据，使用真实数据
  if (notifications.value.length > 0) {
    return notifications.value.slice(0, 2); // 只显示最近2条
  }
  
  // fallback：使用静态数据
  return [
    { icon: '📝', title: '学习计划提醒', time: '5小时前', link: '/student/home' },
    { icon: '🎉', title: '测验成绩公布：92分', time: '1天前', link: '/student/home' },
  ];
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
  if (!diagnosisSummary.value) return { level: 'low', text: '低风险', icon: '🟢', class: 'student-home-v2-diagnosis-risk-low' };
  
  // 优先使用后端返回的整体风险等级
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
  
  // fallback：根据 risk_alerts 推断
  const alerts = diagnosisSummary.value.risk_alerts || [];
  if (alerts.some(r => r.level === 'high')) {
    return { level: 'high', text: '高风险', icon: '🔴', class: 'student-home-v2-diagnosis-risk-high' };
  }
  if (alerts.some(r => r.level === 'medium')) {
    return { level: 'medium', text: '中等风险', icon: '⚠️', class: 'student-home-v2-diagnosis-risk-medium' };
  }
  return { level: 'low', text: '低风险', icon: '🟢', class: 'student-home-v2-diagnosis-risk-low' };
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
  selectedNodeKey.value = graph.value?.name ?? "";
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
  const rawLinks = graphVisualization.value.mocKgRelationDtoList ?? [];
  const selectedName = selectedNode.value?.name;
  const currentNames = new Set([currentChapter.value?.name, currentSection.value?.name, currentPoint.value?.name].filter(Boolean));
  const visibleNames = getProgressiveVisibleNodeNames();

  const filteredNodes = rawNodes.filter((node) => visibleNames.has(node.nodeName));
  const visibleIds = new Set(filteredNodes.map((node) => String(node.id)));
  const filteredLinks = rawLinks.filter(
      (item) => visibleIds.has(String(item.fromNodeId)) && visibleIds.has(String(item.toNodeId)),
  );

  graphChart.setOption({
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
        roam: true,
        draggable: true,
        force: {
          repulsion: 210,
          edgeLength: 95,
          gravity: 0.08,
          friction: 0.08,
        },
        label: {
          show: true,
          position: "right",
          fontSize: 11,
          color: "#334155",
          formatter: "{b}",
        },
        lineStyle: {
          color: "rgba(148, 163, 184, 0.4)",
          width: 1.2,
          curveness: 0.08,
        },
        emphasis: {
          focus: "adjacency",
          scale: true,
          lineStyle: {
            width: 2,
            color: "#2563eb",
          },
        },
        data: filteredNodes.map((node) => {
          const isSelected = node.nodeName === selectedName;
          const isCurrent = currentNames.has(node.nodeName);
          const isDone = String(node.flag ?? 0) === "1";
          const level = Number(node.level ?? 0);
          return {
            id: String(node.id),
            name: node.nodeName,
            value: node.description || "暂无说明",
            symbolSize: Math.max(22, 60 - level * 6),
            itemStyle: {
              color: isSelected ? "#2563eb" : isDone ? "#dbeafe" : "#ffffff",
              borderColor: isCurrent ? "#10b981" : isSelected ? "#2563eb" : "#94a3b8",
              borderWidth: isCurrent ? 4 : 2,
              shadowBlur: isSelected || isCurrent ? 18 : 8,
              shadowColor: isSelected ? "rgba(37, 99, 235, 0.22)" : "rgba(15, 23, 42, 0.08)",
            },
            label: {
              show: true,
            },
          };
        }),
        links: filteredLinks.map((item) => ({
          source: String(item.fromNodeId),
          target: String(item.toNodeId),
        })),
      },
    ],
  });

  graphChart.off("click");
  graphChart.on("click", (params: any) => {
    if (params.dataType === "node" && params.data?.name) {
      handleGraphNodeClick(params.data.name);
    }
  });

  graphChart.resize();
}

function getProgressiveVisibleNodeNames() {
  const names = new Set<string>();
  const rootName = graph.value?.name;
  if (rootName) {
    names.add(rootName);
  }

  const selectedChapter = activeChapter.value;
  const selectedSectionNode = activeSection.value;

  for (const chapter of chapterNodes.value) {
    names.add(chapter.name);
  }

  if (selectedChapter) {
    names.add(selectedChapter.name);
    for (const section of selectedChapter.grandchildren ?? []) {
      names.add(section.name);
    }
  }

  if (selectedSectionNode) {
    names.add(selectedSectionNode.name);
    for (const point of selectedSectionNode["great-grandchildren"] ?? []) {
      names.add(point.name);
    }
  }

  return names;
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
    
    // 加载诊断数据（不阻塞主流程）
    loadDiagnosisSummary().catch(err => {
      console.warn('诊断数据加载失败:', err);
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
  try {
    const response = await fetchRecentNotifications(10);
    notifications.value = response.notifications || [];
  } catch (err) {
    console.error('通知数据加载失败:', err);
    notifications.value = [];
  } finally {
    notificationsLoading.value = false;
  }
}

async function loadDiagnosisSummary() {
  if (!currentUser.value?.username) return;
  
  diagnosisLoading.value = true;
  try {
    diagnosisSummary.value = await fetchStudentTwin(currentUser.value.username);
  } catch (err) {
    console.error('诊断数据加载失败:', err);
    diagnosisSummary.value = null;
  } finally {
    diagnosisLoading.value = false;
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
