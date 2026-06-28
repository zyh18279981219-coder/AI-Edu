<template>
  <div class="student-learning-v2-path-panel">
    <div class="student-learning-v2-path-header">
      <div>
        <h2>🎯 个性化学习路径</h2>
        <p class="muted">基于你的学习数据，系统为你推荐以下学习顺序</p>
      </div>
      <button class="ghost-btn" type="button" :disabled="loading" @click="handleRegenerate">
        {{ loading ? "生成中..." : "重新规划" }}
      </button>
    </div>

    <div v-if="loading" class="state-card">正在生成个性化学习路径...</div>
    <div v-else-if="error" class="state-card error-state">{{ error }}</div>

    <template v-else-if="pathData">
      <div v-if="pathData.llm_advice" class="student-learning-v2-path-advice">
        <div class="student-learning-v2-path-advice-header"><strong>💡 AI 学习建议</strong></div>
        <div class="student-learning-v2-path-advice-content">{{ pathData.llm_advice }}</div>
      </div>

      <div v-if="pathData.llm_order_reason" class="student-learning-v2-path-reason">
        <div class="student-learning-v2-path-reason-header"><strong>🔍 排序依据</strong></div>
        <div class="student-learning-v2-path-reason-content">{{ pathData.llm_order_reason }}</div>
      </div>

      <div class="student-learning-v2-path-controls">
        <label>
          <input type="radio" value="priority" v-model="sortMode" />
          按优先级排序
        </label>
        <label>
          <input type="radio" value="mastery" v-model="sortMode" />
          按掌握度排序
        </label>
      </div>

      <div v-if="sortedNodes.length" class="student-learning-v2-path-nodes">
        <div class="student-learning-v2-path-nodes-header">
          <strong>需要加强的知识点（{{ sortedNodes.length }}个）</strong>
        </div>
        <div class="student-learning-v2-path-node-list">
          <article
            v-for="(node, index) in sortedNodes"
            :key="node.node_id"
            class="student-learning-v2-path-node-item"
          >
            <div class="student-learning-v2-path-node-rank">{{ index + 1 }}</div>
            <div class="student-learning-v2-path-node-content">
              <div class="student-learning-v2-path-node-title">{{ node.node_id }}</div>
              <div class="student-learning-v2-path-node-meta">
                <span>掌握度 {{ formatScore(node.mastery_score) }}%</span>
                <span>优先级 {{ node.priority || node.llm_priority || "-" }}</span>
                <span class="student-learning-v2-path-status" :class="`is-${pathNodeStatus(node.node_id).status}`">
                  {{ pathStatusLabel(pathNodeStatus(node.node_id).status) }}
                </span>
              </div>
              <div v-if="pathNodeStatus(node.node_id).started_at || pathNodeStatus(node.node_id).completed_at" class="student-learning-v2-path-node-time">
                <span v-if="pathNodeStatus(node.node_id).started_at">开始：{{ formatPathTime(pathNodeStatus(node.node_id).started_at) }}</span>
                <span v-if="pathNodeStatus(node.node_id).completed_at">完成：{{ formatPathTime(pathNodeStatus(node.node_id).completed_at) }}</span>
              </div>

              <div v-if="node.resources?.length" class="student-learning-v2-path-node-resources">
                <article
                  v-for="resource in node.resources"
                  :key="resource.url"
                  class="student-learning-v2-resource-card"
                  :class="{ 'is-previewable': canPreview(resource) }"
                  :role="canPreview(resource) ? 'button' : undefined"
                  :tabindex="canPreview(resource) ? 0 : undefined"
                  @click="canPreview(resource) && openResource(resource)"
                  @keydown.enter.prevent="canPreview(resource) && openResource(resource)"
                  @keydown.space.prevent="canPreview(resource) && openResource(resource)"
                >
                  <div class="student-learning-v2-resource-card-top">
                    <span class="student-learning-v2-resource-kind">{{ resourceTypeLabel(resource) }}</span>
                    <span v-if="resource.score != null" class="student-learning-v2-resource-score">
                      {{ Math.round(resource.score * 100) }}%
                    </span>
                  </div>
                  <h4>{{ resource.title || resource.url }}</h4>
                  <p v-if="resource.reason" class="student-learning-v2-resource-reason">{{ resource.reason }}</p>
                  <div class="student-learning-v2-resource-actions">
                    <button
                      v-if="canPreview(resource)"
                      type="button"
                      class="student-learning-v2-resource-watch"
                      @click.stop="openResource(resource)"
                    >
                      {{ previewButtonLabel(resource) }}
                    </button>
                    <a
                      v-else
                      :href="resource.url"
                      target="_blank"
                      rel="noopener noreferrer"
                      @click.stop
                    >
                      打开原链接
                    </a>
                  </div>
                </article>
              </div>
              <div class="student-learning-v2-path-node-actions">
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
                  class="student-learning-v2-resource-watch"
                  :disabled="isPathStatusBusy(node.node_id) || pathNodeStatus(node.node_id).status === 'completed'"
                  @click="handlePathStatusUpdate(node.node_id, 'completed', node.mastery_score)"
                >
                  {{ pathNodeStatus(node.node_id).status === 'completed' ? '已完成' : '标记完成' }}
                </button>
              </div>
            </div>
          </article>
        </div>
      </div>

      <div v-else class="student-learning-v2-path-empty">
        <div class="student-learning-v2-path-empty-icon">🎉</div>
        <div class="student-learning-v2-path-empty-text">暂无需要加强的知识点，继续保持！</div>
      </div>
    </template>

    <div v-if="activeResource" class="student-learning-v2-video-modal-mask" @click.self="closeResource">
      <section class="student-learning-v2-video-modal">
        <div class="student-learning-v2-video-modal-head">
          <h3>{{ activeResource.title || "推荐资源" }}</h3>
          <button type="button" class="ghost-btn" @click="closeResource">关闭</button>
        </div>

        <iframe
          v-if="activeResourcePreview.mode === 'video-embed'"
          :src="activeResourcePreview.url"
          allowfullscreen
          scrolling="no"
          referrerpolicy="no-referrer-when-downgrade"
          class="student-learning-v2-video-modal-frame"
        ></iframe>

        <div v-else-if="activeResourcePreview.mode === 'video-stream'" class="student-learning-v2-video-player-shell">
          <video
            ref="videoElementRef"
            class="student-learning-v2-video-player"
            controls
            playsinline
            preload="metadata"
          ></video>
          <div v-if="playerError" class="student-learning-v2-video-player-error">
            <p>{{ playerError }}</p>
            <a :href="activeResource.url" target="_blank" rel="noopener noreferrer">打开原链接</a>
          </div>
        </div>

        <iframe
          v-else-if="activeResourcePreview.mode === 'document'"
          :src="activeResourcePreview.url"
          allowfullscreen
          referrerpolicy="no-referrer-when-downgrade"
          class="student-learning-v2-video-modal-frame student-learning-v2-document-frame"
        ></iframe>

        <div v-else class="student-learning-v2-preview-fallback">
          <p>暂不支持在弹窗内预览该资源。</p>
          <a :href="activeResource.url" target="_blank" rel="noopener noreferrer">打开原链接</a>
        </div>
      </section>
    </div>
  </div>
</template>

<script setup lang="ts">
import Hls from "hls.js";
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from "vue";
import { fetchCurrentUser } from "../../../api/login";
import { fetchCurrentLearningPath, generateLearningPath, updateLearningPathNodeStatus } from "../../../api/student";
import type {
  LearningPathNodeStatus,
  LearningPathNodeStatusValue,
  LearningPathResponse,
  LearningPathResource,
} from "../../../types/student";

const loading = ref(false);
const error = ref("");
const pathData = ref<LearningPathResponse | null>(null);
const sortMode = ref<"priority" | "mastery">("priority");
const activeResource = ref<LearningPathResource | null>(null);
const videoElementRef = ref<HTMLVideoElement | null>(null);
const playerError = ref("");
const currentUsername = ref("");
const pathStatusUpdating = ref<Record<string, boolean>>({});
let hlsInstance: Hls | null = null;

type ResourcePreviewMode = "video-embed" | "video-stream" | "document" | "external";

const activeResourcePreview = computed<{ mode: ResourcePreviewMode; url: string }>(() => {
  if (!activeResource.value) {
    return { mode: "external", url: "" };
  }
  return getResourcePreview(activeResource.value);
});

const sortedNodes = computed(() => {
  const sourceNodes = pathData.value?.formal_path_nodes?.length
    ? pathData.value.formal_path_nodes
    : pathData.value?.weak_nodes ?? [];
  const nodes = [...sourceNodes];
  return sortMode.value === "priority"
    ? nodes.sort((a, b) => (a.sequence_order ?? a.llm_priority ?? a.priority ?? 999) - (b.sequence_order ?? b.llm_priority ?? b.priority ?? 999))
    : nodes.sort((a, b) => a.mastery_score - b.mastery_score);
});

const pathStatusMap = computed<Record<string, LearningPathNodeStatus>>(() => {
  const result: Record<string, LearningPathNodeStatus> = {};
  for (const item of pathData.value?.path_node_status ?? []) {
    if (!item.node_id) continue;
    result[item.node_id] = item;
  }
  return result;
});

function formatScore(value?: number) {
  return Number(value ?? 0).toFixed(1);
}

function defaultPathNodeStatus(nodeId: string): LearningPathNodeStatus {
  return {
    status_id: 0,
    plan_id: 0,
    username: currentUsername.value,
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

function canPreview(resource: LearningPathResource) {
  return getResourcePreview(resource).mode !== "external";
}

function previewButtonLabel(resource: LearningPathResource) {
  const preview = getResourcePreview(resource);
  if (preview.mode === "document") return "预览讲义";
  if (preview.mode === "video-embed") return "观看视频";
  if (preview.mode === "video-stream") return "播放视频";
  return "打开资源";
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

function pdfViewerUrl(resource: LearningPathResource) {
  return `/api/pdf/${encodePdfResourcePath(resource.url)}#toolbar=0&navpanes=0&zoom=page-width`;
}

function getResourcePreview(resource: LearningPathResource): { mode: ResourcePreviewMode; url: string } {
  const embeddedUrl = getEmbeddedVideoUrl(resource);
  if (isDocumentResource(resource)) {
    return { mode: "document", url: getDocumentPreviewUrl(resource) };
  }
  if (embeddedUrl) {
    return { mode: "video-embed", url: embeddedUrl };
  }
  if (isPlayableVideo(resource.url)) {
    return { mode: "video-stream", url: resource.url };
  }
  return { mode: "external", url: resource.url };
}

function isDocumentResource(resource: LearningPathResource) {
  return resource.type === "document" || isPdfUrl(resource.url);
}

function getDocumentPreviewUrl(resource: LearningPathResource) {
  if (/^https?:\/\//i.test(resource.url)) {
    return resource.url;
  }
  return pdfViewerUrl(resource);
}

function isPdfUrl(url: string) {
  return /\.pdf(?:$|[?#])/i.test(url);
}

function isPlayableVideo(url: string) {
  return /\.(m3u8|mp4|webm)(?:$|[?#])/i.test(url);
}

function getEmbeddedVideoUrl(resource: LearningPathResource) {
  if (resource.embed_url) {
    return resource.embed_url;
  }

  const youtubeVideoId = extractYouTubeVideoId(resource.url);
  if (youtubeVideoId) {
    return `https://www.youtube.com/embed/${encodeURIComponent(youtubeVideoId)}?rel=0`;
  }

  const bilibiliVideoId = extractBilibiliVideoId(resource.url);
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

function openResource(resource: LearningPathResource) {
  activeResource.value = resource;
}

function closeResource() {
  activeResource.value = null;
  playerError.value = "";
}

function destroyHls() {
  if (hlsInstance) {
    hlsInstance.destroy();
    hlsInstance = null;
  }
}

async function bindVideoPlayer(resource: LearningPathResource) {
  await nextTick();
  const video = videoElementRef.value;
  if (!video) return;

  destroyHls();
  playerError.value = "";
  video.removeAttribute("src");
  video.load();

  const url = resource.url || "";
  if (!url) {
    playerError.value = "没有可播放的视频地址。";
    return;
  }

  if (url.toLowerCase().includes(".m3u8")) {
    if (Hls.isSupported()) {
      hlsInstance = new Hls();
      hlsInstance.loadSource(url);
      hlsInstance.attachMedia(video);
      hlsInstance.on(Hls.Events.ERROR, (_event, data) => {
        if (data.fatal) {
          playerError.value = "视频流加载失败，可能是源站不允许播放。";
        }
      });
      return;
    }
    if (video.canPlayType("application/vnd.apple.mpegurl")) {
      video.src = url;
      return;
    }
    playerError.value = "当前浏览器不支持该视频流格式。";
    return;
  }

  video.src = url;
}

async function loadPath(forceGenerate = false) {
  loading.value = true;
  error.value = "";
  try {
    const user = await fetchCurrentUser();
    currentUsername.value = user.username;
    if (forceGenerate) {
      pathData.value = await generateLearningPath(user.username);
    } else {
      try {
        pathData.value = await fetchCurrentLearningPath(user.username);
      } catch (err: any) {
        if (err.response?.status === 404 || String(err?.message || "").includes("No learning path found")) {
          pathData.value = await generateLearningPath(user.username);
        } else {
          throw err;
        }
      }
    }
  } catch (err) {
    error.value = err instanceof Error ? err.message : "加载学习路径失败";
  } finally {
    loading.value = false;
  }
}

function handleRegenerate() {
  loadPath(true);
}

async function handlePathStatusUpdate(
  nodeId: string,
  status: "pending" | "in_progress" | "completed" | "skipped",
  masteryScore?: number,
) {
  if (!currentUsername.value) {
    const user = await fetchCurrentUser();
    currentUsername.value = user.username;
  }
  const current = pathNodeStatus(nodeId);
  pathStatusUpdating.value = { ...pathStatusUpdating.value, [nodeId]: true };
  error.value = "";
  try {
    const updated = await updateLearningPathNodeStatus(currentUsername.value, nodeId, {
      status,
      plan_id: current.plan_id || null,
      mastery_after: status === "completed" ? Math.max(Number(masteryScore ?? current.mastery_before ?? 0), 60) : null,
      payload: {
        source: "student_course_content_path_panel",
      },
    });
    mergePathNodeStatus(updated);
  } catch (err) {
    error.value = err instanceof Error ? err.message : "学习路径状态更新失败";
  } finally {
    const next = { ...pathStatusUpdating.value };
    delete next[nodeId];
    pathStatusUpdating.value = next;
  }
}

onMounted(() => {
  loadPath();
});

watch(activeResource, (resource) => {
  if (!resource || getResourcePreview(resource).mode !== "video-stream") {
    destroyHls();
    playerError.value = "";
    return;
  }
  void bindVideoPlayer(resource);
});

onBeforeUnmount(() => {
  destroyHls();
});
</script>

<style scoped>
.student-learning-v2-path-panel {
  display: grid;
  gap: 20px;
}

.student-learning-v2-path-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 16px;
  padding: 24px;
  background: linear-gradient(135deg, #ffffff 0%, #f8fbff 100%);
  border: 1px solid #e2e8f0;
  border-radius: 12px;
  box-shadow: 0 4px 12px rgba(15, 23, 42, 0.04);
}

.student-learning-v2-path-header h2 {
  margin: 0 0 8px;
  font-size: 24px;
  color: #0f172a;
}

.student-learning-v2-path-advice,
.student-learning-v2-path-reason {
  padding: 20px;
  background: #ffffff;
  border: 1px solid #e2e8f0;
  border-radius: 12px;
}

.student-learning-v2-path-advice {
  background: linear-gradient(135deg, #eff6ff 0%, #dbeafe 100%);
  border-color: #bfdbfe;
}

.student-learning-v2-path-advice-header,
.student-learning-v2-path-reason-header {
  margin-bottom: 12px;
  font-size: 16px;
  color: #0f172a;
}

.student-learning-v2-path-advice-content,
.student-learning-v2-path-reason-content {
  font-size: 14px;
  line-height: 1.6;
  color: #475569;
  white-space: pre-wrap;
}

.student-learning-v2-path-controls {
  display: flex;
  gap: 16px;
  padding: 16px;
  background: #f8fafc;
  border-radius: 8px;
}

.student-learning-v2-path-controls label {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 14px;
  color: #475569;
  cursor: pointer;
}

.student-learning-v2-path-nodes {
  padding: 20px;
  background: #ffffff;
  border: 1px solid #e2e8f0;
  border-radius: 12px;
}

.student-learning-v2-path-nodes-header {
  margin-bottom: 16px;
  font-size: 16px;
  color: #0f172a;
}

.student-learning-v2-path-node-list {
  display: grid;
  gap: 12px;
}

.student-learning-v2-path-node-item {
  display: flex;
  gap: 16px;
  padding: 16px;
  background: #f8fafc;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  transition: all 0.2s;
}

.student-learning-v2-path-node-item:hover {
  border-color: #bfdbfe;
  box-shadow: 0 4px 8px rgba(37, 99, 235, 0.12);
}

.student-learning-v2-path-node-rank {
  flex-shrink: 0;
  width: 32px;
  height: 32px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #3b82f6 0%, #2563eb 100%);
  color: #fff;
  font-weight: 700;
  border-radius: 50%;
  font-size: 14px;
}

.student-learning-v2-path-node-content {
  flex: 1;
}

.student-learning-v2-path-node-title {
  font-size: 16px;
  font-weight: 600;
  color: #0f172a;
  margin-bottom: 8px;
}

.student-learning-v2-path-node-meta {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 16px;
  font-size: 13px;
  color: #64748b;
  margin-bottom: 12px;
}

.student-learning-v2-path-status {
  display: inline-flex;
  align-items: center;
  min-height: 24px;
  padding: 3px 9px;
  border-radius: 999px;
  background: #eef2ff;
  color: #4338ca;
  font-size: 12px;
  font-weight: 700;
}

.student-learning-v2-path-status.is-in_progress {
  background: #e0f2fe;
  color: #0369a1;
}

.student-learning-v2-path-status.is-completed {
  background: #dcfce7;
  color: #15803d;
}

.student-learning-v2-path-status.is-skipped {
  background: #f1f5f9;
  color: #475569;
}

.student-learning-v2-path-node-time {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  margin: -4px 0 12px;
  color: #64748b;
  font-size: 12px;
}

.student-learning-v2-path-node-resources {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(230px, 1fr));
  gap: 12px;
}

.student-learning-v2-path-node-actions {
  display: flex;
  flex-wrap: wrap;
  justify-content: flex-end;
  gap: 10px;
  margin-top: 14px;
}

.student-learning-v2-path-node-actions button:disabled {
  cursor: not-allowed;
  opacity: 0.62;
}

.student-learning-v2-resource-card {
  display: grid;
  gap: 10px;
  padding: 14px;
  border: 1px solid #dbe4f0;
  border-radius: 12px;
  background: #fff;
}

.student-learning-v2-resource-card.is-previewable {
  cursor: pointer;
}

.student-learning-v2-resource-card.is-previewable:hover {
  border-color: #bfdbfe;
  box-shadow: 0 4px 8px rgba(37, 99, 235, 0.12);
}

.student-learning-v2-resource-card-top {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
}

.student-learning-v2-resource-kind,
.student-learning-v2-resource-score {
  display: inline-flex;
  align-items: center;
  min-height: 26px;
  padding: 4px 9px;
  border-radius: 999px;
  font-size: 12px;
  font-weight: 700;
}

.student-learning-v2-resource-kind {
  background: #e0f2fe;
  color: #0369a1;
}

.student-learning-v2-resource-score {
  background: #ecfdf5;
  color: #047857;
}

.student-learning-v2-resource-card h4 {
  margin: 0;
  font-size: 15px;
  line-height: 1.45;
}

.student-learning-v2-resource-reason {
  margin: 0;
  color: #64748b;
  font-size: 13px;
  line-height: 1.55;
}

.student-learning-v2-resource-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: auto;
}

.student-learning-v2-resource-actions a,
.student-learning-v2-resource-watch {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-height: 34px;
  padding: 0 12px;
  border-radius: 999px;
  font-size: 13px;
  font-weight: 700;
}

.student-learning-v2-resource-actions a {
  border: 1px solid #cbd5e1;
  color: #334155;
  background: #fff;
}

.student-learning-v2-resource-watch {
  border: none;
  color: #fff;
  background: #2563eb;
  cursor: pointer;
}

.student-learning-v2-path-empty {
  padding: 60px 20px;
  text-align: center;
  background: #f8fafc;
  border-radius: 12px;
  border: 1px dashed #cbd5e1;
}

.student-learning-v2-path-empty-icon {
  font-size: 64px;
  margin-bottom: 16px;
}

.student-learning-v2-path-empty-text {
  font-size: 16px;
  color: #64748b;
  font-weight: 500;
}

.student-learning-v2-video-modal-mask {
  position: fixed;
  inset: 0;
  z-index: 90;
  display: grid;
  place-items: center;
  padding: 24px;
  background: rgba(15, 23, 42, 0.58);
}

.student-learning-v2-video-modal {
  width: min(980px, 100%);
  border: 1px solid #dbe4f0;
  border-radius: 16px;
  background: #fff;
  box-shadow: 0 24px 70px rgba(15, 23, 42, 0.24);
  overflow: hidden;
}

.student-learning-v2-video-modal-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  padding: 14px 16px;
  border-bottom: 1px solid #e2e8f0;
}

.student-learning-v2-video-modal-head h3 {
  margin: 0;
  font-size: 17px;
  line-height: 1.45;
}

.student-learning-v2-video-modal iframe {
  display: block;
  width: 100%;
  border: 0;
  background: #020617;
}

.student-learning-v2-video-modal-frame {
  aspect-ratio: 16 / 9;
}

.student-learning-v2-document-frame {
  height: min(78vh, 860px);
  aspect-ratio: auto;
}

.student-learning-v2-video-player-shell {
  position: relative;
  background: #020617;
}

.student-learning-v2-video-player {
  display: block;
  width: 100%;
  aspect-ratio: 16 / 9;
  background: #020617;
}

.student-learning-v2-video-player-error {
  position: absolute;
  inset: 0;
  display: grid;
  place-items: center;
  gap: 12px;
  padding: 20px;
  color: #fff;
  text-align: center;
  background: rgba(2, 6, 23, 0.78);
}

.student-learning-v2-video-player-error p {
  margin: 0;
  line-height: 1.6;
}

.student-learning-v2-video-player-error a {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-height: 34px;
  padding: 0 12px;
  border-radius: 999px;
  background: #2563eb;
  color: #fff;
  font-size: 13px;
  font-weight: 700;
}

.student-learning-v2-preview-fallback {
  display: grid;
  place-items: center;
  gap: 12px;
  min-height: 240px;
  padding: 24px;
  background: #020617;
  color: #fff;
  text-align: center;
}

.student-learning-v2-preview-fallback a {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-height: 34px;
  padding: 0 12px;
  border-radius: 999px;
  background: #2563eb;
  color: #fff;
  font-size: 13px;
  font-weight: 700;
}

@media (max-width: 640px) {
  .student-learning-v2-path-header {
    flex-direction: column;
  }

  .student-learning-v2-path-controls {
    flex-direction: column;
    gap: 12px;
  }

  .student-learning-v2-path-node-item {
    flex-direction: column;
  }
}
</style>
