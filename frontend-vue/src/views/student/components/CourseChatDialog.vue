<template>
  <div class="chat-container">
    <div ref="scrollRef" class="chat-scroll">
      <article
        v-for="(msg, index) in messages"
        :key="index"
        class="chat-bubble"
        :class="msg.role === 'user' ? 'user' : 'assistant'"
      >
        <div class="chat-role">{{ msg.role === 'user' ? '用户' : 'AI 助教' }}</div>
        <div v-if="msg.role === 'assistant'" class="chat-text">
          <markdown :content="msg.content"/>
        </div>
        <div v-else class="chat-text">
          {{ msg.content }}
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
</template>

<script setup lang="ts">
import { ref, onMounted, nextTick } from 'vue';
import { apiClient } from "../../../api/client";

const props = defineProps({
  lessonId: {
    type: String,
    required: false,
  },
  studentId: {
    type: String,
    required: false,
  }
});

export interface ChatContentPart{
  text:string
}

export interface ChatContent{
  parts:ChatContentPart[],
  role:'user' | 'model'
}

// Experimental: Type definition for chat history based on chat_history.py model
export interface ChatResponse {
  model_version:string,
  content:ChatContent,
  partial:boolean,
  finish_reason:string,
  invocation_id:string,
  author:string,
  id:string,
  timestamp:Number
}

export interface ChatMessage{
  role:'assistant'|'user',
  content:string
}

const input = ref('');
const loading = ref(false);
const scrollRef = ref<HTMLDivElement | null>(null);

const messages = ref<ChatMessage[]>([]);

async function scrollToBottom() {
  await nextTick();
  if (scrollRef.value) {
    scrollRef.value.scrollTop = scrollRef.value.scrollHeight;
  }
}

// Experimental: Function to fetch conversation history
async function fetchChatHistory(userId: string, lessonId: string) {
  try {
    const { data } = await apiClient.get<ChatResponse[]>(`/api/chat/history`);
    return data;
  } catch (error) {
    console.error("Failed to fetch chat history:", error);
    return [];
  }
}

async function sendMessage() {
  const message = input.value.trim();
  if (!message || loading.value) return;

  messages.value.push({ role: 'user', content: message });
  input.value = '';
  loading.value = true;

  // Placeholder for the incoming assistant message
  const assistantMsgIndex = messages.value.length;
  messages.value.push({ role: 'assistant', content: '' });

  await scrollToBottom();

  try {
    const url = '/api/chat/message';
    const response = await fetch(url, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        content: message,
        lesson_id: props.lessonId,
        user_id: props.studentId
      })
    });

    if (!response.body) throw new Error('ReadableStream not supported');

    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let done = false;

    while (!done) {
      const { value, done: doneReading } = await reader.read();
      done = doneReading;
      const chunk = decoder.decode(value, { stream: true });

        try {
          messages.value[assistantMsgIndex].content+=chunk
          await scrollToBottom();
        } catch (e) {
          console.warn("Failed to parse stream chunk:", chunk);
        }

    }
  } catch (error) {
    console.error("Failed to send message:", error);
    messages.value[assistantMsgIndex].content = '发送失败，请检查网络连接或稍后再试。';
  } finally {
    loading.value = false;
    await scrollToBottom();
  }
}


onMounted(async () => {
  if (props.studentId && props.lessonId) {
    const history = await fetchChatHistory(props.studentId, props.lessonId);
    if (history && history.length > 0) {
      messages.value = history.filter(r=>{
        const role=r.content.role;
        return role=='model'||role=='user'
      }).map(r => ({
        role: r.content.role === 'model' ? 'assistant' : 'user',
        content: r.content.parts[0].text,
      }));
    }
  }

  if (messages.value.length === 0) {
    messages.value.push({ role: 'assistant', content: '你好！我是 AI 助教，关于本节课程内容有什么我可以帮你的吗？' });
  }

  await scrollToBottom();
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
