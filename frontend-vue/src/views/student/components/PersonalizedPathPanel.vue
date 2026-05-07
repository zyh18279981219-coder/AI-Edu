<template>
  <div class="student-learning-v2-path-panel">
    <div class="student-learning-v2-path-header">
      <div>
        <h2>🎯 个性化学习路径</h2>
        <p class="muted">基于你的学习数据，系统为你推荐以下学习顺序</p>
      </div>
      <button class="ghost-btn" type="button" :disabled="loading" @click="handleRegenerate">
        {{ loading ? '生成中...' : '重新规划' }}
      </button>
    </div>

    <div v-if="loading" class="state-card">正在生成个性化学习路径...</div>
    <div v-else-if="error" class="state-card error-state">{{ error }}</div>
    
    <template v-else-if="pathData">
      <!-- AI 建议 -->
      <div v-if="pathData.llm_advice" class="student-learning-v2-path-advice">
        <div class="student-learning-v2-path-advice-header">
          <strong>💡 AI 学习建议</strong>
        </div>
        <div class="student-learning-v2-path-advice-content">{{ pathData.llm_advice }}</div>
      </div>

      <!-- 排序原因 -->
      <div v-if="pathData.llm_order_reason" class="student-learning-v2-path-reason">
        <div class="student-learning-v2-path-reason-header">
          <strong>📋 排序依据</strong>
        </div>
        <div class="student-learning-v2-path-reason-content">{{ pathData.llm_order_reason }}</div>
      </div>

      <!-- 排序控制 -->
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

      <!-- 薄弱知识点列表 -->
      <div v-if="sortedNodes.length" class="student-learning-v2-path-nodes">
        <div class="student-learning-v2-path-nodes-header">
          <strong>需要加强的知识点（{{ sortedNodes.length }}个）</strong>
        </div>
        <div class="student-learning-v2-path-node-list">
          <div
            v-for="(node, index) in sortedNodes"
            :key="node.node_id"
            class="student-learning-v2-path-node-item"
          >
            <div class="student-learning-v2-path-node-rank">{{ index + 1 }}</div>
            <div class="student-learning-v2-path-node-content">
              <div class="student-learning-v2-path-node-title">{{ node.node_id }}</div>
              <div class="student-learning-v2-path-node-meta">
                <span>掌握度: {{ formatScore(node.mastery_score) }}%</span>
                <span>优先级: {{ node.priority || node.llm_priority || '-' }}</span>
              </div>
              <div v-if="node.resources && node.resources.length" class="student-learning-v2-path-node-resources">
                <span class="muted">推荐资源:</span>
                <a
                  v-for="(res, idx) in node.resources"
                  :key="idx"
                  :href="res.url"
                  target="_blank"
                  class="student-learning-v2-path-resource-link"
                >
                  {{ res.title || res.url }}
                </a>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- 无薄弱点状态 -->
      <div v-else class="student-learning-v2-path-empty">
        <div class="student-learning-v2-path-empty-icon">🎉</div>
        <div class="student-learning-v2-path-empty-text">暂无需要加强的知识点，继续保持！</div>
      </div>
    </template>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import { fetchCurrentUser } from "../../../api/login";
import { fetchCurrentLearningPath, generateLearningPath } from "../../../api/student";
import type { LearningPathResponse } from "../../../types/student";

const loading = ref(false);
const error = ref("");
const pathData = ref<LearningPathResponse | null>(null);
const sortMode = ref<"priority" | "mastery">("priority");

const sortedNodes = computed(() => {
  if (!pathData.value?.weak_nodes) return [];
  
  const nodes = [...pathData.value.weak_nodes];
  
  if (sortMode.value === "priority") {
    return nodes.sort((a, b) => {
      const priorityA = a.llm_priority ?? a.priority ?? 999;
      const priorityB = b.llm_priority ?? b.priority ?? 999;
      return priorityA - priorityB;
    });
  } else {
    return nodes.sort((a, b) => a.mastery_score - b.mastery_score);
  }
});

function formatScore(value?: number) {
  return Number(value ?? 0).toFixed(1);
}

async function loadPath(forceGenerate = false) {
  loading.value = true;
  error.value = "";
  
  try {
    const user = await fetchCurrentUser();
    
    if (forceGenerate) {
      pathData.value = await generateLearningPath(user.username);
    } else {
      try {
        pathData.value = await fetchCurrentLearningPath(user.username);
      } catch (err: any) {
        if (err.response?.status === 404) {
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

onMounted(() => {
  loadPath();
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
  padding: 24px;
  background: linear-gradient(135deg, #ffffff 0%, #f8fbff 100%);
  border: 1px solid #e2e8f0;
  border-radius: 12px;
  box-shadow: 0 4px 12px rgba(15, 23, 42, 0.04);
}

.student-learning-v2-path-header h2 {
  margin: 0 0 8px 0;
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
  color: #ffffff;
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
  gap: 16px;
  font-size: 13px;
  color: #64748b;
  margin-bottom: 8px;
}

.student-learning-v2-path-node-resources {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  align-items: center;
  font-size: 13px;
}

.student-learning-v2-path-resource-link {
  color: #2563eb;
  text-decoration: none;
  padding: 4px 8px;
  background: #eff6ff;
  border-radius: 4px;
  transition: all 0.2s;
}

.student-learning-v2-path-resource-link:hover {
  background: #dbeafe;
  text-decoration: underline;
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

@media (max-width: 640px) {
  .student-learning-v2-path-header {
    flex-direction: column;
    gap: 16px;
  }

  .student-learning-v2-path-controls {
    flex-direction: column;
    gap: 12px;
  }

  .student-learning-v2-path-node-item {
    flex-direction: column;
    gap: 12px;
  }
}
</style>
