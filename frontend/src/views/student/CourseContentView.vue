<template>
  <div class="course-shell">
    <!-- 页面头部 -->
    <div class="student-learning-v2-header">
      <div>
        <h1>📚 学习中心</h1>
        <p class="student-learning-v2-desc">按知识点查看教师绑定的 B站、YouTube、CSDN 与课程资料</p>
      </div>
    </div>

    <!-- 三栏布局 -->
    <section class="student-learning-v2-course-context">
      <div class="student-learning-v2-course-copy">
        <span class="course-context-label">当前课程</span>
        <h2>{{ currentCourseName || "请选择课程" }}</h2>
        <p v-if="currentCourseDescription">{{ currentCourseDescription }}</p>
        <p v-else>学习内容按课程组织，切换课程后目录、作业、资源和学习记录会同步刷新。</p>
      </div>
      <div class="student-learning-v2-course-actions">
        <label class="course-select-label" for="student-course-select">课程</label>
        <select
          id="student-course-select"
          v-model="currentCourseId"
          class="student-learning-v2-course-select"
          :disabled="coursesLoading || !studentCourses.length"
          @change="handleCourseChange"
        >
          <option v-if="!studentCourses.length" value="">暂无可学习课程</option>
          <option v-for="course in studentCourses" :key="course.course_id" :value="course.course_id">
            {{ course.course_name || course.course_id }}
          </option>
        </select>
        <div v-if="coursesLoading" class="course-context-hint">正在读取课程...</div>
        <div v-else-if="coursesError" class="course-context-hint error-state">{{ coursesError }}</div>
        <div v-else class="course-context-stats">
          <span>知识点 {{ selectedCourse?.node_count ?? selectableNodes.length }}</span>
          <span>资源 {{ selectedCourse?.resource_count ?? visibleResourceCards.length }}</span>
        </div>
      </div>
    </section>

    <section class="student-learning-v2-layout">
      <!-- 左栏：课程目录 -->
      <aside class="student-learning-v2-left-panel">
        <div class="student-learning-v2-toc-header">
          <h2>课程目录</h2>
          <span class="muted">按章节浏览知识点</span>
        </div>
        <div v-if="graphLoading" class="state-card">正在加载课程目录...</div>
        <div v-else-if="graphError" class="state-card error-state">{{ graphError }}</div>
        <ul v-else class="toc-root">
          <li v-for="chapter in chapterNodes" :key="chapter.name" class="toc-chapter">
            <button type="button" class="toc-chapter-btn" @click="toggleChapter(chapter.name)">
              <span class="toc-arrow">{{ isChapterOpen(chapter.name) ? "▾" : "▸" }}</span>
              <span>{{ chapter.name }}</span>
            </button>
            <ul v-show="isChapterOpen(chapter.name)" class="toc-section-list">
              <li v-for="section in sectionNodes(chapter)" :key="section.name" class="toc-section">
                <button
                  type="button"
                  class="toc-item"
                  :class="{ active: currentNode?.name === section.name, group: !isSelectableNode(section) }"
                  @click="handleSectionClick(section)"
                >
                  <span v-if="knowledgeNodes(section).length" class="toc-arrow">{{ isSectionOpen(section.name) ? "▾" : "▸" }}</span>
                  <span class="toc-item-text">{{ section.name }}</span>
                  <span class="toc-resource-badge muted">{{ sectionResourceLabel(section) }}</span>
                  <span v-if="getNodeFlag(section)" class="toc-item-flag">{{ getNodeFlag(section) }}</span>
                </button>
                <ul v-if="knowledgeNodes(section).length" v-show="isSectionOpen(section.name)" class="toc-knowledge-list">
                  <li v-for="node in knowledgeNodes(section)" :key="node.name">
                    <button
                      type="button"
                      class="toc-subitem"
                      :class="{ active: currentNode?.name === node.name }"
                      @click="selectNode(node)"
                    >
                      <span class="toc-item-text">{{ node.name }}</span>
                      <span class="toc-resource-badge">{{ resourceBadgeText(node) }}</span>
                      <span v-if="getNodeFlag(node)" class="toc-item-flag">{{ getNodeFlag(node) }}</span>
                    </button>
                  </li>
                </ul>
              </li>
            </ul>
          </li>
        </ul>
      </aside>

      <!-- 中栏：内容查看器 -->
      <section class="student-learning-v2-center-panel">
        <!-- 欢迎状态 -->
        <div v-if="!currentNode" class="student-learning-v2-welcome">
          <div class="student-learning-v2-welcome-icon">📖</div>
          <h2>选择一个章节开始学习</h2>
          <p>左侧目录用于浏览课程知识点，中间区域展示资源，右侧可以直接和 AI 助教对话。</p>
            
            <!-- 课程作业 -->
            <div class="student-learning-v2-homework-section">
              <div class="student-learning-v2-section-title">
                <strong>本课程作业</strong>
                <button type="button" class="ghost-btn small" @click="goHomeworkForCourse">查看全部</button>
              </div>
              <div v-if="courseHomeworkLoading" class="muted">加载中...</div>
              <div v-else-if="courseHomeworkError" class="muted">{{ courseHomeworkError }}</div>
              <div v-else-if="!courseHomework.length" class="muted">当前课程暂无已发布作业</div>
              <ul v-else class="student-learning-v2-homework-list">
                <li v-for="item in courseHomework" :key="item.id" class="student-learning-v2-homework-item">
                  <div>
                    <strong>{{ item.title }}</strong>
                    <div class="muted">{{ item.assignment_type }} · 章节 {{ item.node_name || "未关联" }} · 截止 {{ item.due_at ? new Date(item.due_at).toLocaleString() : "未设置" }}</div>
                  </div>
                  <button type="button" class="ghost-btn small" @click="goHomeworkDetail(item.id)">去提交</button>
                </li>
              </ul>
            </div>
        </div>
        
        <!-- 当前学习节点 -->
        <div v-else>
            <!-- 内容头部 -->
            <div class="student-learning-v2-content-header">
              <div class="student-learning-v2-breadcrumb">
                <span>{{ currentCourseName }}</span>
                <span class="sep">›</span>
                <span>{{ currentChapterName }}</span>
                <span class="sep">›</span>
                <span class="current">{{ currentNode.name }}</span>
              </div>
              <div class="student-learning-v2-content-tools">
                <button
                  type="button"
                  class="student-learning-v2-tool-btn"
                  title="上一个知识点"
                  :disabled="!canNavigatePrev"
                  @click="navigatePrevNode"
                >
                  ◀
                </button>
                <button
                  type="button"
                  class="student-learning-v2-tool-btn"
                  title="下一个知识点"
                  :disabled="!canNavigateNext"
                  @click="navigateNextNode"
                >
                  ▶
                </button>
                <button
                  type="button"
                  class="student-learning-v2-tool-btn"
                  :class="{ active: isBookmarked }"
                  :title="isBookmarked ? '取消收藏' : '收藏当前知识点'"
                  @click="toggleBookmark"
                >
                  {{ isBookmarked ? "★" : "☆" }}
                </button>
                <button
                  type="button"
                  class="student-learning-v2-tool-btn"
                  :class="{ active: hasCurrentNote }"
                  title="学习笔记"
                  @click="openNotes"
                >
                  📝
                </button>
              </div>
            </div>
            <div v-if="toolMessage" class="student-learning-v2-tool-message">{{ toolMessage }}</div>

            <!-- Viewer Tabs -->
            <div class="student-learning-v2-viewer-tabs">
              <button
                v-for="tab in resourceViewerTabs"
                :key="tab.key"
                type="button"
                class="student-learning-v2-viewer-tab"
                :class="{ active: activeViewerTab === tab.key }"
                @click="switchViewerTab(tab.key)"
              >
                {{ tab.label }}
                <span class="student-learning-v2-viewer-tab-count">{{ tab.count }}</span>
              </button>
              <button
                type="button"
                class="student-learning-v2-viewer-tab"
                :class="{ active: activeViewerTab === 'quiz' }"
                @click="switchViewerTab('quiz')"
              >
                📝 在线测验
              </button>
              <button
                type="button"
                class="student-learning-v2-viewer-tab"
                :class="{ active: activeViewerTab === 'summary' }"
                @click="switchViewerTab('summary')"
              >
                📋 知识总结
              </button>
            </div>

            <!-- 分类学习资源面板 -->
            <div v-if="isResourceCategoryTab(activeViewerTab)" class="student-learning-v2-viewer-panel">
              <div v-if="nodeLoading" class="student-learning-v2-viewer-empty">
                <div class="empty-icon">...</div>
                <p>正在加载当前知识点资源...</p>
              </div>
              <div v-else-if="nodeResourceError" class="student-learning-v2-viewer-empty error-state">
                <div class="empty-icon">!</div>
                <p>{{ nodeResourceError }}</p>
              </div>
              <div v-else-if="!activeCategoryResourceCards.length" class="student-learning-v2-viewer-empty">
                <div class="empty-icon">R</div>
                <p>当前知识点暂无{{ activeResourceTabLabel }}资源</p>
              </div>
              <div v-else class="student-learning-v2-resource-category-panel">
                <article
                  v-for="(resource, resourceIndex) in activeCategoryResourceCards"
                  :key="resource.url"
                  class="student-learning-v2-resource-display-card"
                  :class="{ embedded: resource.embedUrl || resource.kind === 'document' }"
                >
                  <div class="student-learning-v2-resource-display-head">
                    <div>
                      <span class="student-learning-v2-bound-provider">{{ resource.providerLabel }}</span>
                      <h3>{{ resource.title }}</h3>
                    </div>
                    <span class="student-learning-v2-bound-kind">{{ resource.kindLabel }}</span>
                  </div>
                  <TrackedResourceFrame
                    v-if="resource.embedUrl"
                    :course-id="currentCourseId || 'course_big_data'"
                    :node-id="currentTrackingNodeId"
                    :node-name="currentNode?.name || ''"
                    :resource-url="resource.url"
                    :resource-index="resourceIndex"
                    :provider="resource.provider"
                    :embed-url="resource.embedUrl"
                    :title="resource.title"
                    source="student_course_content"
                    frame-class="student-learning-v2-video-embed"
                  />
                  <iframe
                    v-else-if="resource.kind === 'document'"
                    class="student-learning-v2-resource-frame compact"
                    :src="documentViewerUrl(resource)"
                    :title="resource.title"
                    @load="recordResourceClick(resource)"
                  />
                  <p v-else>{{ resource.description }}</p>
                  <div class="student-learning-v2-bound-actions">
                    <a
                      v-if="resource.external"
                      :href="resource.url"
                      target="_blank"
                      rel="noopener noreferrer"
                      @click="recordResourceClick(resource)"
                    >
                      打开资源
                    </a>
                  </div>
                </article>
              </div>
            </div>

            <!-- 在线测验面板 -->
            <div v-else-if="activeViewerTab === 'quiz'" class="student-learning-v2-viewer-panel">
              <div class="student-learning-v2-quiz-entry">
                <h3>{{ currentNode.name }} - 在线测验</h3>
                <p>围绕当前知识点快速开始测验，检验学习效果。</p>
                <button type="button" class="primary-link button-like" @click="openQuiz">
                  开始测验
                </button>
                <div class="student-learning-v2-quiz-topics">
                  <p class="topics-label">快捷主题：</p>
                  <button type="button" class="topic-chip" @click="quickQuiz('大数据基础概念')">
                    大数据基础概念
                  </button>
                  <button type="button" class="topic-chip" @click="quickQuiz('数据获取')">
                    数据获取
                  </button>
                  <button type="button" class="topic-chip" @click="quickQuiz('数据预处理')">
                    数据预处理
                  </button>
                </div>
              </div>
            </div>

            <!-- 知识总结面板 -->
            <div v-else-if="activeViewerTab === 'summary'" class="student-learning-v2-viewer-panel">
              <div class="student-learning-v2-summary-panel">
                <label class="summary-form">
                  <span>总结主题</span>
                  <input v-model.trim="summaryTopic" type="text" placeholder="输入要总结的主题..." />
                </label>
                <button
                  type="button"
                  class="primary-link button-like full-width"
                  @click="submitSummary"
                  :disabled="summaryLoading"
                >
                  {{ summaryLoading ? "生成中..." : "🤖 AI生成总结" }}
                </button>
                <div class="student-learning-v2-summary-output" :class="{ 'error-state': summaryError }">
                  {{ summaryError || summaryText || "点击上方按钮生成知识总结" }}
                </div>
              </div>
            </div>

            <!-- 底部操作 -->
            <div class="student-learning-v2-content-footer">
              <button type="button" class="btn-secondary" @click="exportNotes">📤 导出笔记</button>
              <button type="button" class="btn-primary" @click="markComplete">✅ 标记完成</button>
            </div>

            <div v-if="noteDialogOpen" class="student-learning-v2-note-mask" @click.self="closeNotes">
              <section class="student-learning-v2-note-dialog" role="dialog" aria-modal="true">
                <div class="student-learning-v2-note-head">
                  <div>
                    <span>学习笔记</span>
                    <h3>{{ currentNode.name }}</h3>
                  </div>
                  <button type="button" class="student-learning-v2-note-close" @click="closeNotes">×</button>
                </div>
                <textarea
                  v-model="noteDraft"
                  class="student-learning-v2-note-textarea"
                  rows="10"
                  placeholder="记录这个知识点的重点、疑问、例题或复习提醒..."
                ></textarea>
                <div class="student-learning-v2-note-actions">
                  <button type="button" class="btn-secondary" @click="closeNotes">取消</button>
                  <button type="button" class="btn-primary" @click="saveNotes">保存笔记</button>
                </div>
              </section>
            </div>
        </div>
      </section>

      <!-- 右栏：5E 智能体 -->
      <aside class="student-learning-v2-right-panel">
        <CourseChatDialog
          :course-id="currentCourseId"
          :student-id="currentStudentId"
          :course-name="currentCourseName"
          :node-name="currentNode?.name"
          :resource-label="selectedResource ? resourceLabel(selectedResource, selectedResourceIndex ?? 0) : ''"
          @open-resource="handleFiveEResource"
          @open-test="handleFiveETest"
        />
      </aside>
    </section>
  </div>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from "vue";
import { useRoute, useRouter } from "vue-router";
import CourseChatDialog from "./components/CourseChatDialog.vue";
import TrackedResourceFrame from "./components/TrackedResourceFrame.vue";
import {
  generateCourseSummary,
} from "../../api/client";
import { homeworkListAssignmentsForNode } from "../../api/homework";
import { fetchCurrentUser } from "../../api/login";
import { fetchNodeResources, fetchStudentCourses, recordResourceLearningEvent } from "../../api/student";
import {CourseNode, KnowledgeGraphResponse} from "../../types/knowledgeGraph";
import type { StudentCourseSummary } from "../../types/student";
import type { HomeworkAssignment } from "../../types/homework";
import {fetchKnowledgeGraph} from "../../api/knowledgeGraph";

const route = useRoute();
const router = useRouter();

// Viewer tab 状态
type ResourceCategoryTab = "bilibili" | "youtube" | "document" | "csdn";
type ViewerTab = ResourceCategoryTab | "quiz" | "summary";
const activeViewerTab = ref<ViewerTab>("bilibili");

const graph = ref<KnowledgeGraphResponse | null>(null);
const graphLoading = ref(true);
const graphError = ref("");
const studentCourses = ref<StudentCourseSummary[]>([]);
const coursesLoading = ref(false);
const coursesError = ref("");
const openChapters = ref<string[]>([]);
const openSections = ref<string[]>([]);

const currentNode = ref<CourseNode | null>(null);
const currentResources = ref<string[]>([]);
const nodeResourceError = ref("");
const selectedResource = ref("");
const selectedResourceIndex = ref<number | null>(null);
const nodeLoading = ref(false);
const currentStudentId = ref("");
const currentCourseId = ref("");

// 面包屑相关
const currentCourseName = ref("");
const currentChapterName = ref("当前章节");

// 本地学习状态
const bookmarkedNodeKeys = ref<Set<string>>(new Set());
const completedNodeKeys = ref<Set<string>>(new Set());
const notesByNode = ref<Record<string, string>>({});
const noteDialogOpen = ref(false);
const noteDraft = ref("");
const toolMessage = ref("");
let toolMessageTimer: number | null = null;

const summaryTopic = ref("");
const summaryText = ref("");
const summaryError = ref("");
const summaryLoading = ref(false);

const courseHomework = ref<HomeworkAssignment[]>([]);
const courseHomeworkLoading = ref(false);
const courseHomeworkError = ref("");
const nodeHomework = ref<HomeworkAssignment[]>([]);
const nodeHomeworkLoading = ref(false);
const nodeHomeworkError = ref("");
const selectedResourceStartedAt = ref<number | null>(null);

const chapterNodes = computed(() => graph.value?.children ?? []);
const selectedCourse = computed(() =>
  studentCourses.value.find((course) => course.course_id === currentCourseId.value) ?? null,
);
const currentCourseDescription = computed(() => selectedCourse.value?.description || "");
type BoundResourceKind = "document" | "video-embed" | "external";
type BoundResourceProvider = "bilibili" | "youtube" | "csdn" | "teacher" | "other";
type BoundResourceCard = {
  url: string;
  title: string;
  description: string;
  kind: BoundResourceKind;
  kindLabel: string;
  provider: BoundResourceProvider;
  providerLabel: string;
  external: boolean;
  embedUrl: string;
};

function isExternalUrl(path: string) {
  return /^https?:\/\//i.test(path);
}

function inferResourceProvider(path: string): BoundResourceProvider {
  const value = path.toLowerCase();
  if (value.includes("bilibili.com")) return "bilibili";
  if (value.includes("youtube.com") || value.includes("youtu.be")) return "youtube";
  if (value.includes("csdn.net")) return "csdn";
  if (!isExternalUrl(path)) return "teacher";
  return "other";
}

function providerLabel(provider: BoundResourceProvider) {
  const labels: Record<BoundResourceProvider, string> = {
    bilibili: "B站",
    youtube: "YouTube",
    csdn: "CSDN",
    teacher: "教师资源",
    other: "外部资源",
  };
  return labels[provider];
}

function isLegacyCourseVideo(path: string) {
  const value = path.toLowerCase();
  if (/\.(m3u8|mp4|webm)(?:$|[?#])/i.test(value)) return true;
  if (!isExternalUrl(path)) return false;
  return !value.includes("bilibili.com")
    && !value.includes("youtube.com")
    && !value.includes("youtu.be")
    && !value.includes("csdn.net");
}

function isDocumentPath(path: string) {
  return !isExternalUrl(path) || /\.pdf(?:$|[?#])/i.test(path);
}

function getEmbeddedVideoUrlFromUrl(url: string) {
  const youtubeVideoId = extractYouTubeVideoId(url);
  if (youtubeVideoId) {
    return `https://www.youtube.com/embed/${encodeURIComponent(youtubeVideoId)}?rel=0`;
  }

  const bilibiliVideoId = extractBilibiliVideoId(url);
  if (bilibiliVideoId) {
    return `https://player.bilibili.com/player.html?bvid=${encodeURIComponent(bilibiliVideoId)}&page=1`;
  }

  return "";
}

function extractYouTubeVideoId(url: string) {
  try {
    const parsed = new URL(url);
    const host = parsed.hostname.replace(/^www\./, "");
    if (host === "youtube.com" || host === "m.youtube.com") {
      if (parsed.pathname === "/watch") {
        return parsed.searchParams.get("v") || "";
      }
      const match = parsed.pathname.match(/^\/(?:embed|shorts)\/([A-Za-z0-9_-]{6,})/);
      return match?.[1] || "";
    }
    if (host === "youtu.be") {
      return parsed.pathname.split("/").filter(Boolean)[0] || "";
    }
    if (host === "youtube-nocookie.com") {
      const match = parsed.pathname.match(/^\/embed\/([A-Za-z0-9_-]{6,})/);
      return match?.[1] || "";
    }
  } catch {
    return "";
  }
  return "";
}

function extractBilibiliVideoId(url: string) {
  const match = url.match(/(BV[0-9A-Za-z]+)/i);
  return match?.[1] || "";
}

function buildResourceCard(path: string): BoundResourceCard | null {
  const url = path.trim();
  if (!url || isLegacyCourseVideo(url)) return null;
  const provider = inferResourceProvider(url);
  const embedUrl = provider === "bilibili" || provider === "youtube"
    ? getEmbeddedVideoUrlFromUrl(url)
    : "";
  const kind: BoundResourceKind = isDocumentPath(url) ? "document" : (embedUrl ? "video-embed" : "external");
  const fileName = decodeURIComponent(url.split(/[/?#]/).filter(Boolean).pop() || url);
  const title = provider === "teacher"
    ? fileName.replace(/\.pdf$/i, "")
    : `${providerLabel(provider)}：${currentNode.value?.name || "知识点资源"}`;
  const description = provider === "teacher"
    ? "教师手动绑定或上传的课程资料。"
    : provider === "csdn"
      ? "CSDN 内容以外链方式打开。"
      : embedUrl
        ? "已内嵌到学习中心，可直接观看。"
        : "当前绑定的是资源检索页，可打开后选择具体内容。";
  return {
    url,
    title,
    description,
    kind,
    kindLabel: kind === "document" ? "文档" : (kind === "video-embed" ? "内嵌" : "外链"),
    provider,
    providerLabel: providerLabel(provider),
    external: isExternalUrl(url),
    embedUrl,
  };
}

function visibleLearningCenterResources(resources: string[]) {
  return resources
    .map((resource) => resource.trim())
    .filter((resource) => resource && !isLegacyCourseVideo(resource));
}

function normalizePdfResourcePath(path: string) {
  return path.replace(/\\/g, "/").replace(/^\/+/, "").replace(/^backend\/data\//, "data/");
}

function encodePdfResourcePath(path: string) {
  return normalizePdfResourcePath(path)
    .split("/")
    .map((segment) => encodeURIComponent(segment))
    .join("/");
}

const heroBadges = computed(() => [
  `章节 ${chapterNodes.value.length}`,
  `当前节点 ${currentNode.value?.name ?? "未选择"}`,
  `资料 ${currentResources.value.length}`,
]);

// 资源分类
const visibleResourceCards = computed(() =>
  currentResources.value
    .map((resource) => buildResourceCard(resource))
    .filter((resource): resource is BoundResourceCard => Boolean(resource)),
);
const documentResourceCards = computed(() =>
  visibleResourceCards.value.filter((resource) => resource.kind === "document"),
);
const bilibiliResourceCards = computed(() =>
  visibleResourceCards.value.filter((resource) => resource.provider === "bilibili" && resource.embedUrl),
);
const youtubeResourceCards = computed(() =>
  visibleResourceCards.value.filter((resource) => resource.provider === "youtube" && resource.embedUrl),
);
const csdnResourceCards = computed(() =>
  visibleResourceCards.value.filter((resource) => resource.provider === "csdn"),
);
const resourceViewerTabs = computed<Array<{ key: ResourceCategoryTab; label: string; count: number }>>(() => [
  { key: "bilibili", label: "B站", count: bilibiliResourceCards.value.length },
  { key: "youtube", label: "YouTube", count: youtubeResourceCards.value.length },
  { key: "document", label: "文档", count: documentResourceCards.value.length },
  { key: "csdn", label: "CSDN", count: csdnResourceCards.value.length },
]);
const activeCategoryResourceCards = computed(() => resourceCardsForTab(activeViewerTab.value));
const activeResourceTabLabel = computed(() => {
  const match = resourceViewerTabs.value.find((tab) => tab.key === activeViewerTab.value);
  return match?.label ? `${match.label} ` : "";
});
const selectableNodes = computed(() => flattenSelectableNodes(chapterNodes.value));
const currentNodeKey = computed(() => currentNode.value ? getNodeKey(currentNode.value) : "");
const currentNodeIndex = computed(() => {
  if (!currentNode.value) return -1;
  return selectableNodes.value.findIndex((item) => getNodeKey(item) === currentNodeKey.value);
});
const canNavigatePrev = computed(() => currentNodeIndex.value > 0);
const canNavigateNext = computed(() => currentNodeIndex.value >= 0 && currentNodeIndex.value < selectableNodes.value.length - 1);
const isBookmarked = computed(() => Boolean(currentNodeKey.value && bookmarkedNodeKeys.value.has(currentNodeKey.value)));
const hasCurrentNote = computed(() => Boolean(currentNodeKey.value && (notesByNode.value[currentNodeKey.value] ?? "").trim()));
const isCompleted = computed(() => Boolean(currentNodeKey.value && completedNodeKeys.value.has(currentNodeKey.value)));
const currentTrackingNodeId = computed(() =>
  currentNode.value ? (getNodeIdentifier(currentNode.value) || currentNode.value.name) : "",
);

function switchViewerTab(tab: ViewerTab) {
  activeViewerTab.value = tab;

  if (isResourceCategoryTab(tab)) {
    const resource = resourceCardsForTab(tab)[0];
    if (resource) {
      selectResource(resource.url, currentResources.value.indexOf(resource.url));
    }
  }
}

function isResourceCategoryTab(tab: ViewerTab): tab is ResourceCategoryTab {
  return tab === "bilibili" || tab === "youtube" || tab === "document" || tab === "csdn";
}

function resourceCardsForTab(tab: ViewerTab) {
  if (tab === "bilibili") return bilibiliResourceCards.value;
  if (tab === "youtube") return youtubeResourceCards.value;
  if (tab === "document") return documentResourceCards.value;
  if (tab === "csdn") return csdnResourceCards.value;
  return [];
}

function firstAvailableResourceTab(): ViewerTab {
  for (const tab of resourceViewerTabs.value) {
    if (tab.count > 0) return tab.key;
  }
  return "bilibili";
}

function sectionNodes(chapter: CourseNode) {
  return chapter.grandchildren ?? [];
}

function knowledgeNodes(section: CourseNode) {
  return section["great-grandchildren"] ?? [];
}

function getResourceKinds(node: CourseNode) {
  const resources = visibleLearningCenterResources(normalizeResources(node));
  return {
    bilibili: resources.some((item) => inferResourceProvider(item) === "bilibili"),
    youtube: resources.some((item) => inferResourceProvider(item) === "youtube"),
    csdn: resources.some((item) => inferResourceProvider(item) === "csdn"),
    document: resources.some((item) => isDocumentPath(item)),
    count: resources.length,
  };
}

function resourceBadgeText(node: CourseNode) {
  const kinds = getResourceKinds(node);
  const labels = [];
  if (kinds.bilibili) labels.push("B站");
  if (kinds.youtube) labels.push("YouTube");
  if (kinds.document) labels.push("文档");
  if (kinds.csdn) labels.push("CSDN");
  return labels.length ? labels.join(" / ") : "待绑定";
}

function sectionResourceLabel(section: CourseNode) {
  if (isSelectableNode(section)) return resourceBadgeText(section);
  const points = knowledgeNodes(section);
  const boundCount = points.filter((item) => getResourceKinds(item).count > 0).length;
  const labels = [`${points.length} 个知识点`];
  if (boundCount) labels.push(`${boundCount} 已绑定`);
  return labels.join(" · ");
}

function flattenSelectableNodes(nodes: CourseNode[]) {
  const items: CourseNode[] = [];
  for (const chapter of nodes) {
    for (const section of sectionNodes(chapter)) {
      if (isSelectableNode(section)) items.push(section);
      for (const point of knowledgeNodes(section)) {
        if (isSelectableNode(point)) items.push(point);
      }
    }
  }
  return items;
}

function matchesRouteNode(node: CourseNode, target: string) {
  if (!target) return false;
  return node.name === target || getNodeIdentifier(node) === target;
}

function isChapterOpen(name: string) {
  return openChapters.value.includes(name);
}

function toggleChapter(name: string) {
  if (isChapterOpen(name)) {
    openChapters.value = openChapters.value.filter((item) => item !== name);
  } else {
    openChapters.value = [...openChapters.value, name];
  }
}

function normalizeResources(node: CourseNode) {
  const raw = node.resource_path;
  if (typeof raw === "string") {
    return raw.trim() ? [raw.trim()] : [];
  }
  if (Array.isArray(raw)) {
    return raw.filter((item): item is string => typeof item === "string" && item.trim().length > 0);
  }
  return [];
}

function isSelectableNode(node: CourseNode) {
  return knowledgeNodes(node).length === 0;
}

function getNodeFlag(node: CourseNode) {
  const flag = (node as { flag?: unknown }).flag;
  if (flag === "done" || flag === "completed") return "✓";
  if (flag === "current" || flag === "in-progress") return "●";
  return "";
}

async function selectNode(node: CourseNode) {
  nodeLoading.value = true;
  nodeResourceError.value = "";
  currentNode.value = node;
  currentResources.value = [];
  summaryTopic.value = node.name;
  summaryText.value = "";
  summaryError.value = "";
  nodeHomework.value = [];
  nodeHomeworkError.value = "";
  
  selectedResource.value = "";
  selectedResourceIndex.value = null;
  activeViewerTab.value = "bilibili";

  updateBreadcrumb(node);
  loadHomeworkForNode(node).catch(() => {});

  try {
    const resources = await fetchNodeResources({
      course_id: currentCourseId.value || "course_big_data",
      node_name: node.name,
    });
    currentResources.value = Array.isArray(resources) ? resources : [];
    activeViewerTab.value = firstAvailableResourceTab();
    const firstResource = resourceCardsForTab(activeViewerTab.value)[0];
    if (firstResource) {
      await selectResource(firstResource.url, currentResources.value.indexOf(firstResource.url));
    }
  } catch (error) {
    currentResources.value = [];
    nodeResourceError.value = error instanceof Error ? error.message : "当前知识点绑定资源加载失败";
  } finally {
    nodeLoading.value = false;
  }
}

function updateBreadcrumb(node: CourseNode) {
  // 简化版面包屑，基于当前节点
  // 如果有完整的父级信息可以在这里扩展
  currentCourseName.value = selectedCourse.value?.course_name || graph.value?.name || currentCourseId.value || "当前课程";
  
  // 尝试从 graph 中找到父章节
  for (const chapter of chapterNodes.value) {
    for (const section of sectionNodes(chapter)) {
      if (section.name === node.name) {
        currentChapterName.value = chapter.name;
        return;
      }
      for (const point of knowledgeNodes(section)) {
        if (point.name === node.name) {
          currentChapterName.value = `${chapter.name} / ${section.name}`;
          return;
        }
      }
    }
  }
  
  currentChapterName.value = "当前章节";
}

function getNodeIdentifier(node: CourseNode) {
  const raw = (node as { node_id?: unknown }).node_id ?? "";
  return String(raw || "");
}

function getNodeKey(node: CourseNode) {
  return getNodeIdentifier(node) || node.name;
}

function learningStateKey(name: string) {
  return `ai-education:${currentCourseId.value || "course_big_data"}:${name}`;
}

function loadLocalLearningState() {
  try {
    const bookmarks = JSON.parse(localStorage.getItem(learningStateKey("bookmarks")) || "[]");
    const completed = JSON.parse(localStorage.getItem(learningStateKey("completed")) || "[]");
    const notes = JSON.parse(localStorage.getItem(learningStateKey("notes")) || "{}");
    bookmarkedNodeKeys.value = new Set(Array.isArray(bookmarks) ? bookmarks.filter((item): item is string => typeof item === "string") : []);
    completedNodeKeys.value = new Set(Array.isArray(completed) ? completed.filter((item): item is string => typeof item === "string") : []);
    notesByNode.value = notes && typeof notes === "object" && !Array.isArray(notes) ? notes as Record<string, string> : {};
  } catch {
    bookmarkedNodeKeys.value = new Set();
    completedNodeKeys.value = new Set();
    notesByNode.value = {};
  }
}

function isSectionOpen(name: string) {
  return openSections.value.includes(name);
}

function toggleSection(name: string) {
  if (isSectionOpen(name)) {
    openSections.value = openSections.value.filter((item) => item !== name);
  } else {
    openSections.value = [...openSections.value, name];
  }
}

function handleSectionClick(section: CourseNode) {
  if (isSelectableNode(section)) {
    void selectNode(section);
    return;
  }
  if (knowledgeNodes(section).length) {
    toggleSection(section.name);
  }
}

function saveLocalLearningState() {
  localStorage.setItem(learningStateKey("bookmarks"), JSON.stringify([...bookmarkedNodeKeys.value]));
  localStorage.setItem(learningStateKey("completed"), JSON.stringify([...completedNodeKeys.value]));
  localStorage.setItem(learningStateKey("notes"), JSON.stringify(notesByNode.value));
}

function showToolMessage(message: string) {
  toolMessage.value = message;
  if (toolMessageTimer) {
    window.clearTimeout(toolMessageTimer);
  }
  toolMessageTimer = window.setTimeout(() => {
    toolMessage.value = "";
    toolMessageTimer = null;
  }, 1800);
}

function ensureChapterOpenForNode(node: CourseNode) {
  for (const chapter of chapterNodes.value) {
    for (const section of sectionNodes(chapter)) {
      if (section.name !== node.name && !knowledgeNodes(section).some((point) => point.name === node.name)) {
        continue;
      }
      if (!openChapters.value.includes(chapter.name)) {
        openChapters.value = [...openChapters.value, chapter.name];
      }
      if (!openSections.value.includes(section.name)) {
        openSections.value = [...openSections.value, section.name];
      }
      return;
    }
  }
}

async function loadHomeworkForNode(node: CourseNode) {
  nodeHomeworkLoading.value = true;
  nodeHomeworkError.value = "";
  try {
    const res = await homeworkListAssignmentsForNode({
      course_id: currentCourseId.value || "course_big_data",
      node_id: getNodeIdentifier(node) || undefined,
      node_name: node.name,
    });
    nodeHomework.value = res.assignments || [];
  } catch (e) {
    nodeHomework.value = [];
    nodeHomeworkError.value = e instanceof Error ? e.message : "章节作业加载失败";
  } finally {
    nodeHomeworkLoading.value = false;
  }
}

async function loadHomeworkForCourse() {
  courseHomeworkLoading.value = true;
  courseHomeworkError.value = "";
  try {
    const res = await homeworkListAssignmentsForNode({
      course_id: currentCourseId.value || "course_big_data",
    });
    courseHomework.value = res.assignments || [];
  } catch (e) {
    courseHomework.value = [];
    courseHomeworkError.value = e instanceof Error ? e.message : "课程作业加载失败";
  } finally {
    courseHomeworkLoading.value = false;
  }
}

function goHomeworkForCurrentNode() {
  if (!currentNode.value) {
    return;
  }
  router.push({
    name: "student-homework",
    query: {
      course_id: currentCourseId.value || "course_big_data",
      node_name: currentNode.value.name,
    },
  });
}

function goHomeworkForCourse() {
  router.push({
    name: "student-homework",
    query: {
      course_id: currentCourseId.value || "course_big_data",
    },
  });
}

function goHomeworkDetail(assignmentId: string) {
  router.push({ name: "student-homework-detail", params: { assignmentId } });
}

async function selectResource(resource: string, index: number) {
  selectedResource.value = resource;
  selectedResourceIndex.value = index;
  selectedResourceStartedAt.value = Date.now();
  void recordCurrentResourceLearningEvent("view", 5, false).catch((error) => {
    console.warn("Failed to record resource view event", error);
  });
}

function getResourceIndex(resource: string) {
  const index = currentResources.value.indexOf(resource);
  return index >= 0 ? index : 0;
}

function openDocumentResource(resource: BoundResourceCard) {
  void selectResource(resource.url, getResourceIndex(resource.url));
  activeViewerTab.value = "document";
}

function documentViewerUrl(resource: BoundResourceCard) {
  if (isExternalUrl(resource.url)) {
    return resource.url;
  }
  return `/api/pdf/${encodePdfResourcePath(resource.url)}#toolbar=0&navpanes=0&zoom=page-width`;
}

function recordResourceClick(resource: BoundResourceCard) {
  void selectResource(resource.url, getResourceIndex(resource.url));
}

function currentResourceDurationSeconds() {
  if (!selectedResourceStartedAt.value) return 0;
  return Math.max(0, Math.round((Date.now() - selectedResourceStartedAt.value) / 1000));
}

async function recordCurrentResourceLearningEvent(
  eventType: "view" | "complete",
  progressPercent: number,
  isCompleted: boolean,
) {
  if (!currentNode.value) return;
  const nodeId = getNodeIdentifier(currentNode.value) || currentNode.value.name;
  await recordResourceLearningEvent({
    course_id: currentCourseId.value || "course_big_data",
    node_id: nodeId,
    resource_path: selectedResource.value || null,
    event_type: eventType,
    duration_seconds: eventType === "complete" ? currentResourceDurationSeconds() : 0,
    progress_percent: progressPercent,
    is_completed: isCompleted,
    payload: {
      source: "student_course_content",
      node_name: currentNode.value.name,
      viewer_tab: activeViewerTab.value,
      resource_index: selectedResourceIndex.value,
    },
  });
}

function resourceLabel(resource: string, index: number) {
  const card = buildResourceCard(resource);
  if (card) {
    return card.title;
  }
  const fileName = resource.split("/").pop() ?? `资料 ${index + 1}`;
  return fileName.replace(/\.pdf$/i, "");
}

async function loadCurrentStudent() {
  try {
    const user = await fetchCurrentUser() as {
      username?: string;
      user_id?: unknown;
      login_id?: unknown;
    };
    currentStudentId.value = String(user.username ?? user.login_id ?? user.user_id ?? "");
  } catch (error) {
    console.warn("Failed to load current student for 5E assistant", error);
    currentStudentId.value = "";
  }
}

function handleFiveEResource(resourceId: string) {
  if (!resourceId) return;
  const targetIndex = currentResources.value.findIndex((item) => item.includes(resourceId));
  if (targetIndex >= 0) {
    const targetResource = currentResources.value[targetIndex];
    selectResource(targetResource, targetIndex);
    const card = buildResourceCard(targetResource);
    if (card?.provider === "bilibili" || card?.provider === "youtube" || card?.provider === "csdn") {
      activeViewerTab.value = card.provider;
    } else if (card?.kind === "document") {
      activeViewerTab.value = "document";
    }
    return;
  }
  showToolMessage(`5E 助教推荐资源：${resourceId}`);
}

function handleFiveETest(testId: string) {
  quickQuiz(testId || currentNode.value?.name || "大数据基础");
}

async function submitSummary() {
  if (!summaryTopic.value) {
    summaryError.value = "请先输入要总结的主题。";
    summaryText.value = "";
    return;
  }
  summaryLoading.value = true;
  summaryError.value = "";
  summaryText.value = "";
  try {
    const data = await generateCourseSummary(summaryTopic.value);
    summaryText.value = data.summary || "当前没有可展示的总结内容。";
  } catch (error) {
    summaryError.value = error instanceof Error ? error.message : "总结生成失败";
  } finally {
    summaryLoading.value = false;
  }
}

function openQuiz() {
  const topic = currentNode.value?.name;
  if (!topic) {
    alert("请先选择一个知识点");
    return;
  }
  router.push({
    path: "/student/quiz",
    query: {
      topic,
      node: topic,
      course_id: currentCourseId.value || "course_big_data",
    },
  });
}

function quickQuiz(topic: string) {
  router.push({
    path: "/student/quiz",
    query: {
      topic,
      node: topic,
      course_id: currentCourseId.value || "course_big_data",
    },
  });
}

async function navigateByOffset(offset: number) {
  const targetIndex = currentNodeIndex.value + offset;
  const target = selectableNodes.value[targetIndex];
  if (!target) return;
  ensureChapterOpenForNode(target);
  await selectNode(target);
  showToolMessage(`已切换到：${target.name}`);
}

function navigatePrevNode() {
  if (!canNavigatePrev.value) {
    showToolMessage("已经是第一个知识点");
    return;
  }
  void navigateByOffset(-1);
}

function navigateNextNode() {
  if (!canNavigateNext.value) {
    showToolMessage("已经是最后一个知识点");
    return;
  }
  void navigateByOffset(1);
}

function toggleBookmark() {
  if (!currentNodeKey.value) return;
  const next = new Set(bookmarkedNodeKeys.value);
  if (next.has(currentNodeKey.value)) {
    next.delete(currentNodeKey.value);
    showToolMessage("已取消收藏");
  } else {
    next.add(currentNodeKey.value);
    showToolMessage("已收藏当前知识点");
  }
  bookmarkedNodeKeys.value = next;
  saveLocalLearningState();
}

function openNotes() {
  if (!currentNodeKey.value) return;
  noteDraft.value = notesByNode.value[currentNodeKey.value] || "";
  noteDialogOpen.value = true;
}

function closeNotes() {
  noteDialogOpen.value = false;
}

function saveNotes() {
  if (!currentNodeKey.value) return;
  notesByNode.value = {
    ...notesByNode.value,
    [currentNodeKey.value]: noteDraft.value.trim(),
  };
  saveLocalLearningState();
  noteDialogOpen.value = false;
  showToolMessage(noteDraft.value.trim() ? "笔记已保存" : "笔记已清空");
}

function exportNotes() {
  const note = currentNodeKey.value ? notesByNode.value[currentNodeKey.value] : "";
  const contentParts = [
    currentNode.value ? `知识点：${currentNode.value.name}` : "",
    note ? `学习笔记：\n${note}` : "",
    summaryText.value ? `知识总结：\n${summaryText.value}` : "",
  ].filter(Boolean);
  if (contentParts.length) {
    const content = contentParts.join("\n\n");
    navigator.clipboard.writeText(content).then(() => {
      showToolMessage("笔记内容已复制");
    }).catch(() => {
      console.log("导出笔记:", content);
      showToolMessage("已在控制台输出笔记内容");
    });
  } else {
    showToolMessage("暂无可导出的笔记或总结");
  }
}

async function markComplete() {
  if (!currentNodeKey.value) return;
  completedNodeKeys.value = new Set([...completedNodeKeys.value, currentNodeKey.value]);
  saveLocalLearningState();
  try {
    await recordCurrentResourceLearningEvent("complete", 100, true);
    showToolMessage(`已标记完成并回流学习证据：${currentNode.value?.name}`);
  } catch (error) {
    console.warn("Failed to record resource completion event", error);
    showToolMessage(`已本地标记完成，学习证据回流失败`);
  }
}

function applyCurrentCourseName() {
  currentCourseName.value = selectedCourse.value?.course_name || graph.value?.name || currentCourseId.value || "当前课程";
}

function resetCourseContentState() {
  graph.value = null;
  currentNode.value = null;
  currentResources.value = [];
  nodeResourceError.value = "";
  selectedResource.value = "";
  selectedResourceIndex.value = null;
  summaryTopic.value = "";
  summaryText.value = "";
  summaryError.value = "";
  nodeHomework.value = [];
  nodeHomeworkError.value = "";
  openChapters.value = [];
  openSections.value = [];
}

async function loadStudentCourseOptions() {
  coursesLoading.value = true;
  coursesError.value = "";
  try {
    const data = await fetchStudentCourses();
    studentCourses.value = data.courses || [];
    const routeCourseId = typeof route.query.course_id === "string" ? route.query.course_id : "";
    const storedCourseId = localStorage.getItem("ai-education:selected-course-id") || "";
    const preferred = routeCourseId || storedCourseId || data.default_course_id || studentCourses.value[0]?.course_id || "course_big_data";
    const available = studentCourses.value.find((course) => course.course_id === preferred);
    currentCourseId.value = available?.course_id || studentCourses.value[0]?.course_id || preferred;
    localStorage.setItem("ai-education:selected-course-id", currentCourseId.value);
    applyCurrentCourseName();
  } catch (error) {
    coursesError.value = error instanceof Error ? error.message : "课程列表加载失败";
    if (!currentCourseId.value) {
      currentCourseId.value = "course_big_data";
    }
    applyCurrentCourseName();
  } finally {
    coursesLoading.value = false;
  }
}

async function handleCourseChange() {
  if (!currentCourseId.value) return;
  localStorage.setItem("ai-education:selected-course-id", currentCourseId.value);
  applyCurrentCourseName();
  resetCourseContentState();
  loadLocalLearningState();
  await loadGraph();
}

async function loadGraph() {
  graphLoading.value = true;
  graphError.value = "";
  try {
    graph.value = await fetchKnowledgeGraph(currentCourseId.value || "course_big_data");
    applyCurrentCourseName();
    const firstChapter = (graph.value.children ?? [])[0];
    openChapters.value = firstChapter ? [firstChapter.name] : [];
    openSections.value = firstChapter ? sectionNodes(firstChapter).slice(0, 1).map((item) => item.name) : [];
    const targetNodeName = typeof route.query.node === "string" ? route.query.node : "";
    if (targetNodeName) {
      const target = flattenSelectableNodes(graph.value.children ?? []).find((item) => matchesRouteNode(item, targetNodeName));
      if (target) {
        ensureChapterOpenForNode(target);
        await selectNode(target);
      }
    }
  } catch (error) {
    graphError.value = error instanceof Error ? error.message : "课程目录加载失败";
  } finally {
    graphLoading.value = false;
  }
  await loadHomeworkForCourse();
}

onMounted(async () => {
  void loadCurrentStudent();
  await loadStudentCourseOptions();
  loadLocalLearningState();
  await loadGraph();
});

onBeforeUnmount(() => {
  if (toolMessageTimer) {
    window.clearTimeout(toolMessageTimer);
  }
});
</script>

<style scoped>
.student-learning-v2-course-context {
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(260px, 360px);
  gap: 16px;
  align-items: center;
  margin: 14px 0 18px;
  padding: 18px 20px;
  border: 1px solid #d7e2f0;
  border-radius: 10px;
  background: #fff;
}

.student-learning-v2-course-copy {
  min-width: 0;
}

.course-context-label,
.course-select-label {
  display: block;
  color: #64748b;
  font-size: 12px;
  font-weight: 700;
}

.student-learning-v2-course-copy h2 {
  margin: 4px 0 6px;
  color: #0f172a;
  font-size: 22px;
  line-height: 1.35;
}

.student-learning-v2-course-copy p {
  margin: 0;
  color: #64748b;
  font-size: 13px;
  line-height: 1.6;
}

.student-learning-v2-course-actions {
  display: grid;
  gap: 8px;
}

.student-learning-v2-course-select {
  width: 100%;
  min-height: 40px;
  border: 1px solid #cbd5e1;
  border-radius: 8px;
  background: #fff;
  color: #0f172a;
  font-size: 14px;
  padding: 0 12px;
}

.course-context-stats {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.course-context-stats span,
.course-context-hint {
  display: inline-flex;
  align-items: center;
  min-height: 26px;
  padding: 3px 9px;
  border-radius: 6px;
  background: #f1f5f9;
  color: #475569;
  font-size: 12px;
  font-weight: 700;
}

.course-context-hint.error-state {
  background: #fef2f2;
  color: #dc2626;
}

/* 内容头部 */
.student-learning-v2-content-header {
  padding: 6px 12px 10px;
  border-bottom: 1px solid #e4e7ed;
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 12px;
  flex-wrap: wrap;
  background: #fff;
}

.student-learning-v2-breadcrumb {
  flex: 1 1 360px;
  min-width: 0;
  font-size: 14px;
  color: #606266;
  display: flex;
  align-items: flex-start;
  gap: 8px;
  flex-wrap: wrap;
  line-height: 1.5;
}

.student-learning-v2-breadcrumb .sep {
  color: #c0c4cc;
}

.student-learning-v2-breadcrumb .current {
  color: #409eff;
  font-weight: 500;
  overflow-wrap: anywhere;
}

.student-learning-v2-content-tools {
  flex: 0 0 auto;
  display: flex;
  gap: 8px;
}

.student-learning-v2-tool-btn {
  width: 32px;
  height: 32px;
  border: 1px solid #dcdfe6;
  background: #fff;
  border-radius: 4px;
  cursor: pointer;
  font-size: 14px;
  transition: all 0.3s;
}

.student-learning-v2-tool-btn:hover {
  background: #ecf5ff;
  border-color: #409eff;
  color: #409eff;
}

.student-learning-v2-tool-btn:disabled {
  cursor: not-allowed;
  opacity: 0.45;
  background: #f8fafc;
  color: #94a3b8;
}

.student-learning-v2-tool-btn.active {
  border-color: #2563eb;
  background: #eaf1ff;
  color: #2563eb;
}

.student-learning-v2-tool-message {
  margin: 10px 12px 0;
  padding: 8px 12px;
  border: 1px solid #bfdbfe;
  border-radius: 10px;
  background: #eff6ff;
  color: #1d4ed8;
  font-size: 13px;
}

/* Viewer Tabs */
.student-learning-v2-viewer-tabs {
  display: flex;
  border-bottom: 1px solid #e4e7ed;
  padding: 0 16px;
  background: #f8fafc;
  overflow-x: auto;
}

.student-learning-v2-viewer-tab {
  min-height: 48px;
  padding: 0 20px;
  border: none;
  background: none;
  cursor: pointer;
  font-size: 14px;
  color: #606266;
  border-bottom: 2px solid transparent;
  transition: all 0.3s;
  font-weight: 500;
}

.student-learning-v2-viewer-tab-count {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 22px;
  height: 22px;
  margin-left: 8px;
  padding: 0 6px;
  border-radius: 999px;
  background: #e2e8f0;
  color: #475569;
  font-size: 12px;
  font-weight: 700;
}

.student-learning-v2-viewer-tab:hover {
  color: #409eff;
  background: rgba(64, 158, 255, 0.05);
}

.student-learning-v2-viewer-tab.active {
  color: #409eff;
  border-bottom-color: #409eff;
  background: #fff;
  font-weight: 700;
}

/* Viewer Panel */
.student-learning-v2-viewer-panel {
  flex: 1;
  overflow: auto;
  display: flex;
  flex-direction: column;
  background: #f8fafc;
  border-radius: 0 0 14px 14px;
  min-height: clamp(560px, 68vh, 760px);
}

.student-learning-v2-viewer-empty {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 60px 20px;
  color: #909399;
}

.student-learning-v2-viewer-empty .empty-icon {
  font-size: 64px;
  margin-bottom: 16px;
  opacity: 0.5;
}

.student-learning-v2-viewer-empty p {
  font-size: 14px;
}

.student-learning-v2-viewer-empty.error-state {
  color: #dc2626;
}

.student-learning-v2-resource-category-panel {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(320px, 1fr));
  gap: 16px;
  padding: 18px;
  align-content: start;
}

.student-learning-v2-resource-display-card {
  padding: 16px;
  border: 1px solid #dbe4f0;
  border-radius: 8px;
  background: #fff;
  display: flex;
  flex-direction: column;
  gap: 10px;
  box-shadow: 0 10px 26px rgba(15, 23, 42, 0.06);
}

.student-learning-v2-resource-display-card.embedded {
  min-height: 420px;
}

.student-learning-v2-resource-display-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
}

.student-learning-v2-resource-display-card h3 {
  margin: 0;
  margin-top: 8px;
  color: #0f172a;
  font-size: 15px;
  line-height: 1.4;
  overflow-wrap: anywhere;
}

.student-learning-v2-resource-display-card p {
  margin: 0;
  color: #64748b;
  font-size: 13px;
  line-height: 1.6;
}

.student-learning-v2-bound-actions {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.student-learning-v2-bound-provider,
.student-learning-v2-bound-kind {
  display: inline-flex;
  align-items: center;
  min-height: 24px;
  padding: 3px 8px;
  border-radius: 6px;
  font-size: 12px;
  font-weight: 700;
}

.student-learning-v2-bound-provider {
  background: #eaf1ff;
  color: #1d4ed8;
}

.student-learning-v2-bound-kind {
  background: #f1f5f9;
  color: #475569;
}

.student-learning-v2-bound-actions {
  margin-top: auto;
}

.student-learning-v2-bound-actions a,
.student-learning-v2-resource-watch,
.student-learning-v2-resource-option {
  border: 1px solid #cbd5e1;
  border-radius: 6px;
  background: #fff;
  color: #2563eb;
  cursor: pointer;
  font-size: 13px;
  font-weight: 700;
  text-decoration: none;
  transition: border-color 0.2s, background 0.2s, color 0.2s;
}

.student-learning-v2-bound-actions a,
.student-learning-v2-resource-watch {
  padding: 7px 12px;
}

.student-learning-v2-bound-actions a:hover,
.student-learning-v2-resource-watch:hover,
.student-learning-v2-resource-option:hover,
.student-learning-v2-resource-option.active {
  border-color: #2563eb;
  background: #eff6ff;
  color: #1d4ed8;
}

.student-learning-v2-resource-frame {
  width: 100%;
  flex: 1;
  border: none;
  background: #fff;
  min-height: clamp(560px, 68vh, 760px);
  border-radius: 0 0 12px 12px;
}

.student-learning-v2-resource-frame.compact,
.student-learning-v2-video-embed {
  width: 100%;
  min-height: 360px;
  aspect-ratio: 16 / 9;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  background: #fff;
}

.student-learning-v2-video-embed {
  border: none;
}

/* 测验入口 */
.student-learning-v2-quiz-entry {
  width: min(720px, calc(100% - 48px));
  min-height: 420px;
  margin: auto;
  padding: 48px;
  background: #fff;
  border: 1px solid #e2e8f0;
  border-radius: 18px;
  box-shadow: 0 18px 42px rgba(15, 23, 42, 0.08);
  text-align: center;
  display: flex;
  flex-direction: column;
  justify-content: center;
}

.student-learning-v2-quiz-entry h3 {
  font-size: 20px;
  margin-bottom: 16px;
  color: #303133;
}

.student-learning-v2-quiz-entry p {
  font-size: 14px;
  color: #606266;
  margin-bottom: 24px;
}

.student-learning-v2-quiz-topics {
  margin-top: 32px;
  padding-top: 24px;
  border-top: 1px solid #e4e7ed;
}

.student-learning-v2-quiz-topics .topics-label {
  font-size: 13px;
  color: #909399;
  margin-bottom: 12px;
}

.student-learning-v2-quiz-topics .topic-chip {
  display: inline-block;
  padding: 8px 16px;
  margin: 4px;
  background: #f5f7fa;
  border: 1px solid #e4e7ed;
  border-radius: 16px;
  cursor: pointer;
  font-size: 13px;
  color: #606266;
  transition: all 0.3s;
}

.student-learning-v2-quiz-topics .topic-chip:hover {
  background: #ecf5ff;
  border-color: #409eff;
  color: #409eff;
}

/* 总结面板 */
.student-learning-v2-summary-panel {
  width: min(860px, calc(100% - 48px));
  min-height: 460px;
  margin: auto;
  padding: 40px;
  background: #fff;
  border: 1px solid #e2e8f0;
  border-radius: 18px;
  box-shadow: 0 18px 42px rgba(15, 23, 42, 0.08);
}

.student-learning-v2-summary-output {
  margin-top: 24px;
  padding: 20px;
  background: #f5f7fa;
  border: 1px solid #e2e8f0;
  border-radius: 14px;
  min-height: 260px;
  font-size: 14px;
  line-height: 1.8;
  color: #606266;
  white-space: pre-wrap;
}

.student-learning-v2-summary-output.error-state {
  background: #fef0f0;
  color: #f56c6c;
}

.student-learning-v2-note-mask {
  position: fixed;
  inset: 0;
  z-index: 60;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 24px;
  background: rgba(15, 23, 42, 0.36);
  backdrop-filter: blur(4px);
}

.student-learning-v2-note-dialog {
  width: min(680px, 100%);
  padding: 24px;
  border: 1px solid #dbe7f7;
  border-radius: 18px;
  background: #fff;
  box-shadow: 0 24px 70px rgba(15, 23, 42, 0.24);
}

.student-learning-v2-note-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 16px;
}

.student-learning-v2-note-head span {
  display: block;
  margin-bottom: 4px;
  color: #2563eb;
  font-size: 13px;
  font-weight: 700;
}

.student-learning-v2-note-head h3 {
  margin: 0;
  color: #0f172a;
  font-size: 20px;
  line-height: 1.35;
}

.student-learning-v2-note-close {
  width: 34px;
  height: 34px;
  border: 1px solid #e2e8f0;
  border-radius: 10px;
  background: #fff;
  color: #64748b;
  cursor: pointer;
  font-size: 20px;
  line-height: 1;
}

.student-learning-v2-note-textarea {
  width: 100%;
  min-height: 260px;
  resize: vertical;
  padding: 14px 16px;
  border: 1px solid #dbe4f0;
  border-radius: 14px;
  color: #0f172a;
  font-size: 14px;
  line-height: 1.7;
  outline: none;
}

.student-learning-v2-note-textarea:focus {
  border-color: #2563eb;
  box-shadow: 0 0 0 3px rgba(37, 99, 235, 0.12);
}

.student-learning-v2-note-actions {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
  margin-top: 16px;
}

@media (max-width: 900px) {
  .student-learning-v2-course-context {
    grid-template-columns: 1fr;
  }

  .student-learning-v2-viewer-panel,
  .student-learning-v2-resource-frame {
    min-height: 480px;
  }

  .student-learning-v2-quiz-entry,
  .student-learning-v2-summary-panel {
    width: calc(100% - 24px);
    padding: 28px;
  }
}

/* 底部操作 */
.student-learning-v2-content-footer {
  padding: 16px 20px;
  border-top: 1px solid #e4e7ed;
  display: flex;
  gap: 12px;
  justify-content: flex-end;
  background: #fff;
}

.btn-primary,
.btn-secondary {
  padding: 10px 20px;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 14px;
  transition: all 0.3s;
}

.btn-primary {
  background: #409eff;
  color: #fff;
}

.btn-primary:hover {
  background: #66b1ff;
}

.btn-secondary {
  background: #fff;
  color: #606266;
  border: 1px solid #dcdfe6;
}

.btn-secondary:hover {
  background: #f5f7fa;
  border-color: #c0c4cc;
}

</style>
