<template>
  <div class="tracked-resource-frame" :class="{ 'tracked-resource-frame--modal': isModalFrame }">
    <div class="tracked-resource-frame__stage" :class="frameClass">
      <iframe
        ref="iframeRef"
        class="tracked-resource-frame__iframe"
        :src="trackedEmbedUrl"
        :title="title"
        allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share"
        allowfullscreen
        scrolling="no"
        referrerpolicy="no-referrer-when-downgrade"
        @load="handleFrameLoad"
      ></iframe>
    </div>
    <div class="tracked-resource-frame__evidence">
      <span>{{ evidenceLabel }}</span>
      <button
        v-if="isBilibili"
        type="button"
        class="tracked-resource-frame__complete"
        :disabled="manualCompleted"
        @click="markBilibiliComplete"
      >
        {{ manualCompleted ? "已标记学完" : "标记已学完" }}
      </button>
    </div>
  </div>
</template>

<script lang="ts">
type YouTubePlayerState = {
  PLAYING: number;
  PAUSED: number;
  ENDED: number;
  BUFFERING: number;
};

type YouTubePlayer = {
  getCurrentTime: () => number;
  getDuration: () => number;
  destroy: () => void;
};

type YouTubePlayerCtor = new (
  element: HTMLIFrameElement,
  options: {
    events?: {
      onReady?: () => void;
      onStateChange?: (event: { data: number }) => void;
    };
  },
) => YouTubePlayer;

declare global {
  interface Window {
    YT?: {
      Player: YouTubePlayerCtor;
      PlayerState: YouTubePlayerState;
    };
    onYouTubeIframeAPIReady?: () => void;
  }
}

let sharedYouTubeApiPromise: Promise<void> | null = null;

function loadSharedYouTubeIframeApi() {
  if (window.YT?.Player) return Promise.resolve();
  if (sharedYouTubeApiPromise) return sharedYouTubeApiPromise;

  sharedYouTubeApiPromise = new Promise<void>((resolve, reject) => {
    const previousReady = window.onYouTubeIframeAPIReady;
    window.onYouTubeIframeAPIReady = () => {
      previousReady?.();
      resolve();
    };

    const existing = document.querySelector<HTMLScriptElement>('script[src="https://www.youtube.com/iframe_api"]');
    if (!existing) {
      const script = document.createElement("script");
      script.src = "https://www.youtube.com/iframe_api";
      script.async = true;
      script.onerror = () => reject(new Error("YouTube IFrame API failed to load"));
      document.head.appendChild(script);
    }
  });

  return sharedYouTubeApiPromise;
}
</script>

<script setup lang="ts">
import { computed, onBeforeUnmount, ref, shallowRef } from "vue";
import { recordResourceLearningEvent } from "../../../api/student";

const props = withDefaults(defineProps<{
  courseId: string;
  nodeId: string;
  nodeName?: string;
  resourceUrl: string;
  embedUrl: string;
  title: string;
  provider?: string | null;
  source?: string;
  resourceIndex?: number | null;
  frameClass?: string;
}>(), {
  nodeName: "",
  provider: "",
  source: "student_resource_viewer",
  resourceIndex: null,
  frameClass: "",
});

const iframeRef = ref<HTMLIFrameElement | null>(null);
const youtubePlayer = shallowRef<YouTubePlayer | null>(null);
const manualCompleted = ref(false);
const frameLoaded = ref(false);

let youtubeHeartbeatTimer: number | null = null;
let bilibiliHeartbeatTimer: number | null = null;
let openedAt = 0;
let playingSince: number | null = null;
let watchedSeconds = 0;
let lastYoutubeProgressReportAt = 0;
let youtubeCompleted = false;
let viewRecorded = false;

const normalizedProvider = computed(() => String(props.provider || inferProvider(props.resourceUrl)).toLowerCase());
const isYoutube = computed(() => normalizedProvider.value === "youtube");
const isBilibili = computed(() => normalizedProvider.value === "bilibili");
const measurementMode = computed(() => isYoutube.value ? "youtube_iframe_api" : "iframe_visible_time");
const isModalFrame = computed(() => props.frameClass.includes("modal"));

const trackedEmbedUrl = computed(() => {
  if (!isYoutube.value || !props.embedUrl) return props.embedUrl;
  try {
    const parsed = new URL(props.embedUrl, window.location.origin);
    parsed.searchParams.set("enablejsapi", "1");
    parsed.searchParams.set("origin", window.location.origin);
    return parsed.toString();
  } catch {
    return props.embedUrl;
  }
});

const evidenceLabel = computed(() => {
  if (isYoutube.value) return "YouTube：记录真实播放进度，播放到 90% 计为完成";
  if (isBilibili.value) return "B站：记录打开、停留和手动完成，不作为真实观看时长";
  return "资源学习行为会记录到学生画像";
});

function inferProvider(url: string) {
  const value = url.toLowerCase();
  if (value.includes("youtube.com") || value.includes("youtu.be")) return "youtube";
  if (value.includes("bilibili.com")) return "bilibili";
  return "other";
}

function ensureOpenedAt() {
  if (!openedAt) openedAt = Date.now();
}

function visibleSeconds() {
  if (!openedAt) return 0;
  return Math.max(0, Math.round((Date.now() - openedAt) / 1000));
}

function currentWatchedSeconds() {
  const activeSegment = playingSince ? (Date.now() - playingSince) / 1000 : 0;
  return Math.max(0, Math.round(watchedSeconds + activeSegment));
}

function youtubeProgress() {
  const player = youtubePlayer.value;
  if (!player) return { current: 0, duration: 0, percent: null as number | null };
  const current = safeNumber(player.getCurrentTime());
  const duration = safeNumber(player.getDuration());
  const percent = duration > 0 ? Math.max(0, Math.min(100, (current / duration) * 100)) : null;
  return { current, duration, percent };
}

function safeNumber(value: unknown) {
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : 0;
}

async function reportLearningEvent(
  eventType: "view" | "progress" | "complete",
  options: {
    durationSeconds?: number;
    progressPercent?: number | null;
    isCompleted?: boolean;
    phase?: string;
    extra?: Record<string, unknown>;
  } = {},
) {
  if (!props.courseId || !props.nodeId || !props.resourceUrl) return;
  try {
    await recordResourceLearningEvent({
      course_id: props.courseId,
      node_id: props.nodeId,
      resource_path: props.resourceUrl,
      event_type: eventType,
      duration_seconds: options.durationSeconds ?? 0,
      progress_percent: options.progressPercent ?? null,
      is_completed: Boolean(options.isCompleted),
      payload: {
        source: props.source,
        node_name: props.nodeName,
        provider: normalizedProvider.value,
        measurement_mode: measurementMode.value,
        resource_index: props.resourceIndex,
        phase: options.phase || eventType,
        ...options.extra,
      },
    });
  } catch (error) {
    console.warn("Failed to record resource learning event", error);
  }
}

function recordViewOnce() {
  if (viewRecorded) return;
  viewRecorded = true;
  void reportLearningEvent("view", {
    progressPercent: isYoutube.value ? 0 : null,
    phase: "iframe_loaded",
  });
}

function handleFrameLoad() {
  frameLoaded.value = true;
  ensureOpenedAt();
  recordViewOnce();
  if (isYoutube.value) {
    void bindYouTubePlayer();
  } else if (isBilibili.value) {
    startBilibiliHeartbeat();
  }
}

async function bindYouTubePlayer() {
  const iframe = iframeRef.value;
  if (!iframe || youtubePlayer.value) return;
  try {
    await loadSharedYouTubeIframeApi();
    if (!window.YT?.Player || !iframeRef.value) return;
    youtubePlayer.value = new window.YT.Player(iframeRef.value, {
      events: {
        onReady: () => {
          recordViewOnce();
        },
        onStateChange: handleYouTubeStateChange,
      },
    });
  } catch (error) {
    console.warn("Failed to bind YouTube player", error);
  }
}

function handleYouTubeStateChange(event: { data: number }) {
  const state = window.YT?.PlayerState;
  if (!state) return;
  if (event.data === state.PLAYING) {
    startYoutubePlaying();
    return;
  }
  if (event.data === state.PAUSED || event.data === state.BUFFERING) {
    stopYoutubePlaying();
    void reportYoutubeProgress("pause");
    return;
  }
  if (event.data === state.ENDED) {
    stopYoutubePlaying();
    void reportYoutubeComplete("ended");
  }
}

function startYoutubePlaying() {
  if (!playingSince) playingSince = Date.now();
  if (youtubeHeartbeatTimer) return;
  youtubeHeartbeatTimer = window.setInterval(() => {
    void reportYoutubeProgress("heartbeat");
  }, 15000);
}

function stopYoutubePlaying() {
  if (playingSince) {
    watchedSeconds += (Date.now() - playingSince) / 1000;
    playingSince = null;
  }
  if (youtubeHeartbeatTimer) {
    window.clearInterval(youtubeHeartbeatTimer);
    youtubeHeartbeatTimer = null;
  }
}

async function reportYoutubeProgress(phase: string) {
  const progress = youtubeProgress();
  const now = Date.now();
  const percent = progress.percent;
  if (percent != null && percent >= 90 && !youtubeCompleted) {
    await reportYoutubeComplete("watched_90_percent");
    return;
  }
  if (phase === "heartbeat" && now - lastYoutubeProgressReportAt < 14000) return;
  lastYoutubeProgressReportAt = now;
  await reportLearningEvent("progress", {
    durationSeconds: currentWatchedSeconds(),
    progressPercent: percent,
    phase,
    extra: {
      player_current_seconds: Math.round(progress.current),
      player_duration_seconds: Math.round(progress.duration),
    },
  });
}

async function reportYoutubeComplete(phase: string) {
  if (youtubeCompleted) return;
  youtubeCompleted = true;
  const progress = youtubeProgress();
  await reportLearningEvent("complete", {
    durationSeconds: currentWatchedSeconds(),
    progressPercent: progress.percent ?? 100,
    isCompleted: true,
    phase,
    extra: {
      player_current_seconds: Math.round(progress.current),
      player_duration_seconds: Math.round(progress.duration),
      complete_rule: phase === "ended" ? "ended" : "progress_gte_90",
    },
  });
}

function startBilibiliHeartbeat() {
  if (bilibiliHeartbeatTimer) return;
  bilibiliHeartbeatTimer = window.setInterval(() => {
    void reportLearningEvent("progress", {
      durationSeconds: visibleSeconds(),
      progressPercent: null,
      phase: "visible_heartbeat",
    });
  }, 30000);
}

function stopBilibiliHeartbeat() {
  if (!bilibiliHeartbeatTimer) return;
  window.clearInterval(bilibiliHeartbeatTimer);
  bilibiliHeartbeatTimer = null;
}

async function markBilibiliComplete() {
  manualCompleted.value = true;
  await reportLearningEvent("complete", {
    durationSeconds: visibleSeconds(),
    progressPercent: 100,
    isCompleted: true,
    phase: "manual_complete",
  });
}

onBeforeUnmount(() => {
  stopYoutubePlaying();
  stopBilibiliHeartbeat();
  if (isYoutube.value && viewRecorded && !youtubeCompleted) {
    void reportYoutubeProgress("close");
  } else if (isBilibili.value && viewRecorded) {
    void reportLearningEvent("progress", {
      durationSeconds: visibleSeconds(),
      progressPercent: manualCompleted.value ? 100 : null,
      isCompleted: manualCompleted.value,
      phase: "close",
    });
  }
  if (youtubePlayer.value) {
    youtubePlayer.value.destroy();
    youtubePlayer.value = null;
  }
});
</script>

<style scoped>
.tracked-resource-frame {
  display: grid;
  gap: 8px;
  width: 100%;
}

.tracked-resource-frame__stage {
  position: relative;
  width: 100%;
  min-height: 360px;
  aspect-ratio: 16 / 9;
  overflow: hidden;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  background: #020617;
}

.tracked-resource-frame--modal .tracked-resource-frame__stage {
  min-height: min(62vh, 620px);
  aspect-ratio: 16 / 9;
}

.tracked-resource-frame__iframe {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  border: 0;
}

.tracked-resource-frame__evidence {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  color: #64748b;
  font-size: 12px;
  line-height: 1.5;
}

.tracked-resource-frame__complete {
  border: 1px solid #cbd5e1;
  background: #ffffff;
  color: #334155;
  border-radius: 6px;
  padding: 5px 10px;
  cursor: pointer;
  white-space: nowrap;
}

.tracked-resource-frame__complete:disabled {
  color: #64748b;
  background: #f8fafc;
  cursor: default;
}

@media (max-width: 720px) {
  .tracked-resource-frame__stage {
    min-height: 220px;
  }

  .tracked-resource-frame--modal .tracked-resource-frame__stage {
    min-height: 220px;
  }
}
</style>
