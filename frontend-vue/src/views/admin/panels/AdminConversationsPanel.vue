<template>
  <section class="admin-conversations">
    <div class="card-panel admin-filter-grid">
      <div class="field">
        <span>模块筛选</span>
        <el-select v-model="filterState.module" placeholder="全部模块" clearable>
          <el-option value="" label="全部模块" />
          <el-option v-for="module in moduleOptions" :key="module" :value="module" :label="getModuleLabel(module)" />
        </el-select>
      </div>
      <div class="field">
        <span>模型筛选</span>
        <el-select v-model="filterState.model" placeholder="全部模型" clearable>
          <el-option value="" label="全部模型" />
          <el-option v-for="model in modelOptions" :key="model" :value="model" :label="model" />
        </el-select>
      </div>
      <div class="field">
        <span>时间范围</span>
        <el-select v-model="filterState.timeRange" placeholder="全部时间">
          <el-option value="all" label="全部时间" />
          <el-option value="today" label="今天" />
          <el-option value="week" label="近 7 天" />
          <el-option value="month" label="近 30 天" />
        </el-select>
      </div>
      <div class="field">
        <span>搜索内容</span>
        <el-input v-model="filterState.search" placeholder="搜索请求或回答内容" clearable />
      </div>
    </div>

    <div class="stack-list">
      <article v-for="item in filteredConversations" :key="item.id" class="list-card admin-conversation-card">
        <div class="section-head">
          <div>
            <div class="list-title">{{ getModuleLabel(item.module) }}</div>
            <div class="list-meta">
              {{ formatDateTime(item.timestamp) }} · {{ item.model || "未知模型" }} · Token {{ formatCount(item.totalTokens) }}
            </div>
          </div>
          <el-button plain @click="toggleConversation(item.id)">
            {{ expandedIds.has(item.id) ? "收起详情" : "展开详情" }}
          </el-button>
        </div>

        <div v-if="expandedIds.has(item.id)" class="admin-conversation-body">
          <div class="admin-conversation-section">
            <strong>用户请求</strong>
            <pre>{{ item.requestText || "暂无请求内容" }}</pre>
          </div>
          <div class="admin-conversation-section">
            <strong>AI 响应</strong>
            <pre>{{ item.responseText || "暂无响应内容" }}</pre>
          </div>
        </div>
      </article>
    </div>
  </section>
</template>

<script setup lang="ts">
import { computed, reactive, ref } from "vue";
import type { AdminLlmLog } from "../../../api/studentTwin";

interface ConversationRow {
  id: number;
  timestamp: string;
  module: string;
  model: string;
  totalTokens: number;
  requestText: string;
  responseText: string;
}

const props = defineProps<{
  logs: AdminLlmLog[];
}>();

const expandedIds = ref(new Set<number>());

const filterState = reactive({
  module: "",
  model: "",
  timeRange: "all",
  search: "",
});

const modelOptions = computed(() => {
  const rows = new Set<string>();
  props.logs.forEach((log) => rows.add(log.request?.model || "Unknown"));
  return Array.from(rows);
});

const moduleOptions = computed(() => Array.from(new Set(props.logs.map((log) => log.module || "Unknown"))));

const conversationRows = computed<ConversationRow[]>(() => {
  return props.logs.map((log, index) => ({
    id: index,
    timestamp: log.timestamp,
    module: log.module || "Unknown",
    model: log.request?.model || "Unknown",
    totalTokens: log.response?.usage?.total_tokens ?? 0,
    requestText: (log.request?.messages ?? [])
      .map((message) => `[${message.role === "user" ? "用户" : message.role === "assistant" ? "助手" : message.role}] ${message.content}`)
      .join("\n\n"),
    responseText: log.response?.choices?.[0]?.message?.content || "",
  }));
});

const filteredConversations = computed(() => {
  const now = Date.now();
  return [...conversationRows.value]
    .filter((item) => {
      if (filterState.module && item.module !== filterState.module) return false;
      if (filterState.model && item.model !== filterState.model) return false;
      if (filterState.timeRange === "today") {
        const start = new Date();
        start.setHours(0, 0, 0, 0);
        if (new Date(item.timestamp).getTime() < start.getTime()) return false;
      }
      if (filterState.timeRange === "week" && new Date(item.timestamp).getTime() < now - 7 * 24 * 60 * 60 * 1000) return false;
      if (filterState.timeRange === "month" && new Date(item.timestamp).getTime() < now - 30 * 24 * 60 * 60 * 1000) return false;
      const keyword = filterState.search.trim().toLowerCase();
      if (!keyword) return true;
      return `${item.requestText} ${item.responseText}`.toLowerCase().includes(keyword);
    })
    .sort((a, b) => new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime());
});

function formatCount(value: number) {
  if (value >= 1_000_000) return `${(value / 1_000_000).toFixed(1)}M`;
  if (value >= 1_000) return `${(value / 1_000).toFixed(1)}K`;
  return String(Math.round(value));
}

function formatDateTime(value: string) {
  return new Date(value).toLocaleString("zh-CN");
}

function getModuleLabel(module: string) {
  const map: Record<string, string> = {
    "AgentModule.edu_agent": "AI 助教",
    "QuizModule.quiz_operations": "测验生成",
    "SummaryModule.summary_generator": "知识总结",
    "LearningPlanModule.learning_plan": "学习计划",
    "frontend.quizpage": "前端测验",
  };
  return map[module] || module;
}

function toggleConversation(id: number) {
  const next = new Set(expandedIds.value);
  if (next.has(id)) next.delete(id);
  else next.add(id);
  expandedIds.value = next;
}
</script>
