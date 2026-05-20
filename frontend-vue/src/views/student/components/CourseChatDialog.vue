<template>
  <div v-if="courseId!=undefined">
    course
  </div>
  <br/>
  <div v-if="studentId!=null">
    stu
  </div>
  <br/>
  <div v-if="studentId!=null && courseId!=null">
    courseId: {{ courseId }} <br/>
    student: {{ studentId }}
    <div class="chat-container">
      <div ref="scrollRef" class="chat-scroll">
        <article
            v-for="(msg, index) in messages"
            :key="index"
            class="chat-bubble"
            :class="msg.role"
        >
          <div class="chat-role">{{ msg.role === 'user' ? '用户' : 'AI 助教' }}</div>
          <div v-if="msg.role === 'user'" class="chat-text">
            {{msg.content}}
          </div>
          <div v-else class="chat-text">
            <markdown :content="msg.content"/>
            <div v-if="msg.buttons?.length || msg.resources?.length || msg.tests?.length" class="chat-actions">
              <el-button v-for="(btn, bIdx) in msg.buttons" :key="'btn-' + bIdx" size="small" round
                         @click="handleNormalButton(btn)">
                {{ btn.show_text }}
              </el-button>
              <el-button v-for="(res, rIdx) in msg.resources" :key="'res-' + rIdx" size="small" type="success" plain
                         round @click="handleResourceButton(res)">
                📚 {{ res.show_text }}
              </el-button>
              <el-button v-for="(tst, tIdx) in msg.tests" :key="'tst-' + tIdx" size="small" type="warning" plain round
                         @click="handleTestButton(tst)">
                📝 {{ tst.show_text }}
              </el-button>
            </div>
          </div>
        </article>
        <div v-if="loading" class="chat-bubble bot loading">
          <div class="chat-role">AI 助教</div>
          <div class="chat-text">正在思考中...</div>
        </div>
      </div>

      <footer class="chat-footer">
        <el-input
            v-model="input"
            type="textarea"
            :rows="3"
            placeholder="输入你的问题..."
            :disabled="loading"
            @keydown.enter.prevent="sendMessage"
        />
        <el-button
            :loading="loading"
            class="send-btn el-button--primary"
            @click="sendMessage"
        >
          发送
        </el-button>
      </footer>
    </div>
  </div>
</template>

<script setup lang="ts">
import {ref, onMounted, nextTick, watch} from 'vue';
import {fetchChatHistory} from "../../../api/5E";
import {ChatResponse, Button, Resource, Test} from "../../../types/5E";

const props = defineProps({
  courseId: {
    type: String,
    required: false,
  },
  studentId: {
    type: String,
    required: false,
  }
});

const input = ref('');
const loading = ref(false);
const scrollRef = ref<HTMLDivElement | null>(null);

const messages = ref<ChatResponse[]>([]);

async function scrollToBottom() {
  await nextTick();
  if (scrollRef.value) {
    scrollRef.value.scrollTop = scrollRef.value.scrollHeight;
  }
}

async function loadChatHistory() {
  if (props.studentId && props.courseId) {
    messages.value = []; // Clear current messages
    const history = await fetchChatHistory(props.studentId.toString(), props.courseId.toString());
    if (history && history.length > 0) {
      messages.value = history
    }
  }

  await scrollToBottom();
}

async function sendMessage() {
  const message = input.value.trim();
  if (!message || loading.value) return;

  messages.value.push({
    role: 'user',
    content: message,
    buttons: [],
    resources: [],
    tests: [],
    timestamp: (Date.now() + performance.now()) / 1000
  });
  input.value = '';
  loading.value = true;

  // Placeholder for the incoming assistant message
  const assistantMsgIndex = messages.value.length;
  messages.value.push({
    role: 'assistant',
    content: '',
    buttons: [],
    resources: [],
    tests: [],
    timestamp: (Date.now() + performance.now()) / 1000
  });

  await scrollToBottom();

  try {
    const url = '/api/5e/chat/message';
    const response = await fetch(url, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        content: message,
        course_id: props.courseId?.toString(),
        user_id: props.studentId?.toString()
      })
    });

    if (!response.body) throw new Error('ReadableStream not supported');

    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let done = false;
    let accumulatedContent = ''; // Accumulate content text

    while (!done) {
      const {value, done: doneReading} = await reader.read();
      done = doneReading;
      const chunk = decoder.decode(value, {stream: true});

      // Append chunk to content
      accumulatedContent += chunk;
      messages.value[assistantMsgIndex] = JSON.parse(accumulatedContent);
      await scrollToBottom();
    }

  } catch (error) {
    console.error("Failed to send message:", error);
    messages.value[assistantMsgIndex].content = '发送失败，请检查网络连接或稍后再试。';
  } finally {
    loading.value = false;
    await scrollToBottom();
  }
}

async function handleNormalButton(btn: Button) {
  input.value = btn.send_text;
  await sendMessage();
}

function handleResourceButton(res: Resource) {
  // Logic to jump to resource. This could be a router push or emitting an event.
  console.log('Navigating to resource:', res.id, res.show_text);
}

function handleTestButton(tst: Test) {
  // Logic to jump to test.
  console.log('Navigating to test:', tst.id, tst.show_text);
}

watch([() => props.courseId, () => props.studentId],
    async ([newCourseId, newStudentId], [oldCourseId, oldStudentId]) => {
      if (newCourseId !== oldCourseId || newStudentId !== oldStudentId) {
        if (newCourseId && newStudentId) {
          await loadChatHistory();
        }
      }
    });

</script>

<style scoped>
.chat-container {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.chat-scroll {
  flex: 1;
  overflow-y: auto;
  padding: 16px;
  display: flex;
  flex-direction: column;
  gap: 16px;
  border: 1px solid var(--line);
  border-radius: 12px;
  background: #f8fbff;
}

.chat-bubble {
  max-width: 85%;
  width: fit-content;
  padding: 12px 16px;
  border-radius: 16px;
  line-height: 1.6;
  font-size: 14px;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);
}

.chat-bubble.user {
  align-self: flex-end;
  background: var(--primary);
  color: #fff;
  border-bottom-right-radius: 4px;
}

.chat-bubble.assistant {
  align-self: flex-start;
  background: #fff;
  border: 1px solid var(--line);
  border-bottom-left-radius: 4px;
}

.chat-role {
  font-size: 11px;
  font-weight: 700;
  margin-bottom: 4px;
  opacity: 0.7;
}

.chat-text {
  white-space: pre-wrap;
  word-break: break-word;
}

.chat-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 12px;
}

.chat-footer {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.send-btn {
  align-self: flex-end;
}

.loading .chat-text {
  font-style: italic;
  color: var(--muted);
}
</style>