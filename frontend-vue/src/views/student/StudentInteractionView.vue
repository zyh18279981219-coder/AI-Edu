<template>
  <div class="student-interaction-shell">
    <section class="hero-panel app-hero app-hero--student">
      <div class="app-hero-copy">
        <p class="eyebrow">Class Interaction</p>
        <h1>班级互动中心</h1>
        <p class="hero-desc">查看教师公告与讨论话题，点击即可在弹窗中阅读详情并参与提问。</p>
      </div>
      <div class="app-hero-actions">
        <button class="ghost-btn" type="button" :disabled="loading" @click="loadAll">刷新</button>
      </div>
    </section>

    <section v-if="error" class="card-panel state-card error-state">{{ error }}</section>

    <section class="card-panel">
      <div class="section-head">
        <h3>公告列表</h3>
        <span class="muted">点击公告查看详情</span>
      </div>
      <div class="industry-table-wrap">
        <table class="industry-table">
          <thead>
          <tr>
            <th>标题</th>
            <th>班级</th>
            <th>课程</th>
            <th>发布时间</th>
          </tr>
          </thead>
          <tbody>
          <tr v-for="item in announcements" :key="item.id" class="clickable-row" @click="selectedAnnouncement = item">
            <td><strong>{{ item.title }}</strong></td>
            <td>{{ item.class_name || "-" }}</td>
            <td>{{ item.course_id || "-" }}</td>
            <td>{{ formatTime(item.published_at) }}</td>
          </tr>
          <tr v-if="!announcements.length">
            <td colspan="4">暂无公告</td>
          </tr>
          </tbody>
        </table>
      </div>
    </section>

    <section class="card-panel">
      <div class="section-head">
        <h3>讨论话题</h3>
        <span class="muted">点击话题查看详情并参与提问</span>
      </div>
      <div class="industry-table-wrap">
        <table class="industry-table">
          <thead>
          <tr>
            <th>标题</th>
            <th>班级</th>
            <th>课程</th>
            <th>提问数</th>
            <th>回复数</th>
            <th>更新时间</th>
          </tr>
          </thead>
          <tbody>
          <tr v-for="item in topics" :key="item.id" class="clickable-row" @click="openTopic(item)">
            <td><strong>{{ item.title }}</strong></td>
            <td>{{ item.class_name || "-" }}</td>
            <td>{{ item.course_id || "-" }}</td>
            <td>{{ item.student_question_count }}</td>
            <td>{{ item.teacher_reply_count }}</td>
            <td>{{ formatTime(item.updated_at) }}</td>
          </tr>
          <tr v-if="!topics.length">
            <td colspan="6">暂无讨论话题</td>
          </tr>
          </tbody>
        </table>
      </div>
    </section>

    <div v-if="selectedAnnouncement" class="modal-mask" @click.self="selectedAnnouncement = null">
      <div class="modal-card">
        <div class="section-head">
          <h3>{{ selectedAnnouncement.title }}</h3>
          <button class="ghost-btn" type="button" @click="selectedAnnouncement = null">关闭</button>
        </div>
        <div class="detail-meta">
          <span>班级：{{ selectedAnnouncement.class_name || "未指定" }}</span>
          <span>课程：{{ selectedAnnouncement.course_id || "未指定" }}</span>
          <span>发布时间：{{ formatTime(selectedAnnouncement.published_at) }}</span>
        </div>
        <p class="detail-content">{{ selectedAnnouncement.content }}</p>
      </div>
    </div>

    <div v-if="selectedTopic" class="modal-mask" @click.self="selectedTopic = null">
      <div class="modal-card">
        <div class="section-head">
          <h3>{{ selectedTopic.title }}</h3>
          <button class="ghost-btn" type="button" @click="selectedTopic = null">关闭</button>
        </div>
        <div class="detail-meta">
          <span>班级：{{ selectedTopic.class_name || "未指定" }}</span>
          <span>课程：{{ selectedTopic.course_id || "未指定" }}</span>
        </div>
        <p class="detail-content">{{ selectedTopic.content }}</p>
        <div class="posts-list">
          <div v-for="post in selectedTopic.posts || []" :key="post.id" class="post-row">
            <span class="relevance-pill" :class="post.author_role === 'teacher' ? 'mastery-high' : 'mastery-low'">
              {{ post.author_role === "teacher" ? "教师回复" : "学生提问" }}
            </span>
            <strong>{{ post.author_username }}</strong>
            <span class="muted">{{ formatTime(post.created_at) }}</span>
            <span class="post-content">{{ post.content }}</span>
          </div>
          <div v-if="!(selectedTopic.posts || []).length" class="muted">暂无跟帖</div>
        </div>

        <label class="field">
          <span>我要提问</span>
          <textarea v-model="questionDraft" class="input input-textarea" rows="3" placeholder="请输入你的问题" />
        </label>
        <button class="ghost-btn" type="button" :disabled="questionSubmitting" @click="submitQuestion">
          {{ questionSubmitting ? "提交中..." : "提交提问" }}
        </button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from "vue";
import {
  teachingCreateStudentQuestion,
  teachingListPublicAnnouncements,
  teachingListPublicTopics,
} from "../../api/teaching";
import type { TeachingAnnouncement, TeachingDiscussionTopic } from "../../types/teaching";

const loading = ref(false);
const error = ref("");
const questionSubmitting = ref(false);
const announcements = ref<TeachingAnnouncement[]>([]);
const topics = ref<TeachingDiscussionTopic[]>([]);
const selectedAnnouncement = ref<TeachingAnnouncement | null>(null);
const selectedTopic = ref<TeachingDiscussionTopic | null>(null);
const questionDraft = ref("");

async function loadAll() {
  loading.value = true;
  error.value = "";
  try {
    const [announcementRes, topicRes] = await Promise.all([
      teachingListPublicAnnouncements(),
      teachingListPublicTopics(),
    ]);
    announcements.value = announcementRes.announcements;
    topics.value = topicRes.topics;
    if (selectedTopic.value) {
      selectedTopic.value = topics.value.find((item) => item.id === selectedTopic.value?.id) || null;
    }
  } catch (err) {
    error.value = err instanceof Error ? err.message : "互动数据加载失败";
  } finally {
    loading.value = false;
  }
}

function openTopic(item: TeachingDiscussionTopic) {
  selectedTopic.value = item;
  questionDraft.value = "";
}

async function submitQuestion() {
  if (!selectedTopic.value || !questionDraft.value.trim()) return;
  questionSubmitting.value = true;
  try {
    await teachingCreateStudentQuestion(selectedTopic.value.id, questionDraft.value);
    questionDraft.value = "";
    await loadAll();
  } catch (err) {
    error.value = err instanceof Error ? err.message : "提问失败";
  } finally {
    questionSubmitting.value = false;
  }
}

function formatTime(value: string) {
  return value ? new Date(value).toLocaleString() : "-";
}

onMounted(loadAll);
</script>

<style scoped>
.clickable-row {
  cursor: pointer;
}

.clickable-row:hover {
  background: #f8fafc;
}

.modal-mask {
  position: fixed;
  inset: 0;
  background: rgba(15, 23, 42, 0.46);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1200;
  padding: 20px;
}

.modal-card {
  width: min(980px, 92vw);
  max-height: 86vh;
  overflow: auto;
  border-radius: 18px;
  padding: 20px;
  background: #ffffff;
  box-shadow: 0 24px 60px rgba(15, 23, 42, 0.24);
  display: grid;
  gap: 14px;
}

.field {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.posts-list {
  display: grid;
  gap: 10px;
}

.post-row {
  display: flex;
  gap: 10px;
  align-items: center;
  flex-wrap: wrap;
}

.detail-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  color: #475569;
  font-size: 13px;
}

.detail-content {
  white-space: pre-wrap;
  color: #1f2937;
}

@media (max-width: 900px) {
  .modal-card {
    width: 95vw;
  }
}
</style>
