<template>
  <div class="student-learning-v2-path-panel">
    <div class="student-learning-v2-path-header">
      <div>
        <h2>🎯 个性化学习路径</h2>
        <p class="muted">综合学生画像、学习进度、测验与作业证据，推荐后续学习顺序和配套资源</p>
      </div>
      <div class="student-learning-v2-path-header-actions">
        <button class="ghost-btn" type="button" :disabled="loading" @click="handleRegenerate">
          {{ loading ? "生成中..." : "重新规划" }}
        </button>
      </div>
    </div>

    <section class="student-learning-v2-path-course-context">
      <div>
        <span>课程范围</span>
        <strong>{{ currentCourseName || "当前课程" }}</strong>
        <p>路径依据当前课程的整体学习情况生成，资源推荐来自该课程知识点绑定的 B站、YouTube、CSDN 与教师资源。</p>
      </div>
      <label class="student-learning-v2-path-course-select">
        <span>切换课程</span>
        <select v-model="currentCourseId" :disabled="coursesLoading || !studentCourses.length" @change="handleCourseChange">
          <option v-if="!studentCourses.length" value="">暂无可学习课程</option>
          <option v-for="course in studentCourses" :key="course.course_id" :value="course.course_id">
            {{ course.course_name || course.course_id }}
          </option>
        </select>
      </label>
      <em v-if="coursesLoading">正在读取课程...</em>
      <em v-else-if="coursesError" class="error-state">{{ coursesError }}</em>
    </section>

    <div v-if="loading" class="state-card">正在生成个性化学习路径...</div>
    <div v-else-if="error" class="state-card error-state">{{ error }}</div>

    <template v-else-if="pathData">
      <section class="student-learning-v2-path-manual-goal">
        <div>
          <strong>按目标规划</strong>
          <p>输入本阶段想完成的学习目标，系统会生成一个新的路径版本。</p>
        </div>
        <form class="student-learning-v2-path-manual-form" @submit.prevent="handleManualGoalGenerate">
          <input
            v-model.trim="manualGoal"
            type="text"
            maxlength="80"
            placeholder="例如：两周内补齐 Kafka 和 Flink 基础"
            :disabled="loading"
          />
          <button class="student-learning-v2-resource-watch" type="submit" :disabled="loading || !manualGoal">
            生成目标路径
          </button>
        </form>
      </section>

      <div v-if="pathRefreshNotice" class="student-learning-v2-path-refresh" :class="{ warning: pathRefreshNoticeType === 'warning' }">
        {{ pathRefreshNotice }}
      </div>

      <div class="student-learning-v2-path-meta">
        <div>
          <span>路径版本</span>
          <strong>v{{ pathData.version_no ?? 1 }}</strong>
        </div>
        <div>
          <span>版本状态</span>
          <strong>{{ lifecycleStatusLabel(pathData.lifecycle_status) }}</strong>
        </div>
        <div>
          <span>生成来源</span>
          <strong>{{ triggerLabel(pathData.trigger_type) }}</strong>
        </div>
        <div>
          <span>诊断依据</span>
          <strong>{{ basisEvidenceLabel }}</strong>
        </div>
        <div>
          <span>课程</span>
          <strong>{{ pathData.course_id || "默认课程" }}</strong>
        </div>
        <div>
          <span>生成时间</span>
          <strong>{{ formatPathTime(pathData.generated_at) || "待记录" }}</strong>
        </div>
        <div v-if="pathData.basis_report_id">
          <span>依据报告</span>
          <strong>{{ pathData.basis_report_id }}</strong>
        </div>
      </div>

      <div v-if="pathVersions.length > 1" class="student-learning-v2-path-versions">
        <div class="student-learning-v2-path-versions-head">
          <strong>路径版本记录</strong>
          <button
            v-if="isViewingHistoricalVersion"
            class="ghost-btn small"
            type="button"
            @click="showCurrentPathVersion"
          >
            返回当前版本
          </button>
        </div>
        <div class="student-learning-v2-path-version-list">
          <button
            v-for="version in pathVersions"
            :key="versionKey(version)"
            type="button"
            class="student-learning-v2-path-version"
            :class="{ active: versionKey(version) === selectedVersionKey }"
            @click="selectPathVersion(version)"
          >
            <strong>v{{ version.version_no ?? 1 }}</strong>
            <span>{{ lifecycleStatusLabel(version.lifecycle_status) }} · {{ triggerLabel(version.trigger_type) }}</span>
            <em>{{ formatPathTime(version.generated_at || version.updated_at) || "时间待记录" }}</em>
          </button>
        </div>
      </div>

      <div v-if="pathData.trigger_reason || pathData.basis?.formal_node_rule" class="student-learning-v2-path-basis">
        <strong>生成依据</strong>
        <p v-if="pathData.trigger_reason">{{ pathData.trigger_reason }}</p>
        <p v-if="pathData.basis?.formal_node_rule">{{ pathData.basis.formal_node_rule }}</p>
      </div>

      <div v-if="insufficientNodes.length" class="student-learning-v2-path-evidence">
        <strong>依据不足，先补证据</strong>
        <p>这些知识点暂不进入正式补学路径，请先完成测验、作业或学习记录。</p>
        <div v-for="node in insufficientNodes" :key="node.node_id" class="student-learning-v2-path-evidence-row">
          <span>{{ node.node_id }}</span>
          <em>{{ insufficientNodeText(node) }}</em>
        </div>
      </div>
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
          <strong>推荐学习路径（{{ sortedNodes.length }} 个知识点）</strong>
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
                <span v-if="node.source">来源 {{ nodeSourceLabel(node.source) }}</span>
                <span v-if="node.evidence_level">证据 {{ evidenceLevelLabel(node.evidence_level) }}</span>
                <span class="student-learning-v2-path-status" :class="`is-${pathNodeStatus(node.node_id).status}`">
                  {{ pathStatusLabel(pathNodeStatus(node.node_id).status) }}
                </span>
              </div>
              <div v-if="node.reason || node.suggested_actions?.length" class="student-learning-v2-path-node-basis">
                <span v-if="node.reason">{{ node.reason }}</span>
                <span v-if="node.suggested_actions?.length">{{ node.suggested_actions.join("、") }}</span>
              </div>
              <div v-if="pathNodeStatus(node.node_id).started_at || pathNodeStatus(node.node_id).completed_at" class="student-learning-v2-path-node-time">
                <span v-if="pathNodeStatus(node.node_id).started_at">开始：{{ formatPathTime(pathNodeStatus(node.node_id).started_at) }}</span>
                <span v-if="pathNodeStatus(node.node_id).completed_at">完成：{{ formatPathTime(pathNodeStatus(node.node_id).completed_at) }}</span>
              </div>

              <div v-if="node.resources?.length" class="student-learning-v2-path-node-resources">
                <article
                  v-for="(resource, resourceIndex) in node.resources"
                  :key="resource.url"
                  class="student-learning-v2-resource-card"
                  :class="{ 'is-previewable': canPreview(resource) }"
                  :role="canPreview(resource) ? 'button' : undefined"
                  :tabindex="canPreview(resource) ? 0 : undefined"
                  @click="canPreview(resource) && openResource(resource, node, resourceIndex)"
                  @keydown.enter.prevent="canPreview(resource) && openResource(resource, node, resourceIndex)"
                  @keydown.space.prevent="canPreview(resource) && openResource(resource, node, resourceIndex)"
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
                      @click.stop="openResource(resource, node, resourceIndex)"
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
                  :disabled="isViewingHistoricalVersion || isPathStatusBusy(node.node_id) || pathNodeStatus(node.node_id).status === 'completed'"
                  @click="handlePathStatusUpdate(node.node_id, 'in_progress')"
                >
                  {{ pathNodeStatus(node.node_id).status === 'in_progress' ? '学习中' : '开始学习' }}
                </button>
                <button
                  type="button"
                  class="student-learning-v2-resource-watch"
                  :disabled="isViewingHistoricalVersion || isPathStatusBusy(node.node_id) || pathNodeStatus(node.node_id).status === 'completed'"
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

      <div v-if="supplementalItems.length" class="student-learning-v2-path-supplemental">
        <div class="student-learning-v2-path-nodes-header">
          <strong>补充学习项（{{ supplementalItems.length }} 个）</strong>
        </div>
        <div class="student-learning-v2-supplemental-list">
          <article
            v-for="item in supplementalItems"
            :key="item.item_id || `${item.node_id}-${item.source}-${item.title}`"
            class="student-learning-v2-supplemental-item"
          >
            <div class="student-learning-v2-supplemental-main">
              <span class="student-learning-v2-resource-kind">{{ supplementalSourceLabel(item.source) }}</span>
              <h4>{{ item.title || item.node_id }}</h4>
              <p v-if="item.reason">{{ item.reason }}</p>
            </div>
            <div v-if="item.resources?.length" class="student-learning-v2-path-node-resources">
              <article
                v-for="(resource, resourceIndex) in item.resources"
                :key="resource.url"
                class="student-learning-v2-resource-card"
                :class="{ 'is-previewable': canPreview(resource) }"
                :role="canPreview(resource) ? 'button' : undefined"
                :tabindex="canPreview(resource) ? 0 : undefined"
                @click="canPreview(resource) && openResource(resource, item, resourceIndex)"
                @keydown.enter.prevent="canPreview(resource) && openResource(resource, item, resourceIndex)"
                @keydown.space.prevent="canPreview(resource) && openResource(resource, item, resourceIndex)"
              >
                <div class="student-learning-v2-resource-card-top">
                  <span class="student-learning-v2-resource-kind">{{ resourceTypeLabel(resource) }}</span>
                  <span v-if="resource.score != null" class="student-learning-v2-resource-score">
                    {{ Math.round(resource.score * 100) }}%
                  </span>
                </div>
                <h4>{{ resource.title || resource.url }}</h4>
                <div class="student-learning-v2-resource-actions">
                  <button
                    v-if="canPreview(resource)"
                    type="button"
                    class="student-learning-v2-resource-watch"
                    @click.stop="openResource(resource, item, resourceIndex)"
                  >
                    {{ previewButtonLabel(resource) }}
                  </button>
                  <a v-else :href="resource.url" target="_blank" rel="noopener noreferrer" @click.stop>
                    打开资源
                  </a>
                </div>
              </article>
            </div>
          </article>
        </div>
      </div>
    </template>

    <div v-if="activeResource" class="student-learning-v2-video-modal-mask" @click.self="closeResource">
      <section class="student-learning-v2-video-modal">
        <div class="student-learning-v2-video-modal-head">
          <h3>{{ activeResource.title || "推荐资源" }}</h3>
          <button type="button" class="ghost-btn" @click="closeResource">关闭</button>
        </div>

        <TrackedResourceFrame
          v-if="activeResourcePreview.mode === 'video-embed'"
          :course-id="currentCourseId || pathData?.course_id || 'course_big_data'"
          :node-id="activeResourceContext.nodeId"
          :node-name="activeResourceContext.nodeName"
          :resource-url="activeResource.url"
          :resource-index="activeResourceContext.resourceIndex"
          :provider="activeResourceProvider"
          :embed-url="activeResourcePreview.url"
          :title="activeResource.title || activeResource.url"
          source="student_learning_path"
          frame-class="student-learning-v2-video-modal-frame"
        />

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
import { fetchCurrentLearningPath, fetchLearningPathVersions, fetchStudentCourses, generateLearningPath, updateLearningPathNodeStatus } from "../../../api/student";
import TrackedResourceFrame from "./TrackedResourceFrame.vue";
import type {
  LearningPathNodeStatus,
  LearningPathNodeStatusValue,
  LearningPathResponse,
  LearningPathResource,
  StudentCourseSummary,
} from "../../../types/student";

const loading = ref(false);
const error = ref("");
const studentCourses = ref<StudentCourseSummary[]>([]);
const coursesLoading = ref(false);
const coursesError = ref("");
const currentCourseId = ref("");
const pathData = ref<LearningPathResponse | null>(null);
const currentPathData = ref<LearningPathResponse | null>(null);
const pathVersions = ref<LearningPathResponse[]>([]);
const sortMode = ref<"priority" | "mastery">("priority");
const activeResource = ref<LearningPathResource | null>(null);
const activeResourceContext = ref({
  nodeId: "",
  nodeName: "",
  resourceIndex: null as number | null,
});
const videoElementRef = ref<HTMLVideoElement | null>(null);
const playerError = ref("");
const currentUsername = ref("");
const pathStatusUpdating = ref<Record<string, boolean>>({});
const pathRefreshNotice = ref("");
const pathRefreshNoticeType = ref<"success" | "warning">("success");
const selectedVersionKey = ref("");
const manualGoal = ref("");
let hlsInstance: Hls | null = null;

const selectedCourse = computed(() =>
  studentCourses.value.find((course) => course.course_id === currentCourseId.value) ?? null,
);
const currentCourseName = computed(() =>
  selectedCourse.value?.course_name || pathData.value?.course_id || currentCourseId.value || "默认课程",
);

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
const activeResourceProvider = computed(() => {
  const resource = activeResource.value;
  return resource ? (resource.provider || resource.source || inferResourceProvider(resource.url)) : "";
});

const supplementalItems = computed(() => pathData.value?.supplemental_items ?? []);
const insufficientNodes = computed(() => pathData.value?.basis?.insufficient_nodes ?? []);
const basisEvidenceLabel = computed(() => {
  const level = pathData.value?.basis?.diagnosis_evidence_level;
  const confidence = pathData.value?.basis?.diagnosis_confidence;
  const levelText = evidenceLevelLabel(level);
  return typeof confidence === "number" ? `${levelText} · ${formatPercentValue(confidence)}` : levelText;
});
const currentVersionKey = computed(() => currentPathData.value ? versionKey(currentPathData.value) : "");
const isViewingHistoricalVersion = computed(() =>
  Boolean(selectedVersionKey.value && currentVersionKey.value && selectedVersionKey.value !== currentVersionKey.value),
);

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

function formatPercentValue(value: number) {
  const percent = value > 1 ? value : value * 100;
  return `${Number(percent.toFixed(2))}%`;
}

function triggerLabel(value?: string) {
  const mapping: Record<string, string> = {
    diagnosis: "诊断生成",
    manual_goal: "学生目标",
    node_completed: "完成后重规划",
    new_course: "新课初始化",
    intervention_completed: "干预完成后调整",
  };
  return mapping[String(value || "diagnosis")] || "学习数据生成";
}

function lifecycleStatusLabel(value?: string | null) {
  const mapping: Record<string, string> = {
    active: "当前生效",
    archived: "历史版本",
    superseded: "已被新版本替代",
    draft: "草稿",
  };
  return mapping[String(value || "active").toLowerCase()] || String(value || "当前生效");
}

function evidenceLevelLabel(value?: string | null) {
  const mapping: Record<string, string> = {
    sufficient: "证据充分",
    partial: "部分证据",
    insufficient: "依据不足",
  };
  return mapping[String(value || "").toLowerCase()] || "证据待确认";
}

function nodeSourceLabel(value?: string | null) {
  const mapping: Record<string, string> = {
    published_course_graph: "已发布课程图谱",
    diagnosis_weak_node: "诊断薄弱点",
    path_planner: "路径规划",
  };
  return mapping[String(value || "").toLowerCase()] || String(value || "学习数据");
}

function insufficientNodeText(node: { reason?: string; suggested_actions?: string[] }) {
  if (node.reason) return node.reason;
  if (node.suggested_actions?.length) return node.suggested_actions.join("、");
  return "建议先补测验、补作业或补学习记录";
}

function supplementalSourceLabel(value?: string) {
  const mapping: Record<string, string> = {
    resource_recommendation: "推荐资源",
    diagnosis_weak_node_outside_published_graph: "补充学习",
  };
  return mapping[String(value || "")] || "补充项";
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

function versionKey(version: LearningPathResponse) {
  return String(version.plan_id ?? version.filename ?? `${version.version_no ?? 1}-${version.generated_at ?? ""}`);
}

function setCurrentPath(path: LearningPathResponse) {
  currentPathData.value = path;
  pathData.value = path;
  selectedVersionKey.value = versionKey(path);
}

async function refreshPathVersions(username = currentUsername.value) {
  if (!username) return;
  const data = await fetchLearningPathVersions(username, 8, currentCourseId.value || null);
  pathVersions.value = data.versions || [];
  if (currentPathData.value) {
    const currentKey = versionKey(currentPathData.value);
    const latestCurrent = pathVersions.value.find((item) => versionKey(item) === currentKey);
    if (latestCurrent) {
      currentPathData.value = latestCurrent;
      if (!isViewingHistoricalVersion.value) {
        pathData.value = latestCurrent;
        selectedVersionKey.value = versionKey(latestCurrent);
      }
    }
  }
}

function selectPathVersion(version: LearningPathResponse) {
  pathData.value = version;
  selectedVersionKey.value = versionKey(version);
  pathRefreshNotice.value = versionKey(version) === currentVersionKey.value
    ? ""
    : `正在查看历史路径版本 v${version.version_no ?? 1}，历史版本仅用于追溯。`;
  pathRefreshNoticeType.value = versionKey(version) === currentVersionKey.value ? "success" : "warning";
}

function showCurrentPathVersion() {
  if (!currentPathData.value) return;
  pathData.value = currentPathData.value;
  selectedVersionKey.value = versionKey(currentPathData.value);
  pathRefreshNotice.value = "";
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

function inferResourceProvider(url: string) {
  const value = url.toLowerCase();
  if (value.includes("youtube.com") || value.includes("youtu.be")) return "youtube";
  if (value.includes("bilibili.com")) return "bilibili";
  if (value.includes("csdn.net")) return "csdn";
  return "other";
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

function openResource(resource: LearningPathResource, context?: { node_id?: string; title?: string }, resourceIndex: number | null = null) {
  activeResource.value = resource;
  activeResourceContext.value = {
    nodeId: context?.node_id || resource.title || resource.url,
    nodeName: context?.title || context?.node_id || resource.title || "",
    resourceIndex,
  };
}

function closeResource() {
  activeResource.value = null;
  activeResourceContext.value = {
    nodeId: "",
    nodeName: "",
    resourceIndex: null,
  };
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

async function loadStudentCourseOptions() {
  coursesLoading.value = true;
  coursesError.value = "";
  try {
    const data = await fetchStudentCourses();
    studentCourses.value = data.courses || [];
    const storedCourseId = localStorage.getItem("ai-education:selected-course-id") || "";
    const preferred = storedCourseId || data.default_course_id || studentCourses.value[0]?.course_id || "course_big_data";
    const available = studentCourses.value.find((course) => course.course_id === preferred);
    currentCourseId.value = available?.course_id || studentCourses.value[0]?.course_id || preferred;
    localStorage.setItem("ai-education:selected-course-id", currentCourseId.value);
  } catch (err) {
    coursesError.value = err instanceof Error ? err.message : "课程列表加载失败";
    if (!currentCourseId.value) {
      currentCourseId.value = "course_big_data";
    }
  } finally {
    coursesLoading.value = false;
  }
}

async function handleCourseChange() {
  if (!currentCourseId.value) return;
  localStorage.setItem("ai-education:selected-course-id", currentCourseId.value);
  pathData.value = null;
  currentPathData.value = null;
  pathVersions.value = [];
  selectedVersionKey.value = "";
  activeResource.value = null;
  manualGoal.value = "";
  await loadPath(false);
}

async function loadPath(
  forceGenerate = false,
  options: { triggerType?: string; manualGoal?: string | null; notice?: string } = {},
) {
  loading.value = true;
  error.value = "";
  pathRefreshNotice.value = "";
  try {
    const user = await fetchCurrentUser();
    currentUsername.value = user.username;
    if (forceGenerate) {
      setCurrentPath(await generateLearningPath(user.username, {
        course_id: currentCourseId.value || null,
        trigger_type: options.triggerType || "diagnosis",
        manual_goal: options.manualGoal || null,
      }));
    } else {
      try {
        setCurrentPath(await fetchCurrentLearningPath(user.username, currentCourseId.value || null));
      } catch (err: any) {
        if (err.response?.status === 404 || String(err?.message || "").includes("No learning path found")) {
          setCurrentPath(await generateLearningPath(user.username, {
            course_id: currentCourseId.value || null,
            trigger_type: "new_course",
            manual_goal: null,
          }));
        } else {
          throw err;
        }
      }
    }
    try {
      await refreshPathVersions(user.username);
    } catch (versionErr) {
      pathRefreshNoticeType.value = "warning";
        pathRefreshNotice.value = versionErr instanceof Error ? versionErr.message : "学习路径版本记录加载失败";
    }
    if (options.notice) {
      pathRefreshNoticeType.value = "success";
      pathRefreshNotice.value = options.notice;
    }
  } catch (err) {
    error.value = err instanceof Error ? err.message : "加载学习路径失败";
  } finally {
    loading.value = false;
  }
}

function handleRegenerate() {
  pathRefreshNotice.value = "";
  loadPath(true, { triggerType: "diagnosis" });
}

function handleManualGoalGenerate() {
  const goal = manualGoal.value.trim();
  if (!goal) return;
  loadPath(true, {
    triggerType: "manual_goal",
    manualGoal: goal,
    notice: `已根据目标“${goal}”生成新的学习路径版本。`,
  });
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
    const response = await updateLearningPathNodeStatus(currentUsername.value, nodeId, {
      status,
      plan_id: current.plan_id || null,
      mastery_after: status === "completed" ? Math.max(Number(masteryScore ?? current.mastery_before ?? 0), 60) : null,
      refresh_path: status === "completed",
      payload: {
        source: "student_course_content_path_panel",
        completed_node_id: status === "completed" ? nodeId : undefined,
      },
    });
    mergePathNodeStatus(response.node_status);
    if (status === "completed") {
      if (response.path_refresh?.path) {
        setCurrentPath(response.path_refresh.path);
        try {
          await refreshPathVersions(currentUsername.value);
        } catch {
          // Keep the refreshed path visible even if version history cannot be loaded.
        }
        pathRefreshNoticeType.value = "success";
        pathRefreshNotice.value = `已根据本次完成记录重新规划路径，当前版本 v${response.path_refresh.path.version_no ?? ""}`.trim();
      } else if (response.path_refresh?.error) {
        pathRefreshNoticeType.value = "warning";
        pathRefreshNotice.value = `节点已标记完成，但路径刷新失败：${response.path_refresh.error}`;
      } else if (response.path_refresh && response.path_refresh.triggered === false) {
        pathRefreshNoticeType.value = "warning";
        pathRefreshNotice.value = "节点已标记完成，本次未触发路径重规划。";
      }
    }
  } catch (err) {
    error.value = err instanceof Error ? err.message : "学习路径状态更新失败";
  } finally {
    const next = { ...pathStatusUpdating.value };
    delete next[nodeId];
    pathStatusUpdating.value = next;
  }
}

onMounted(async () => {
  await loadStudentCourseOptions();
  await loadPath();
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

.student-learning-v2-path-header-actions {
  display: flex;
  flex-wrap: wrap;
  justify-content: flex-end;
  gap: 10px;
}

.student-learning-v2-path-course-context {
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(220px, 320px) auto;
  gap: 16px;
  align-items: center;
  padding: 18px 20px;
  border: 1px solid #d7e2f0;
  border-radius: 10px;
  background: #ffffff;
}

.student-learning-v2-path-course-context span {
  display: block;
  color: #64748b;
  font-size: 12px;
  font-weight: 700;
}

.student-learning-v2-path-course-context strong {
  display: block;
  margin-top: 4px;
  color: #0f172a;
  font-size: 20px;
  line-height: 1.35;
}

.student-learning-v2-path-course-context p {
  margin: 6px 0 0;
  color: #64748b;
  font-size: 13px;
  line-height: 1.6;
}

.student-learning-v2-path-course-context em {
  color: #64748b;
  font-size: 13px;
  font-style: normal;
}

.student-learning-v2-path-course-context em.error-state {
  color: #dc2626;
}

.student-learning-v2-path-course-select {
  display: grid;
  gap: 6px;
}

.student-learning-v2-path-course-select select {
  min-height: 40px;
  width: 100%;
  border: 1px solid #cbd5e1;
  border-radius: 8px;
  background: #fff;
  color: #0f172a;
  font-size: 14px;
  padding: 0 12px;
}

.student-learning-v2-path-manual-goal {
  display: grid;
  grid-template-columns: minmax(220px, 0.85fr) minmax(0, 1.15fr);
  gap: 16px;
  align-items: center;
  padding: 16px;
  border: 1px solid #dbeafe;
  border-radius: 12px;
  background: #f8fbff;
}

.student-learning-v2-path-manual-goal strong {
  color: #0f172a;
  font-size: 15px;
}

.student-learning-v2-path-manual-goal p {
  margin: 6px 0 0;
  color: #64748b;
  font-size: 13px;
  line-height: 1.6;
}

.student-learning-v2-path-manual-form {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  gap: 10px;
}

.student-learning-v2-path-manual-form input {
  min-width: 0;
  min-height: 38px;
  border: 1px solid #cbd5e1;
  border-radius: 8px;
  padding: 0 12px;
  background: #fff;
  color: #0f172a;
  font-size: 14px;
}

.student-learning-v2-path-manual-form input:focus {
  border-color: #2563eb;
  box-shadow: 0 0 0 3px rgba(37, 99, 235, 0.12);
  outline: none;
}

.student-learning-v2-path-meta {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 12px;
}

.student-learning-v2-path-refresh {
  border: 1px solid #bbf7d0;
  border-radius: 8px;
  padding: 10px 12px;
  background: #f0fdf4;
  color: #166534;
  font-size: 13px;
  font-weight: 600;
  line-height: 1.55;
}

.student-learning-v2-path-refresh.warning {
  border-color: #fde68a;
  background: #fffbeb;
  color: #92400e;
}

.student-learning-v2-path-meta div,
.student-learning-v2-path-basis,
.student-learning-v2-path-evidence,
.student-learning-v2-path-supplemental {
  padding: 16px;
  border: 1px solid #e2e8f0;
  border-radius: 12px;
  background: #fff;
}

.student-learning-v2-path-meta span {
  display: block;
  margin-bottom: 6px;
  color: #64748b;
  font-size: 12px;
}

.student-learning-v2-path-meta strong {
  color: #0f172a;
  font-size: 15px;
}

.student-learning-v2-path-versions {
  display: grid;
  gap: 12px;
  padding: 16px;
  border: 1px solid #dbe4f0;
  border-radius: 8px;
  background: #fff;
}

.student-learning-v2-path-versions-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.student-learning-v2-path-version-list {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
  gap: 10px;
}

.student-learning-v2-path-version {
  display: grid;
  gap: 4px;
  min-height: 86px;
  padding: 12px;
  border: 1px solid #dbe4f0;
  border-radius: 8px;
  background: #f8fafc;
  color: #475569;
  text-align: left;
  cursor: pointer;
}

.student-learning-v2-path-version.active {
  border-color: #2563eb;
  background: #eff6ff;
}

.student-learning-v2-path-version strong {
  color: #0f172a;
}

.student-learning-v2-path-version span,
.student-learning-v2-path-version em {
  font-size: 12px;
  font-style: normal;
  line-height: 1.35;
}

.student-learning-v2-path-basis p {
  margin: 8px 0 0;
  color: #475569;
  font-size: 13px;
  line-height: 1.6;
}

.student-learning-v2-path-evidence {
  border-color: #fed7aa;
  background: #fff7ed;
}

.student-learning-v2-path-evidence p {
  margin: 8px 0 0;
  color: #9a3412;
  font-size: 13px;
  line-height: 1.6;
}

.student-learning-v2-path-evidence-row {
  display: grid;
  grid-template-columns: minmax(0, 180px) minmax(0, 1fr);
  gap: 10px;
  margin-top: 10px;
  color: #9a3412;
  font-size: 13px;
}

.student-learning-v2-path-evidence-row em {
  color: #7c2d12;
  font-style: normal;
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

.student-learning-v2-path-node-basis {
  display: grid;
  gap: 4px;
  margin: -4px 0 12px;
  color: #475569;
  font-size: 13px;
  line-height: 1.55;
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

.student-learning-v2-supplemental-list {
  display: grid;
  gap: 12px;
}

.student-learning-v2-supplemental-item {
  display: grid;
  gap: 12px;
  padding: 14px;
  border: 1px solid #dbe4f0;
  border-radius: 12px;
  background: #f8fafc;
}

.student-learning-v2-supplemental-main h4 {
  margin: 10px 0 6px;
  color: #0f172a;
  font-size: 15px;
}

.student-learning-v2-supplemental-main p {
  margin: 0;
  color: #64748b;
  font-size: 13px;
  line-height: 1.55;
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

  .student-learning-v2-path-header-actions {
    justify-content: flex-start;
  }

  .student-learning-v2-path-course-context {
    grid-template-columns: 1fr;
  }

  .student-learning-v2-path-manual-goal,
  .student-learning-v2-path-manual-form {
    grid-template-columns: 1fr;
  }

  .student-learning-v2-path-meta,
  .student-learning-v2-path-evidence-row {
    grid-template-columns: 1fr;
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
