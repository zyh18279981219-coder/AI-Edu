<template>
  <div class="course-shell">
    <!-- 页面头部 -->
    <div class="student-learning-v2-header">
      <div>
        <h1>📚 学习中心</h1>
        <p class="student-learning-v2-desc">课程目录、学习资源和 AI 助教</p>
      </div>
    </div>

    <!-- 三栏布局 -->
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
              <li v-for="section in sectionNodes(chapter)" :key="section.name">
                <button
                  type="button"
                  class="toc-item"
                  :disabled="!isSelectableNode(section)"
                  :class="{ active: currentNode?.name === section.name }"
                  @click="isSelectableNode(section) && selectNode(section)"
                >
                  <span class="toc-item-text">{{ section.name }}</span>
                  <span v-if="getNodeFlag(section)" class="toc-item-flag">{{ getNodeFlag(section) }}</span>
                </button>
                <ul v-if="knowledgeNodes(section).length" class="toc-knowledge-list">
                  <li v-for="node in knowledgeNodes(section)" :key="node.name">
                    <button
                      type="button"
                      class="toc-subitem"
                      :disabled="!isSelectableNode(node)"
                      :class="{ active: currentNode?.name === node.name }"
                      @click="isSelectableNode(node) && selectNode(node)"
                    >
                      <span class="toc-item-text">{{ node.name }}</span>
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
        <!-- 模式切换入口 -->
        <div class="student-learning-v2-mode-switcher">
          <div class="student-learning-v2-mode-tabs">
            <button
              class="student-learning-v2-mode-tab"
              :class="{ active: activeMode === 'content' }"
              type="button"
              @click="activeMode = 'content'"
            >
              学习内容
            </button>
            <button
              class="student-learning-v2-mode-tab"
              :class="{ active: activeMode === 'path' }"
              type="button"
              @click="activeMode = 'path'"
            >
              个性化路径
            </button>
          </div>
          <div class="student-learning-v2-mode-hint">
            {{ activeMode === 'content' ? '当前正在查看课程资源与 AI 助教，个性化路径可查看系统推荐的学习顺序' : '查看系统为你推荐的个性化学习路径' }}
          </div>
        </div>

        <!-- 学习内容视图 -->
        <div v-if="activeMode === 'content'">
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
                <button type="button" class="student-learning-v2-tool-btn" title="上一个" @click="navigatePrevNode">◀</button>
                <button type="button" class="student-learning-v2-tool-btn" title="下一个" @click="navigateNextNode">▶</button>
                <button type="button" class="student-learning-v2-tool-btn" title="收藏" @click="toggleBookmark">⭐</button>
                <button type="button" class="student-learning-v2-tool-btn" title="笔记" @click="openNotes">📝</button>
              </div>
            </div>

            <!-- Viewer Tabs -->
            <div class="student-learning-v2-viewer-tabs">
              <button
                type="button"
                class="student-learning-v2-viewer-tab"
                :class="{ active: activeViewerTab === 'pdf' }"
                @click="switchViewerTab('pdf')"
              >
                📄 PDF文档
              </button>
              <button
                type="button"
                class="student-learning-v2-viewer-tab"
                :class="{ active: activeViewerTab === 'video' }"
                @click="switchViewerTab('video')"
              >
                🎥 视频讲解
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

            <!-- PDF 文档面板 -->
            <div v-if="activeViewerTab === 'pdf'" class="student-learning-v2-viewer-panel">
              <div v-if="!hasPdfResource" class="student-learning-v2-viewer-empty">
                <div class="empty-icon">📄</div>
                <p>当前知识点暂无 PDF 文档</p>
              </div>
              <div v-else>
                <iframe
                  v-if="selectedResource"
                  class="student-learning-v2-resource-frame"
                  :src="pdfViewerUrl"
                  title="课程 PDF 预览"
                />
              </div>
            </div>

            <!-- 视频讲解面板 -->
            <div v-else-if="activeViewerTab === 'video'" class="student-learning-v2-viewer-panel">
              <div v-if="!hasVideoResource" class="student-learning-v2-viewer-empty">
                <div class="empty-icon">🎥</div>
                <p>当前知识点暂无视频讲解</p>
              </div>
              <div v-else class="student-learning-v2-video-shell">
                <video
                  v-if="selectedResource"
                  class="student-learning-v2-resource-video"
                  :key="selectedResource"
                  :src="selectedResource"
                  controls
                  playsinline
                  preload="metadata"
                  @loadstart="handleVideoLoadStart"
                  @canplay="handleVideoCanPlay"
                  @error="handleVideoError"
                >
                  您的浏览器不支持视频播放
                </video>
                <div v-if="videoLoading" class="video-loading-overlay">
                  <div class="loading-spinner"></div>
                  <p>视频加载中...</p>
                </div>
                <div v-if="videoError" class="video-error-overlay">
                  <p>{{ videoError }}</p>
                  <button type="button" @click="retryVideo">重试</button>
                </div>
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
          </div>
        </div>

        <!-- 个性化路径视图 -->
        <div v-else>
          <Suspense>
            <template #default>
              <PersonalizedPathPanel />
            </template>
            <template #fallback>
              <div class="student-learning-v2-loading-state">
                <div class="loading-spinner"></div>
                <p>加载个性化路径中...</p>
              </div>
            </template>
          </Suspense>
        </div>
      </section>

      <!-- 右栏：AI 助手 -->
      <aside class="student-learning-v2-right-panel">
        <div class="student-learning-v2-assistant-header">
          <h3>🤖 AI 助教</h3>
        </div>
        
        <SegmentedTabs v-model="assistantTab" :tabs="assistantTabs" />

        <div v-if="assistantTab === 'chat'" class="assistant-panel assistant-panel--chat">
          <course-chat-dialog :student-id="currentUser?.user_id?.toString()" :course-id="currentCourseId"/>
        </div>

        <div v-else-if="assistantTab === 'summary'" class="assistant-panel">
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
            {{ summaryLoading ? "生成中..." : "生成总结" }}
          </button>
          <div class="assistant-output" :class="{ 'error-state': summaryError }">
            {{ summaryError || summaryText || "点击上方按钮生成知识总结" }}
          </div>
        </div>

        <div v-else class="assistant-panel">
          <div class="quiz-card-vue">
            <h3>在线测验</h3>
            <p>围绕当前知识点快速开始一次测验，检验学习效果。</p>
            <button type="button" class="primary-link button-like full-width" @click="openQuiz">
              开始测验
            </button>
          </div>
          <div class="stack-list">
            <button type="button" class="list-card learning-plan-card" @click="quickQuiz('大数据基础概念')">
              大数据基础概念
            </button>
            <button type="button" class="list-card learning-plan-card" @click="quickQuiz('数据获取')">
              数据获取
            </button>
            <button type="button" class="list-card learning-plan-card" @click="quickQuiz('数据预处理')">
              数据预处理
            </button>
          </div>
        </div>
      </aside>
    </section>
  </div>
</template>

<script setup lang="ts">
import { computed, defineAsyncComponent, nextTick, onMounted, ref } from "vue";
import { useRoute, useRouter } from "vue-router";
import SegmentedTabs from "../../components/ui/SegmentedTabs.vue";
import {
  generateCourseSummary,
  selectPdfForChat,
  sendCourseChat,
} from "../../api/client";
import { homeworkListAssignmentsForNode } from "../../api/homework";
import {CourseNode, KnowledgeGraphResponse} from "../../types/knowledgeGraph";
import type { HomeworkAssignment } from "../../types/homework";
import {fetchKnowledgeGraph} from "../../api/knowledgeGraph";
import CourseChatDialog from "./components/CourseChatDialog.vue";
import {User} from "../../types/login";
import {fetchCurrentUser} from "../../api/login";
import {fetchCourseIdByName} from "../../api/5E";

// 懒加载个性化路径面板
const PersonalizedPathPanel = defineAsyncComponent(() => 
  import("./components/PersonalizedPathPanel.vue")
);

const currentUser:Ref<User|null>=ref(null)

type AssistantTab = "chat" | "summary" | "quiz";

const assistantTabs = [
  { label: "AI 助教", value: "chat" },
  { label: "总结", value: "summary" },
  { label: "测验", value: "quiz" },
];

const route = useRoute();
const router = useRouter();

// 页内模式切换
const activeMode = ref<"content" | "path">("content");

// Viewer tab 状态
type ViewerTab = "pdf" | "video" | "quiz" | "summary";
const activeViewerTab = ref<ViewerTab>("pdf");

const assistantTab = ref<AssistantTab>("chat");
const graph = ref<KnowledgeGraphResponse | null>(null);
const graphLoading = ref(true);
const graphError = ref("");
const openChapters = ref<string[]>([]);

const currentNode = ref<CourseNode | null>(null);
const currentResources = ref<string[]>([]);
const selectedResource = ref("");
const selectedResourceIndex = ref<number | null>(null);
const nodeLoading = ref(false);

// 面包屑相关
const currentCourseName = ref("大数据基础");
const currentCourseId:Ref<string|undefined>=ref(undefined)
const currentChapterName = ref("当前章节");

// 本地状态
const isBookmarked = ref(false);
const isCompleted = ref(false);

// PDF 聊天绑定缓存
const boundPdfResources = ref<Set<string>>(new Set());

const chatMessages = ref<Array<{ role: "user" | "bot"; content: string }>>([
  { role: "bot", content: "你好，我是 AI 助教，有什么可以帮你的？" },
]);
const chatHistory = ref<Array<[string, string]>>([]);
const chatInput = ref("");
const chatSending = ref(false);
const chatScrollRef = ref<HTMLDivElement | null>(null);

const summaryTopic = ref("");
const summaryText = ref("");
const summaryError = ref("");
const summaryLoading = ref(false);

const videoLoading = ref(false);
const videoError = ref("");
const courseHomework = ref<HomeworkAssignment[]>([]);
const courseHomeworkLoading = ref(false);
const courseHomeworkError = ref("");
const nodeHomework = ref<HomeworkAssignment[]>([]);
const nodeHomeworkLoading = ref(false);
const nodeHomeworkError = ref("");

const chapterNodes = computed(() => graph.value?.children ?? []);
const selectedResourceType = computed(() => {
  return selectedResource.value.startsWith("http://") || selectedResource.value.startsWith("https://")
    ? "video"
    : "pdf";
});
function normalizePdfResourcePath(path: string) {
  return path.replace(/\\/g, "/").replace(/^\/+/, "").replace(/^backend\/data\//, "data/");
}

function encodePdfResourcePath(path: string) {
  return normalizePdfResourcePath(path)
    .split("/")
    .map((segment) => encodeURIComponent(segment))
    .join("/");
}

const pdfViewerUrl = computed(() =>
  selectedResource.value
    ? `/api/pdf/${encodePdfResourcePath(selectedResource.value)}#toolbar=0&navpanes=0&zoom=page-width`
    : "",
);
const heroBadges = computed(() => [
  `章节 ${chapterNodes.value.length}`,
  `当前节点 ${currentNode.value?.name ?? "未选择"}`,
  `资料 ${currentResources.value.length}`,
]);

// 资源分类
const pdfResources = computed(() => 
  currentResources.value.filter(r => !r.startsWith("http://") && !r.startsWith("https://"))
);
const videoResources = computed(() => 
  currentResources.value.filter(r => r.startsWith("http://") || r.startsWith("https://"))
);
const hasPdfResource = computed(() => pdfResources.value.length > 0);
const hasVideoResource = computed(() => videoResources.value.length > 0);

function switchViewerTab(tab: ViewerTab) {
  activeViewerTab.value = tab;

  if (tab === "pdf" && hasPdfResource.value) {
    const resource = pdfResources.value[0];
    selectResource(resource, currentResources.value.indexOf(resource));
  }

  if (tab === "video" && hasVideoResource.value) {
    const resource = videoResources.value[0];
    selectResource(resource, currentResources.value.indexOf(resource));
  }
}

function sectionNodes(chapter: CourseNode) {
  return chapter.grandchildren ?? [];
}

function knowledgeNodes(section: CourseNode) {
  return section["great-grandchildren"] ?? [];
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
  return normalizeResources(node).length > 0;
}

function getNodeFlag(node: CourseNode) {
  const flag = (node as { flag?: unknown }).flag;
  if (flag === "done" || flag === "completed") return "✓";
  if (flag === "current" || flag === "in-progress") return "●";
  return "";
}

async function selectNode(node: CourseNode) {
  // 设置加载状态
  nodeLoading.value = true;
  
  // 立即更新UI状态，给用户即时反馈
  currentNode.value = node;
  const {course_id} = await fetchCourseIdByName(currentNode.value.name);
  currentCourseId.value=course_id;
  currentResources.value = normalizeResources(node);
  summaryTopic.value = node.name;
  summaryText.value = "";
  summaryError.value = "";
  nodeHomework.value = [];
  nodeHomeworkError.value = "";
  
  // 清空之前的资源选择
  selectedResource.value = "";
  selectedResourceIndex.value = null;
  
  // 根据资源类型设置默认 viewer tab
  if (videoResources.value.length > 0) {
    activeViewerTab.value = "video";
  } else if (pdfResources.value.length > 0) {
    activeViewerTab.value = "pdf";
  } else {
    activeViewerTab.value = "summary";
  }
  
  // 更新面包屑（简化版，基于当前节点）
  updateBreadcrumb(node);
  
  loadHomeworkForNode(node).catch(() => {});
  
  // 异步加载资源，不阻塞UI
  if (currentResources.value.length > 0) {
    // 使用 nextTick 确保UI先更新
    await nextTick();
    const firstResource = activeViewerTab.value === "video" && videoResources.value.length > 0
      ? videoResources.value[0]
      : pdfResources.value[0] || currentResources.value[0];
    const firstIndex = currentResources.value.indexOf(firstResource);
    selectResource(firstResource, firstIndex).catch(err => {
      console.error('资源加载失败:', err);
    }).finally(() => {
      nodeLoading.value = false;
    });
  } else {
    nodeLoading.value = false;
  }
}

function updateBreadcrumb(node: CourseNode) {
  // 简化版面包屑，基于当前节点
  // 如果有完整的父级信息可以在这里扩展
  currentCourseName.value = "大数据基础";
  
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

async function loadHomeworkForNode(node: CourseNode) {
  nodeHomeworkLoading.value = true;
  nodeHomeworkError.value = "";
  try {
    const res = await homeworkListAssignmentsForNode({
      course_id: "course_big_data",
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
      course_id: "course_big_data",
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
      course_id: "course_big_data",
      node_name: currentNode.value.name,
    },
  });
}

function goHomeworkForCourse() {
  router.push({
    name: "student-homework",
    query: {
      course_id: "course_big_data",
    },
  });
}

function goHomeworkDetail(assignmentId: string) {
  router.push({ name: "student-homework-detail", params: { assignmentId } });
}

async function selectResource(resource: string, index: number) {
  selectedResource.value = resource;
  selectedResourceIndex.value = index;
  videoLoading.value = false;
  videoError.value = "";
  // PDF 不再立即绑定，改为懒加载策略
}

function handleVideoLoadStart() {
  videoLoading.value = true;
  videoError.value = "";
}

function handleVideoCanPlay() {
  videoLoading.value = false;
  videoError.value = "";
}

function handleVideoError(event: Event) {
  videoLoading.value = false;
  const target = event.target as HTMLVideoElement;
  const error = target.error;
  
  if (error) {
    switch (error.code) {
      case error.MEDIA_ERR_ABORTED:
        videoError.value = "视频加载被中止";
        break;
      case error.MEDIA_ERR_NETWORK:
        videoError.value = "网络错误，无法加载视频";
        break;
      case error.MEDIA_ERR_DECODE:
        videoError.value = "视频解码失败";
        break;
      case error.MEDIA_ERR_SRC_NOT_SUPPORTED:
        videoError.value = "不支持的视频格式或视频源不可用";
        break;
      default:
        videoError.value = "视频加载失败";
    }
  } else {
    videoError.value = "视频加载失败，请检查视频链接是否有效";
  }
}

function retryVideo() {
  videoError.value = "";
  videoLoading.value = true;
  // 强制重新加载视频
  const resource = selectedResource.value;
  selectedResource.value = "";
  setTimeout(() => {
    selectedResource.value = resource;
  }, 100);
}

function resourceLabel(resource: string, index: number) {
  const isVideo = resource.startsWith("http://") || resource.startsWith("https://");
  if (isVideo) {
    return `视频 ${index + 1}`;
  }
  const fileName = resource.split("/").pop() ?? `资料 ${index + 1}`;
  return fileName.replace(/\.pdf$/i, "");
}

async function submitChat() {
  const message = chatInput.value.trim();
  if (!message) return;
  
  // 懒加载：如果当前是 PDF 资源且尚未绑定，先绑定
  if (selectedResourceType.value === "pdf" && selectedResource.value && !boundPdfResources.value.has(selectedResource.value)) {
    try {
      await selectPdfForChat(normalizePdfResourcePath(selectedResource.value));
      boundPdfResources.value.add(selectedResource.value);
    } catch (err) {
      console.warn('PDF 聊天绑定失败，但不影响发送消息:', err);
    }
  }
  
  // 添加用户消息
  chatMessages.value.push({ role: "user", content: message });
  chatInput.value = "";
  
  // 滚动到底部
  await scrollToBottom();
  
  // 立即添加"正在思考中..."的占位消息
  const thinkingMessageIndex = chatMessages.value.length;
  chatMessages.value.push({ role: "bot", content: "正在思考中..." });
  
  // 再次滚动到底部显示思考消息
  await scrollToBottom();
  
  chatSending.value = true;
  
  try {
    const result = await sendCourseChat({
      message,
      history: chatHistory.value,
    });
    
    // 替换"正在思考中..."为实际回答
    chatMessages.value[thinkingMessageIndex] = {
      role: "bot",
      content: result.response || "暂未生成回答。"
    };
    
    chatHistory.value.push([message, result.response || ""]);
    
    // 滚动到底部显示完整回答
    await scrollToBottom();
  } catch (error) {
    // 替换"正在思考中..."为错误消息
    chatMessages.value[thinkingMessageIndex] = {
      role: "bot",
      content: error instanceof Error ? error.message : "抱歉，当前回答失败，请稍后再试。"
    };
    
    await scrollToBottom();
  } finally {
    chatSending.value = false;
  }
}

async function scrollToBottom() {
  await nextTick();
  if (chatScrollRef.value) {
    chatScrollRef.value.scrollTop = chatScrollRef.value.scrollHeight;
  }
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
    },
  });
}

function quickQuiz(topic: string) {
  router.push({
    path: "/student/quiz",
    query: {
      topic,
      node: topic,
    },
  });
}

// 导航方法（占位）
function navigatePrevNode() {
  console.log("上一个节点（待实现）");
  // 可以基于 flattenSelectableNodes 实现节点遍历
}

function navigateNextNode() {
  console.log("下一个节点（待实现）");
  // 可以基于 flattenSelectableNodes 实现节点遍历
}

function toggleBookmark() {
  isBookmarked.value = !isBookmarked.value;
  console.log(`收藏状态: ${isBookmarked.value ? "已收藏" : "未收藏"}`);
}

function openNotes() {
  console.log("打开笔记（待实现）");
}

function exportNotes() {
  if (summaryText.value) {
    // 简单的复制到剪贴板
    navigator.clipboard.writeText(summaryText.value).then(() => {
      alert("总结内容已复制到剪贴板");
    }).catch(() => {
      console.log("导出笔记:", summaryText.value);
      alert("导出笔记功能（前端占位）");
    });
  } else {
    alert("暂无总结内容可导出");
  }
}

function markComplete() {
  isCompleted.value = true;
  alert(`已标记"${currentNode.value?.name}"为完成状态（本地状态）`);
  console.log("标记完成（前端占位，未写入后端）");
}

async function loadGraph() {
  graphLoading.value = true;
  graphError.value = "";
  try {
    graph.value = await fetchKnowledgeGraph();
    openChapters.value = (graph.value.children ?? []).slice(0, 1).map((item) => item.name);
    const targetNodeName = typeof route.query.node === "string" ? route.query.node : "";
    if (targetNodeName) {
      const target = flattenSelectableNodes(graph.value.children ?? []).find((item) => item.name === targetNodeName);
      if (target) {
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

onMounted(async ()=>{
  await loadGraph();
  currentUser.value=await fetchCurrentUser();
});
</script>

<style scoped>
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

/* Viewer Tabs */
.student-learning-v2-viewer-tabs {
  display: flex;
  border-bottom: 1px solid #e4e7ed;
  padding: 0 20px;
  background: #fafafa;
}

.student-learning-v2-viewer-tab {
  padding: 12px 20px;
  border: none;
  background: none;
  cursor: pointer;
  font-size: 14px;
  color: #606266;
  border-bottom: 2px solid transparent;
  transition: all 0.3s;
  font-weight: 500;
}

.student-learning-v2-viewer-tab:hover {
  color: #409eff;
  background: rgba(64, 158, 255, 0.05);
}

.student-learning-v2-viewer-tab.active {
  color: #409eff;
  border-bottom-color: #409eff;
  background: #fff;
}

/* Viewer Panel */
.student-learning-v2-viewer-panel {
  flex: 1;
  overflow: auto;
  display: flex;
  flex-direction: column;
  background: #f5f7fa;
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

/* 资源选择器 */
.student-learning-v2-resource-selector {
  padding: 16px 20px;
  background: #fff;
  border-bottom: 1px solid #e4e7ed;
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.student-learning-v2-resource-frame {
  width: 100%;
  flex: 1;
  border: none;
  background: #fff;
  min-height: 600px;
}

.student-learning-v2-video-shell {
  position: relative;
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 260px;
  max-height: 460px;
  margin: 16px 20px;
  overflow: hidden;
  background: #000;
  border-radius: 8px;
}

.student-learning-v2-resource-video {
  width: 100%;
  max-width: 100%;
  max-height: 460px;
  background: #000;
  object-fit: contain;
}

.student-learning-v2-video-shell .video-loading-overlay,
.student-learning-v2-video-shell .video-error-overlay {
  position: absolute;
  inset: 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  background: rgba(0, 0, 0, 0.62);
  color: #fff;
  text-align: center;
}

.student-learning-v2-video-shell .video-loading-overlay p,
.student-learning-v2-video-shell .video-error-overlay p {
  margin: 8px 0 0;
  font-size: 14px;
}

.student-learning-v2-video-shell .video-error-overlay button {
  margin-top: 12px;
  padding: 7px 16px;
  border: 1px solid rgba(255, 255, 255, 0.75);
  border-radius: 4px;
  background: rgba(255, 255, 255, 0.12);
  color: #fff;
  cursor: pointer;
}

/* 测验入口 */
.student-learning-v2-quiz-entry {
  max-width: 600px;
  margin: 60px auto;
  padding: 40px;
  background: #fff;
  border-radius: 8px;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.1);
  text-align: center;
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
  max-width: 800px;
  margin: 40px auto;
  padding: 40px;
  background: #fff;
  border-radius: 8px;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.1);
}

.student-learning-v2-summary-output {
  margin-top: 24px;
  padding: 20px;
  background: #f5f7fa;
  border-radius: 8px;
  min-height: 200px;
  font-size: 14px;
  line-height: 1.8;
  color: #606266;
  white-space: pre-wrap;
}

.student-learning-v2-summary-output.error-state {
  background: #fef0f0;
  color: #f56c6c;
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

/* 懒加载状态 */
.student-learning-v2-loading-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 60px 20px;
  color: #909399;
}

.student-learning-v2-loading-state .loading-spinner {
  width: 40px;
  height: 40px;
  border: 3px solid #e4e7ed;
  border-top-color: #409eff;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
  margin-bottom: 16px;
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}

.student-learning-v2-loading-state p {
  font-size: 14px;
}
</style>
