<template>
  <div class="course-shell">
    <PageHero
      eyebrow="Course Content"
      title="课程内容与 AI 助教"
      description="在同一页面中浏览课程目录、查看资料内容、向 AI 助教提问，并围绕当前知识点生成总结与测验。"
      tone="default"
    />

    <section class="course-grid">
      <aside class="card-panel course-sidebar">
        <div class="section-head">
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
                  {{ section.name }}
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
                      {{ node.name }}
                    </button>
                  </li>
                </ul>
              </li>
            </ul>
          </li>
        </ul>
      </aside>

      <section class="card-panel course-center">
        <section v-if="!currentNode" class="question-card node-homework-panel">
          <div class="section-head compact">
            <strong>本课程作业</strong>
            <button type="button" class="ghost-btn small" @click="goHomeworkForCourse">查看全部</button>
          </div>
          <div v-if="courseHomeworkLoading" class="muted">加载中...</div>
          <div v-else-if="courseHomeworkError" class="muted">{{ courseHomeworkError }}</div>
          <div v-else-if="!courseHomework.length" class="muted">当前课程暂无已发布作业</div>
          <ul v-else class="stack-list">
            <li v-for="item in courseHomework" :key="item.id" class="list-card learning-plan-card">
              <div>
                <strong>{{ item.title }}</strong>
                <div class="muted">{{ item.assignment_type }} · 章节 {{ item.node_name || "未关联" }} · 截止 {{ item.due_at ? new Date(item.due_at).toLocaleString() : "未设置" }}</div>
              </div>
              <button type="button" class="ghost-btn small" @click="goHomeworkDetail(item.id)">去提交</button>
            </li>
          </ul>
        </section>
        <div v-if="!currentNode" class="course-welcome">
          <div class="welcome-badge">课程内容</div>
          <h1>选择一个章节开始学习</h1>
          <p>左侧目录用于浏览课程知识点，中间区域展示资源，右侧可以直接和 AI 助教对话。</p>
        </div>
        <template v-else>
          <div class="resource-header-vue">
            <div>
              <div class="resource-kicker">当前学习节点</div>
              <h2>{{ currentNode.name }}</h2>
            </div>
          </div>

          <div class="resource-chip-list">
            <button
              v-for="(resource, index) in currentResources"
              :key="`${resource}-${index}`"
              type="button"
              class="resource-chip"
              :class="{ active: selectedResourceIndex === index }"
              @click="selectResource(resource, index)"
            >
              {{ resourceLabel(resource, index) }}
            </button>
            <span v-if="currentResources.length === 0" class="muted">该节点暂时没有资料</span>
          </div>

          <section class="question-card node-homework-panel">
            <div class="section-head compact">
              <strong>本章节作业</strong>
              <button type="button" class="ghost-btn small" @click="goHomeworkForCurrentNode">查看全部</button>
            </div>
            <div v-if="nodeHomeworkLoading" class="muted">加载中...</div>
            <div v-else-if="nodeHomeworkError" class="muted">{{ nodeHomeworkError }}</div>
            <div v-else-if="!nodeHomework.length" class="muted">当前章节暂无已发布作业</div>
            <ul v-else class="stack-list">
              <li v-for="item in nodeHomework" :key="item.id" class="list-card learning-plan-card">
                <div>
                  <strong>{{ item.title }}</strong>
                  <div class="muted">{{ item.assignment_type }} · 截止 {{ item.due_at ? new Date(item.due_at).toLocaleString() : "未设置" }}</div>
                </div>
                <button type="button" class="ghost-btn small" @click="goHomeworkDetail(item.id)">去提交</button>
              </li>
            </ul>
          </section>

          <div class="resource-viewer-panel">
            <div v-if="!selectedResource && currentResources.length === 0" class="resource-placeholder">
              该节点暂无学习资料，请选择其他知识点
            </div>
            <div v-else-if="!selectedResource" class="resource-placeholder">请选择一个资料进行查看</div>
            <iframe
              v-else-if="selectedResourceType === 'pdf'"
              class="resource-frame"
              :src="pdfViewerUrl"
              title="课程 PDF 预览"
            />
            <video
              v-else
              class="resource-video"
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
        </template>
      </section>

      <aside class="card-panel course-assistant">
        <SegmentedTabs v-model="assistantTab" :tabs="assistantTabs" />

        <div v-if="assistantTab === 'chat'" class="assistant-panel assistant-panel--chat">
          <div class="assistant-chat-head">
            <div>
              <strong>{{ currentNode?.name || "AI 助教" }}</strong>
              <p>{{ selectedResource ? "已关联当前资料，可结合内容回答。" : "先选择课程资料，再提问会更准确。" }}</p>
            </div>
          </div>
          <div class="chat-scroll" ref="chatScrollRef">
            <div
              v-for="(message, index) in chatMessages"
              :key="`${message.role}-${index}`"
              class="chat-bubble"
              :class="message.role"
            >
              <div class="chat-role">{{ message.role === "user" ? "我" : "AI 助教" }}</div>
              <div 
                class="chat-text" 
                :class="{ thinking: message.content === '正在思考中...' }"
              >
                {{ message.content }}
              </div>
            </div>
          </div>
          <div class="chat-composer">
            <textarea
              v-model.trim="chatInput"
              placeholder="输入你的问题..."
              rows="3"
              @keydown.enter.exact.prevent="submitChat"
            ></textarea>
            <button
              type="button"
              class="primary-link button-like"
              @click="submitChat"
              :disabled="chatSending || !chatInput.trim()"
            >
              {{ chatSending ? "发送中..." : "发送" }}
            </button>
          </div>
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
import { computed, nextTick, onMounted, ref } from "vue";
import { useRoute, useRouter } from "vue-router";
import PageHero from "../../components/ui/PageHero.vue";
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


type AssistantTab = "chat" | "summary" | "quiz";

const assistantTabs = [
  { label: "AI 助教", value: "chat" },
  { label: "总结", value: "summary" },
  { label: "测验", value: "quiz" },
];

const route = useRoute();
const router = useRouter();
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
const pdfViewerUrl = computed(() =>
  selectedResource.value ? `/api/pdf/${encodeURIComponent(selectedResource.value)}` : "",
);
const heroBadges = computed(() => [
  `章节 ${chapterNodes.value.length}`,
  `当前节点 ${currentNode.value?.name ?? "未选择"}`,
  `资料 ${currentResources.value.length}`,
]);

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

async function selectNode(node: CourseNode) {
  // 设置加载状态
  nodeLoading.value = true;
  
  // 立即更新UI状态，给用户即时反馈
  currentNode.value = node;
  currentResources.value = normalizeResources(node);
  summaryTopic.value = node.name;
  summaryText.value = "";
  summaryError.value = "";
  nodeHomework.value = [];
  nodeHomeworkError.value = "";
  
  // 清空之前的资源选择
  selectedResource.value = "";
  selectedResourceIndex.value = null;
  loadHomeworkForNode(node).catch(() => {});
  
  // 异步加载资源，不阻塞UI
  if (currentResources.value.length > 0) {
    // 使用 nextTick 确保UI先更新
    await nextTick();
    selectResource(currentResources.value[0], 0).catch(err => {
      console.error('资源加载失败:', err);
    }).finally(() => {
      nodeLoading.value = false;
    });
  } else {
    nodeLoading.value = false;
  }
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
  
  if (selectedResourceType.value === "pdf") {
    // PDF选择API调用，即使失败也不影响查看器
    selectPdfForChat(resource).catch(err => {
      console.warn('PDF选择提示失败，但不影响查看:', err);
    });
  } else {
    // 视频资源，显示加载状态
    videoLoading.value = true;
  }
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

onMounted(loadGraph);
</script>
