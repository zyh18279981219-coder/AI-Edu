<template>
  <div class="fivee-chat">
    <div class="fivee-chat-head">
      <div>
        <strong>{{ nodeName || courseName || "5E AI 助教" }}</strong>
        <p>{{ subtitle }}</p>
      </div>
    </div>

    <section v-if="studentFeedback" class="fivee-feedback" aria-label="5E 引导反馈">
      <div class="fivee-feedback-top">
        <div>
          <span class="fivee-feedback-label">本轮引导反馈</span>
          <strong>{{ studentFeedback.effectiveness_level || evidenceStatusLabel(studentFeedback.evidence_status) }}</strong>
        </div>
        <span class="fivee-status-pill">{{ evidenceStatusLabel(studentFeedback.evidence_status) }}</span>
      </div>

      <p>{{ studentFeedback.summary }}</p>
      <p class="fivee-policy">{{ effectivenessPolicyText }}</p>

      <div v-if="recentStudentEvidence.length" class="fivee-evidence-list">
        <article v-for="item in recentStudentEvidence" :key="evidenceKey(item)" class="fivee-evidence-item">
          <div>
            <strong>{{ stageLabel(item.stage) }}</strong>
            <span>{{ evidenceStatusLabel(item.evidence_status) }}</span>
          </div>
          <p>{{ item.student_feedback || item.summary || "已记录一次 5E 学习互动。" }}</p>
        </article>
      </div>

      <ul v-if="studentFeedback.next_steps?.length">
        <li v-for="step in studentFeedback.next_steps.slice(0, 3)" :key="step">{{ step }}</li>
      </ul>
    </section>

    <div ref="scrollRef" class="fivee-chat-scroll">
      <article
        v-for="(msg, index) in messages"
        :key="`${msg.role}-${msg.timestamp}-${index}`"
        class="fivee-chat-bubble"
        :class="messageClass(msg.role)"
      >
        <div class="fivee-chat-role">{{ msg.role === "user" ? "我" : "5E 助教" }}</div>
        <div v-if="msg.role === 'user'" class="fivee-chat-text">{{ msg.content }}</div>
        <Markdown v-else class="fivee-chat-text" :content="msg.content || '正在思考中...'" />

        <div v-if="msg.role !== 'user' && hasActions(msg)" class="fivee-chat-actions">
          <button
            v-for="(btn, bIdx) in msg.buttons"
            :key="`btn-${bIdx}`"
            type="button"
            class="fivee-action-btn"
            @click="handleNormalButton(btn)"
          >
            {{ btn.show_text }}
          </button>
          <button
            v-for="(res, rIdx) in msg.resources"
            :key="`res-${rIdx}`"
            type="button"
            class="fivee-action-btn success"
            @click="$emit('open-resource', res.id)"
          >
            资源 {{ res.show_text }}
          </button>
          <button
            v-for="(test, tIdx) in msg.tests"
            :key="`test-${tIdx}`"
            type="button"
            class="fivee-action-btn warning"
            @click="$emit('open-test', test.id)"
          >
            测验 {{ test.show_text }}
          </button>
        </div>
      </article>
    </div>

    <footer class="fivee-chat-footer">
      <textarea
        v-model.trim="input"
        rows="3"
        placeholder="输入你的问题..."
        :disabled="loading || !canChat"
        @keydown.enter.exact.prevent="sendMessage"
      />
      <button
        type="button"
        class="fivee-send-btn"
        :disabled="loading || !input.trim() || !canChat"
        @click="sendMessage"
      >
        {{ loading ? "发送中..." : "发送" }}
      </button>
    </footer>
  </div>
</template>

<script setup lang="ts">
import { computed, nextTick, onMounted, ref, watch } from "vue";
import Markdown from "../../../components/ui/markdown.vue";
import { fetchChatHistory, fetchFiveEEffectivenessSummary, sendFiveEChatMessage } from "../../../api/5E";
import type {
  Button,
  ChatResponse,
  FiveEEffectivenessEvidence,
  FiveEEffectivenessSummary,
} from "../../../types/5E";

const props = defineProps<{
  courseId?: string;
  studentId?: string;
  courseName?: string;
  nodeName?: string;
  resourceLabel?: string;
}>();

defineEmits<{
  (event: "open-resource", id: string): void;
  (event: "open-test", id: string): void;
}>();

const input = ref("");
const loading = ref(false);
const scrollRef = ref<HTMLDivElement | null>(null);
const messages = ref<ChatResponse[]>([]);
const effectivenessSummary = ref<FiveEEffectivenessSummary | null>(null);

const canChat = computed(() => Boolean(props.studentId && props.courseId));
const subtitle = computed(() => {
  if (!canChat.value) return "正在获取当前学生信息...";
  if (props.resourceLabel) return `结合当前资源：${props.resourceLabel}`;
  if (props.nodeName) return "围绕当前知识点进行 5E 学习引导";
  return "选择课程节点后，助教会结合上下文进行引导";
});
const studentFeedback = computed(() => effectivenessSummary.value?.student_view || null);
const recentStudentEvidence = computed(() =>
  (effectivenessSummary.value?.recent_evidence || []).slice(0, 3),
);
const effectivenessPolicyText = computed(() => {
  const status = studentFeedback.value?.evidence_status || effectivenessSummary.value?.evidence_status;
  if (status === "outcome_supported") {
    return "5E 引导已关联到后续学习结果，可作为诊断和路径推荐的辅助证据，但不会直接改写知识点掌握度。";
  }
  if (status === "insufficient_evidence" || status === "empty") {
    return "当前依据不足，系统会优先提示补充测验、作业或学习记录，不会强行判断学习效果。";
  }
  return "5E 引导记录只反映学习过程和互动质量，是辅助证据，不直接改写知识点掌握度。";
});

function nowSeconds() {
  return Date.now() / 1000;
}

function assistantMessage(content: string): ChatResponse {
  return {
    role: "assistant",
    content,
    buttons: [],
    resources: [],
    tests: [],
    timestamp: nowSeconds(),
  };
}

function messageClass(role: string) {
  return role === "user" ? "user" : "assistant";
}

function hasActions(msg: ChatResponse) {
  return Boolean(msg.buttons?.length || msg.resources?.length || msg.tests?.length);
}

function evidenceStatusLabel(status?: string | null) {
  const labels: Record<string, string> = {
    outcome_supported: "结果证据已支撑",
    process_only: "仅过程记录",
    insufficient_evidence: "依据待补充",
    empty: "暂无记录",
  };
  return labels[String(status || "")] || "引导反馈";
}

function stageLabel(stage?: string | null) {
  const labels: Record<string, string> = {
    engagement: "导入参与",
    exploration: "探索资源",
    explanation: "解释建构",
    elaboration: "迁移应用",
    evaluation: "测评反馈",
  };
  return labels[String(stage || "")] || "学习互动";
}

function evidenceKey(item: FiveEEffectivenessEvidence) {
  return `${item.record_id || item.calculated_at || item.stage || "evidence"}-${item.node_id || "node"}`;
}

async function scrollToBottom() {
  await nextTick();
  if (scrollRef.value) {
    scrollRef.value.scrollTop = scrollRef.value.scrollHeight;
  }
}

async function refreshEffectivenessSummary() {
  if (!props.studentId || !props.courseId) {
    effectivenessSummary.value = null;
    return;
  }
  effectivenessSummary.value = await fetchFiveEEffectivenessSummary({
    course_id: props.courseId,
    student_username: props.studentId,
    limit: 50,
  });
}

async function loadChatHistory() {
  if (!props.studentId || !props.courseId) {
    messages.value = [assistantMessage("登录后即可使用 5E AI 助教。")];
    effectivenessSummary.value = null;
    return;
  }

  try {
    const [history] = await Promise.all([fetchChatHistory(props.studentId, props.courseId), refreshEffectivenessSummary()]);
    messages.value = history.length
      ? history
      : [assistantMessage("你好，我是 5E AI 助教。你可以问我当前知识点怎么理解、怎么应用，也可以让我带你完成一次探究式学习。")];
  } catch {
    messages.value = [assistantMessage("历史对话暂时加载失败，但你仍然可以直接开始提问。")];
    effectivenessSummary.value = null;
  }

  await scrollToBottom();
}

async function sendMessage() {
  const message = input.value.trim();
  if (!message || loading.value || !props.studentId || !props.courseId) return;

  messages.value.push({
    role: "user",
    content: message,
    buttons: [],
    resources: [],
    tests: [],
    timestamp: nowSeconds(),
  });
  input.value = "";
  loading.value = true;

  const assistantIndex = messages.value.length;
  messages.value.push(assistantMessage(""));
  await scrollToBottom();

  try {
    const result = await sendFiveEChatMessage({
      content: message,
      courseId: props.courseId,
      studentId: props.studentId,
      nodeId: props.nodeName || null,
      onChunk: (chunk) => {
        try {
          messages.value[assistantIndex] = JSON.parse(chunk) as ChatResponse;
        } catch {
          messages.value[assistantIndex] = assistantMessage(chunk);
        }
      },
    });
    messages.value[assistantIndex] = result;
    try {
      await refreshEffectivenessSummary();
    } catch {
      effectivenessSummary.value = null;
    }
  } catch (error) {
    messages.value[assistantIndex] = assistantMessage(
      error instanceof Error ? error.message : "5E 助教响应失败，请稍后再试。",
    );
  } finally {
    loading.value = false;
    await scrollToBottom();
  }
}

async function handleNormalButton(btn: Button) {
  input.value = btn.send_text;
  await sendMessage();
}

watch(
  () => [props.courseId, props.studentId],
  () => {
    void loadChatHistory();
  },
);

onMounted(() => {
  void loadChatHistory();
});
</script>

<style scoped>
.fivee-chat {
  display: flex;
  min-height: 560px;
  height: 100%;
  flex-direction: column;
  gap: 12px;
}

.fivee-chat-head {
  padding-bottom: 10px;
  border-bottom: 1px solid #e5e7eb;
}

.fivee-chat-head strong {
  display: block;
  color: #111827;
  font-size: 15px;
  line-height: 1.45;
}

.fivee-chat-head p {
  margin: 4px 0 0;
  color: #64748b;
  font-size: 12px;
  line-height: 1.5;
}

.fivee-feedback {
  display: grid;
  gap: 10px;
  padding: 12px;
  border: 1px solid #bfdbfe;
  border-radius: 8px;
  background: #f8fbff;
}

.fivee-feedback-top {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 10px;
}

.fivee-feedback-label {
  display: block;
  margin-bottom: 3px;
  color: #2563eb;
  font-size: 12px;
  font-weight: 700;
}

.fivee-feedback strong {
  color: #0f172a;
  font-size: 14px;
  line-height: 1.4;
}

.fivee-status-pill {
  flex: 0 0 auto;
  padding: 3px 8px;
  border-radius: 999px;
  background: #dbeafe;
  color: #1d4ed8;
  font-size: 12px;
  font-weight: 700;
}

.fivee-feedback p,
.fivee-feedback ul {
  margin: 0;
  color: #334155;
  font-size: 12px;
  line-height: 1.6;
}

.fivee-policy {
  padding: 8px 10px;
  border-left: 3px solid #38bdf8;
  background: #f0f9ff;
}

.fivee-evidence-list {
  display: grid;
  gap: 8px;
}

.fivee-evidence-item {
  display: grid;
  gap: 4px;
  padding: 8px 10px;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  background: #fff;
}

.fivee-evidence-item div {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}

.fivee-evidence-item strong {
  font-size: 12px;
}

.fivee-evidence-item span {
  color: #64748b;
  font-size: 11px;
}

.fivee-feedback ul {
  padding-left: 18px;
}

.fivee-chat-scroll {
  flex: 1;
  min-height: 360px;
  overflow-y: auto;
  padding: 12px;
  display: flex;
  flex-direction: column;
  gap: 12px;
  border: 1px solid #e2e8f0;
  border-radius: 10px;
  background: #f8fafc;
}

.fivee-chat-bubble {
  width: fit-content;
  max-width: 92%;
  padding: 10px 12px;
  border-radius: 12px;
  line-height: 1.65;
  font-size: 13px;
  overflow-wrap: anywhere;
}

.fivee-chat-bubble.user {
  align-self: flex-end;
  background: #2563eb;
  color: #fff;
}

.fivee-chat-bubble.assistant {
  align-self: flex-start;
  border: 1px solid #e2e8f0;
  background: #fff;
  color: #0f172a;
}

.fivee-chat-role {
  margin-bottom: 4px;
  font-size: 11px;
  font-weight: 700;
  opacity: 0.72;
}

.fivee-chat-text {
  white-space: pre-wrap;
}

.fivee-chat-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 10px;
}

.fivee-action-btn {
  min-height: 30px;
  padding: 5px 10px;
  border: 1px solid #cbd5e1;
  border-radius: 6px;
  background: #fff;
  color: #334155;
  cursor: pointer;
  font-size: 12px;
}

.fivee-action-btn.success {
  border-color: #86efac;
  color: #15803d;
}

.fivee-action-btn.warning {
  border-color: #fcd34d;
  color: #a16207;
}

.fivee-chat-footer {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.fivee-chat-footer textarea {
  width: 100%;
  resize: vertical;
  min-height: 82px;
  padding: 10px 12px;
  border: 1px solid #cbd5e1;
  border-radius: 8px;
  color: #0f172a;
  font-size: 13px;
  line-height: 1.6;
  outline: none;
}

.fivee-chat-footer textarea:focus {
  border-color: #2563eb;
  box-shadow: 0 0 0 3px rgba(37, 99, 235, 0.12);
}

.fivee-send-btn {
  align-self: flex-end;
  min-height: 34px;
  padding: 7px 16px;
  border: none;
  border-radius: 6px;
  background: #2563eb;
  color: #fff;
  cursor: pointer;
  font-weight: 700;
}

.fivee-send-btn:disabled {
  cursor: not-allowed;
  opacity: 0.56;
}
</style>
