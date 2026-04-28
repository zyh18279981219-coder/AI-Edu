<template>
  <div class="course-shell">
    <PageHero
      eyebrow="Course Content"
      title="课程内容与 AI 助教"
      description="在同一页面中浏览课程目录、查看资料内容、向 AI 助教提问，并围绕当前知识点生成总结与测验。"
      :badges="heroBadges"
      tone="default"
    />

    <section class="course-grid full-width-center">
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

      <div class="course-center card-panel" >
       <course-chat-dialog lesson-id="lesson_101" student-id="test_user_002"/>
      </div>
    </section>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import { useRoute, useRouter } from "vue-router";
import PageHero from "../../components/ui/PageHero.vue";
import SegmentedTabs from "../../components/ui/SegmentedTabs.vue";
import {
  generateCourseSummary,
  selectPdfForChat,
  sendCourseChat,
} from "../../api/client";
import {CourseNode, KnowledgeGraphResponse} from "../../types/knowledgeGraph";
import {fetchKnowledgeGraph} from "../../api/knowledgeGraph";
import {fetchCurrentUser} from "../../api/login";
import CourseChatDialog from "./components/CourseChatDialog.vue";

const currentUser = ref<{
  username: string;
  user_type: string;
  user_data: Record<string, unknown>;
} | null>(null);

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

const chatMessages = ref<Array<{ role: "user" | "bot"; content: string }>>([
  { role: "bot", content: "你好，我是 AI 助教，有什么可以帮你的？" },
]);
const chatHistory = ref<Array<[string, string]>>([]);
const chatInput = ref("");
const chatSending = ref(false);

const summaryTopic = ref("");
const summaryText = ref("");
const summaryError = ref("");
const summaryLoading = ref(false);

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
  currentNode.value = node;
  currentResources.value = normalizeResources(node);
  summaryTopic.value = node.name;
  summaryText.value = "";
  summaryError.value = "";
  if (currentResources.value.length > 0) {
    await selectResource(currentResources.value[0], 0);
  } else {
    selectedResource.value = "";
    selectedResourceIndex.value = null;
  }
}

async function selectResource(resource: string, index: number) {
  selectedResource.value = resource;
  selectedResourceIndex.value = index;
  if (selectedResourceType.value === "pdf") {
    try {
      await selectPdfForChat(resource);
    } catch {
      // Keep viewer usable even if selection hint fails.
    }
  }
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
  chatMessages.value.push({ role: "user", content: message });
  chatInput.value = "";
  chatSending.value = true;
  try {
    const result = await sendCourseChat({
      message,
      history: chatHistory.value,
    });
    chatMessages.value.push({ role: "bot", content: result.response || "暂未生成回答。" });
    chatHistory.value.push([message, result.response || ""]);
  } catch (error) {
    chatMessages.value.push({
      role: "bot",
      content: error instanceof Error ? error.message : "抱歉，当前回答失败，请稍后再试。",
    });
  } finally {
    chatSending.value = false;
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
    path: "/quiz",
    query: {
      topic,
      node: topic,
    },
  });
}

function quickQuiz(topic: string) {
  router.push({
    path: "/quiz",
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
}

onMounted(async ()=>{
  loadGraph();
  currentUser.value=await fetchCurrentUser();
});
</script>

<style scoped>
.full-width-center {
  grid-template-columns: 272px minmax(0, 1fr);
}
</style>
