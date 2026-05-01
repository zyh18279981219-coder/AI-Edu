<template>
  <div class="interaction-shell">
    <section class="hero-panel app-hero app-hero--teacher">
      <div class="app-hero-copy">
        <p class="eyebrow">Teaching Interaction</p>
        <h1>教学互动中心</h1>
        <p class="hero-desc">教师可在此发布公告、发起讨论并处理问答。公告和讨论会同步到学生端互动中心，并回流教师六维画像。</p>
      </div>
      <div class="app-hero-actions">
        <button class="ghost-btn" type="button" :disabled="loading" @click="loadAll">刷新</button>
      </div>
    </section>

    <section v-if="error" class="card-panel state-card error-state">{{ error }}</section>

    <section class="card-panel">
      <div class="section-head">
        <h3>互动分析看板</h3>
        <div style="display:flex;gap:8px;align-items:center;">
          <select v-model.number="analyticsWindowDays" class="input" style="min-width: 140px;" @change="loadAnalytics">
            <option :value="7">近7天</option>
            <option :value="30">近30天</option>
            <option :value="90">近90天</option>
          </select>
          <button class="ghost-btn" type="button" @click="loadAnalytics">更新</button>
        </div>
      </div>
      <div class="metrics-grid">
        <article class="metric-card">
          <span class="metric-label">公告总数</span>
          <strong class="metric-value">{{ analytics?.announcement_count ?? 0 }}</strong>
        </article>
        <article class="metric-card">
          <span class="metric-label">讨论总数</span>
          <strong class="metric-value">{{ analytics?.topic_count ?? 0 }}</strong>
        </article>
        <article class="metric-card">
          <span class="metric-label">近窗学生提问</span>
          <strong class="metric-value">{{ analytics?.recent_student_question_count ?? 0 }}</strong>
        </article>
        <article class="metric-card">
          <span class="metric-label">近窗教师回复</span>
          <strong class="metric-value">{{ analytics?.recent_teacher_reply_count ?? 0 }}</strong>
        </article>
        <article class="metric-card">
          <span class="metric-label">平均响应(分钟)</span>
          <strong class="metric-value">{{ analytics?.avg_teacher_response_minutes ?? "-" }}</strong>
        </article>
      </div>
      <div class="top-classes" v-if="analytics?.top_active_classes?.length">
        <strong>活跃班级 TOP</strong>
        <div class="top-classes-list">
          <span v-for="item in analytics.top_active_classes" :key="item.class_name" class="meta-chip">
            {{ item.class_name }} · {{ item.topic_count }} 话题
          </span>
        </div>
      </div>
    </section>

    <div class="two-col-layout">
      <section class="card-panel">
        <div class="section-head">
          <h3>发布公告</h3>
          <span class="muted">自动计入“在线互动频次”和“教学节奏控制”</span>
        </div>
        <label class="field">
          <span>公告标题</span>
          <input v-model="announcementForm.title" class="input" />
        </label>
        <div class="two-col">
          <label class="field">
            <span>班级</span>
            <select v-model="announcementForm.class_name" class="input">
              <option value="">未指定</option>
              <option v-for="item in classOptions" :key="item.value" :value="item.value">{{ item.label }}</option>
            </select>
          </label>
          <label class="field">
            <span>课程</span>
            <select v-model="announcementForm.course_id" class="input">
              <option value="">未指定</option>
              <option v-for="item in courseOptions" :key="item.value" :value="item.value">{{ item.label }}</option>
            </select>
          </label>
        </div>
        <label class="field">
          <span>公告内容</span>
          <textarea v-model="announcementForm.content" class="input input-textarea" rows="4" />
        </label>
        <button class="ghost-btn" type="button" :disabled="submittingAnnouncement" @click="submitAnnouncement">
          {{ submittingAnnouncement ? "发布中..." : "发布公告" }}
        </button>
      </section>

      <section class="card-panel">
        <div class="section-head">
          <h3>发起讨论</h3>
          <span class="muted">自动计入“在线互动频次”</span>
        </div>
        <label class="field">
          <span>讨论标题</span>
          <input v-model="topicForm.title" class="input" />
        </label>
        <div class="two-col">
          <label class="field">
            <span>班级</span>
            <select v-model="topicForm.class_name" class="input">
              <option value="">未指定</option>
              <option v-for="item in classOptions" :key="item.value" :value="item.value">{{ item.label }}</option>
            </select>
          </label>
          <label class="field">
            <span>课程</span>
            <select v-model="topicForm.course_id" class="input">
              <option value="">未指定</option>
              <option v-for="item in courseOptions" :key="item.value" :value="item.value">{{ item.label }}</option>
            </select>
          </label>
        </div>
        <label class="field">
          <span>讨论说明</span>
          <textarea v-model="topicForm.content" class="input input-textarea" rows="4" />
        </label>
        <button class="ghost-btn" type="button" :disabled="submittingTopic" @click="submitTopic">
          {{ submittingTopic ? "创建中..." : "发起讨论" }}
        </button>
      </section>
    </div>

    <section class="card-panel">
      <div class="section-head">
        <h3>公告列表</h3>
        <span class="muted">点击标题查看详情</span>
      </div>
      <div class="industry-table-wrap">
        <table class="industry-table">
          <thead>
          <tr>
            <th>标题</th>
            <th>班级</th>
            <th>课程</th>
            <th>创建时间</th>
            <th>最后修改</th>
            <th>发布时间</th>
            <th>内容摘要</th>
            <th>操作</th>
          </tr>
          </thead>
          <tbody>
          <tr v-for="item in announcements" :key="item.id" class="clickable-row" @click="openAnnouncement(item)">
            <td><strong>{{ item.title }}</strong></td>
            <td>{{ item.class_name || "-" }}</td>
            <td>{{ item.course_id || "-" }}</td>
            <td>{{ formatTime(item.created_at) }}</td>
            <td>{{ formatTime(item.updated_at) }}</td>
            <td>{{ formatTime(item.published_at) }}</td>
            <td>{{ summarize(item.content) }}</td>
            <td>
              <button class="ghost-btn tiny" type="button" @click.stop="beginEditAnnouncement(item)">编辑</button>
              <button class="ghost-btn tiny danger" type="button" @click.stop="deleteAnnouncement(item.id)">删除</button>
            </td>
          </tr>
          <tr v-if="!announcements.length">
            <td colspan="8">暂无公告</td>
          </tr>
          </tbody>
        </table>
      </div>
    </section>

    <section class="card-panel">
      <div class="section-head">
        <h3>讨论区</h3>
        <span class="muted">点击标题查看讨论详情并登记问答</span>
      </div>
      <div class="industry-table-wrap">
        <table class="industry-table">
          <thead>
          <tr>
            <th>讨论标题</th>
            <th>班级</th>
            <th>课程</th>
            <th>学生提问</th>
            <th>教师回复</th>
            <th>创建时间</th>
            <th>更新时间</th>
            <th>操作</th>
          </tr>
          </thead>
          <tbody>
          <tr v-for="topic in topics" :key="topic.id" class="clickable-row" @click="openTopic(topic)">
            <td><strong>{{ topic.title }}</strong></td>
            <td>{{ topic.class_name || "-" }}</td>
            <td>{{ topic.course_id || "-" }}</td>
            <td>{{ topic.student_question_count }}</td>
            <td>{{ topic.teacher_reply_count }}</td>
            <td>{{ formatTime(topic.created_at) }}</td>
            <td>{{ formatTime(topic.updated_at) }}</td>
            <td>
              <button class="ghost-btn tiny" type="button" @click.stop="beginEditTopic(topic)">编辑</button>
              <button class="ghost-btn tiny danger" type="button" @click.stop="deleteTopic(topic.id)">删除</button>
            </td>
          </tr>
          <tr v-if="!topics.length">
            <td colspan="8">暂无讨论话题</td>
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
          <span>创建：{{ formatTime(selectedAnnouncement.created_at) }}</span>
          <span>最后修改：{{ formatTime(selectedAnnouncement.updated_at) }}</span>
          <span>发布时间：{{ formatTime(selectedAnnouncement.published_at) }}</span>
        </div>
        <div class="reply-grid">
          <button class="ghost-btn tiny" type="button" @click="beginEditAnnouncement(selectedAnnouncement)">编辑公告</button>
          <button class="ghost-btn tiny danger" type="button" @click="deleteAnnouncement(selectedAnnouncement.id)">删除公告</button>
        </div>
        <label v-if="editingAnnouncementId === selectedAnnouncement.id" class="field">
          <span>编辑内容</span>
          <input v-model="announcementEditForm.title" class="input" />
          <textarea v-model="announcementEditForm.content" class="input input-textarea" rows="4" />
          <button class="ghost-btn tiny" type="button" @click="saveAnnouncementEdit">保存修改</button>
        </label>
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
          <span>创建：{{ formatTime(selectedTopic.created_at) }}</span>
          <span>最后修改：{{ formatTime(selectedTopic.updated_at) }}</span>
          <span>学生提问：{{ selectedTopic.student_question_count }}</span>
          <span>教师回复：{{ selectedTopic.teacher_reply_count }}</span>
        </div>
        <div class="reply-grid">
          <button class="ghost-btn tiny" type="button" @click="beginEditTopic(selectedTopic)">编辑讨论</button>
          <button class="ghost-btn tiny danger" type="button" @click="deleteTopic(selectedTopic.id)">删除讨论</button>
        </div>
        <label v-if="editingTopicId === selectedTopic.id" class="field">
          <span>编辑讨论内容</span>
          <input v-model="topicEditForm.title" class="input" />
          <textarea v-model="topicEditForm.content" class="input input-textarea" rows="4" />
          <button class="ghost-btn tiny" type="button" @click="saveTopicEdit">保存修改</button>
        </label>
        <p class="detail-content">{{ selectedTopic.content }}</p>
        <div class="posts-list">
          <div v-for="post in selectedTopic.posts || []" :key="post.id" class="post-row">
            <span class="relevance-pill" :class="post.author_role === 'teacher' ? 'mastery-high' : 'mastery-low'">
              {{ post.author_role === "teacher" ? "教师回复" : "学生提问" }}
            </span>
            <strong>{{ post.author_username }}</strong>
            <span class="muted">{{ formatTime(post.created_at) }}</span>
            <span class="muted">最后修改 {{ formatTime(post.updated_at || post.created_at) }}</span>
            <span class="post-content">{{ post.content }}</span>
            <span v-if="post.response_minutes !== null && post.response_minutes !== undefined" class="muted">
              响应 {{ post.response_minutes }} 分钟
            </span>
            <button class="ghost-btn tiny" type="button" @click="editPost(post.id, post.content)">编辑</button>
            <button class="ghost-btn tiny danger" type="button" @click="deletePost(post.id)">删除</button>
          </div>
          <div v-if="!(selectedTopic.posts || []).length" class="muted">暂无跟帖</div>
        </div>
        <div class="reply-grid">
          <label class="field">
            <span>登记学生提问</span>
            <input v-model="studentQuestionForms[selectedTopic.id].author_username" class="input" placeholder="学生用户名" />
            <textarea v-model="studentQuestionForms[selectedTopic.id].content" class="input input-textarea" rows="2" placeholder="学生提问内容" />
            <button class="ghost-btn" type="button" :disabled="postingTopicId === selectedTopic.id" @click="submitStudentQuestion(selectedTopic.id)">
              记录学生提问
            </button>
          </label>
          <label class="field">
            <span>登记教师回复</span>
            <textarea v-model="teacherReplyForms[selectedTopic.id]" class="input input-textarea" rows="2" placeholder="教师回复内容" />
            <button class="ghost-btn" type="button" :disabled="postingTopicId === selectedTopic.id" @click="submitTeacherReply(selectedTopic.id)">
              记录教师回复
            </button>
          </label>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { onBeforeUnmount, onMounted, reactive, ref } from "vue";
import {
  teachingCreateAnnouncement,
  teachingDeleteAnnouncement,
  teachingDeletePost,
  teachingDeleteTopic,
  teachingCreatePost,
  teachingCreateTopic,
  teachingGetInteractionAnalytics,
  teachingGetInteractionContextOptions,
  teachingListAnnouncements,
  teachingListTopics,
  teachingUpdateAnnouncement,
  teachingUpdatePost,
  teachingUpdateTopic,
} from "../../api/teaching";
import type {
  TeachingAnnouncement,
  TeachingContextOption,
  TeachingDiscussionTopic,
  TeachingInteractionAnalytics,
} from "../../types/teaching";

const loading = ref(false);
const error = ref("");
const submittingAnnouncement = ref(false);
const submittingTopic = ref(false);
const postingTopicId = ref("");

const announcements = ref<TeachingAnnouncement[]>([]);
const topics = ref<TeachingDiscussionTopic[]>([]);
const classOptions = ref<TeachingContextOption[]>([]);
const courseOptions = ref<TeachingContextOption[]>([]);
const selectedAnnouncement = ref<TeachingAnnouncement | null>(null);
const selectedTopic = ref<TeachingDiscussionTopic | null>(null);
const analytics = ref<TeachingInteractionAnalytics | null>(null);
const analyticsWindowDays = ref(30);
const editingAnnouncementId = ref("");
const editingTopicId = ref("");

const announcementForm = reactive({
  title: "",
  content: "",
  class_name: "",
  course_id: "",
});

const announcementEditForm = reactive({
  title: "",
  content: "",
  class_name: "",
  course_id: "",
});

const topicEditForm = reactive({
  title: "",
  content: "",
  class_name: "",
  course_id: "",
});

const topicForm = reactive({
  title: "",
  content: "",
  class_name: "",
  course_id: "",
});

const studentQuestionForms = reactive<Record<string, { author_username: string; content: string }>>({});
const teacherReplyForms = reactive<Record<string, string>>({});

function ensureTopicForms(topicId: string) {
  if (!studentQuestionForms[topicId]) {
    studentQuestionForms[topicId] = { author_username: "", content: "" };
  }
  if (!teacherReplyForms[topicId]) {
    teacherReplyForms[topicId] = "";
  }
}

async function loadAll() {
  loading.value = true;
  error.value = "";
  try {
    const [announcementRes, topicRes] = await Promise.all([
      teachingListAnnouncements(),
      teachingListTopics(),
    ]);
    announcements.value = announcementRes.announcements;
    topics.value = topicRes.topics;
    topics.value.forEach((topic) => ensureTopicForms(topic.id));
  } catch (err) {
    error.value = err instanceof Error ? err.message : "教学互动中心加载失败";
  } finally {
    loading.value = false;
  }
}

async function loadAnalytics() {
  try {
    const data = await teachingGetInteractionAnalytics(analyticsWindowDays.value);
    analytics.value = data.analytics;
  } catch (err) {
    error.value = err instanceof Error ? err.message : "互动分析加载失败";
  }
}

async function loadContextOptions() {
  try {
    const data = await teachingGetInteractionContextOptions();
    classOptions.value = data.class_options;
    courseOptions.value = data.course_options;
    if (!announcementForm.class_name && classOptions.value.length) {
      announcementForm.class_name = classOptions.value[0].value;
    }
    if (!topicForm.class_name && classOptions.value.length) {
      topicForm.class_name = classOptions.value[0].value;
    }
    if (!announcementForm.course_id && courseOptions.value.length) {
      announcementForm.course_id = courseOptions.value[0].value;
    }
    if (!topicForm.course_id && courseOptions.value.length) {
      topicForm.course_id = courseOptions.value[0].value;
    }
  } catch (err) {
    error.value = err instanceof Error ? err.message : "班级/课程选项加载失败";
  }
}

async function submitAnnouncement() {
  if (!announcementForm.title.trim() || !announcementForm.content.trim()) return;
  submittingAnnouncement.value = true;
  try {
    await teachingCreateAnnouncement({ ...announcementForm });
    announcementForm.title = "";
    announcementForm.content = "";
    announcementForm.class_name = "";
    announcementForm.course_id = "";
    await loadAll();
  } catch (err) {
    error.value = err instanceof Error ? err.message : "发布公告失败";
  } finally {
    submittingAnnouncement.value = false;
  }
}

async function submitTopic() {
  if (!topicForm.title.trim() || !topicForm.content.trim()) return;
  submittingTopic.value = true;
  try {
    await teachingCreateTopic({ ...topicForm });
    topicForm.title = "";
    topicForm.content = "";
    topicForm.class_name = "";
    topicForm.course_id = "";
    await loadAll();
  } catch (err) {
    error.value = err instanceof Error ? err.message : "发起讨论失败";
  } finally {
    submittingTopic.value = false;
  }
}

function beginEditAnnouncement(item: TeachingAnnouncement) {
  editingAnnouncementId.value = item.id;
  announcementEditForm.title = item.title;
  announcementEditForm.content = item.content;
  announcementEditForm.class_name = item.class_name || "";
  announcementEditForm.course_id = item.course_id || "";
  selectedAnnouncement.value = item;
}

async function saveAnnouncementEdit() {
  if (!editingAnnouncementId.value) return;
  try {
    await teachingUpdateAnnouncement(editingAnnouncementId.value, { ...announcementEditForm });
    editingAnnouncementId.value = "";
    await Promise.all([loadAll(), loadAnalytics()]);
    if (selectedAnnouncement.value) {
      selectedAnnouncement.value = announcements.value.find((item) => item.id === selectedAnnouncement.value?.id) || null;
    }
  } catch (err) {
    error.value = err instanceof Error ? err.message : "公告编辑失败";
  }
}

async function deleteAnnouncement(announcementId: string) {
  if (!confirm("确认删除该公告吗？")) return;
  try {
    await teachingDeleteAnnouncement(announcementId);
    if (selectedAnnouncement.value?.id === announcementId) selectedAnnouncement.value = null;
    await Promise.all([loadAll(), loadAnalytics()]);
  } catch (err) {
    error.value = err instanceof Error ? err.message : "公告删除失败";
  }
}

function beginEditTopic(topic: TeachingDiscussionTopic) {
  editingTopicId.value = topic.id;
  topicEditForm.title = topic.title;
  topicEditForm.content = topic.content;
  topicEditForm.class_name = topic.class_name || "";
  topicEditForm.course_id = topic.course_id || "";
  selectedTopic.value = topic;
}

async function saveTopicEdit() {
  if (!editingTopicId.value) return;
  try {
    await teachingUpdateTopic(editingTopicId.value, { ...topicEditForm });
    editingTopicId.value = "";
    await Promise.all([loadAll(), loadAnalytics()]);
    if (selectedTopic.value) {
      selectedTopic.value = topics.value.find((item) => item.id === selectedTopic.value?.id) || null;
    }
  } catch (err) {
    error.value = err instanceof Error ? err.message : "讨论编辑失败";
  }
}

async function deleteTopic(topicId: string) {
  if (!confirm("确认删除该讨论吗？删除后帖子也会被删除。")) return;
  try {
    await teachingDeleteTopic(topicId);
    if (selectedTopic.value?.id === topicId) selectedTopic.value = null;
    await Promise.all([loadAll(), loadAnalytics()]);
  } catch (err) {
    error.value = err instanceof Error ? err.message : "讨论删除失败";
  }
}

async function submitStudentQuestion(topicId: string) {
  const form = studentQuestionForms[topicId];
  if (!form?.author_username.trim() || !form.content.trim()) return;
  postingTopicId.value = topicId;
  try {
    await teachingCreatePost({
      topic_id: topicId,
      author_username: form.author_username,
      author_role: "student",
      content: form.content,
    });
    form.author_username = "";
    form.content = "";
    await loadAll();
    if (selectedTopic.value?.id === topicId) {
      selectedTopic.value = topics.value.find((item) => item.id === topicId) || null;
    }
  } catch (err) {
    error.value = err instanceof Error ? err.message : "记录学生提问失败";
  } finally {
    postingTopicId.value = "";
  }
}

async function submitTeacherReply(topicId: string) {
  const content = teacherReplyForms[topicId] || "";
  if (!content.trim()) return;
  const topic = topics.value.find((item) => item.id === topicId);
  const repliedTo = [...(topic?.posts || [])].reverse().find((item) => item.author_role === "student");
  postingTopicId.value = topicId;
  try {
    await teachingCreatePost({
      topic_id: topicId,
      author_username: "teacher",
      author_role: "teacher",
      content,
      replied_to_post_id: repliedTo?.id,
      replied_to_created_at: repliedTo?.created_at,
    });
    teacherReplyForms[topicId] = "";
    await loadAll();
    if (selectedTopic.value?.id === topicId) {
      selectedTopic.value = topics.value.find((item) => item.id === topicId) || null;
    }
  } catch (err) {
    error.value = err instanceof Error ? err.message : "记录教师回复失败";
  } finally {
    postingTopicId.value = "";
  }
}

async function editPost(postId: string, currentContent: string) {
  const next = prompt("编辑帖子内容", currentContent);
  if (next === null) return;
  const text = next.trim();
  if (!text) return;
  try {
    await teachingUpdatePost(postId, text);
    await Promise.all([loadAll(), loadAnalytics()]);
    if (selectedTopic.value) {
      selectedTopic.value = topics.value.find((item) => item.id === selectedTopic.value?.id) || null;
    }
  } catch (err) {
    error.value = err instanceof Error ? err.message : "帖子编辑失败";
  }
}

async function deletePost(postId: string) {
  if (!confirm("确认删除该帖子吗？")) return;
  try {
    await teachingDeletePost(postId);
    await Promise.all([loadAll(), loadAnalytics()]);
    if (selectedTopic.value) {
      selectedTopic.value = topics.value.find((item) => item.id === selectedTopic.value?.id) || null;
    }
  } catch (err) {
    error.value = err instanceof Error ? err.message : "帖子删除失败";
  }
}

function openAnnouncement(item: TeachingAnnouncement) {
  selectedAnnouncement.value = item;
}

function openTopic(topic: TeachingDiscussionTopic) {
  ensureTopicForms(topic.id);
  selectedTopic.value = topic;
}

function summarize(value: string) {
  const text = String(value || "");
  return text.length > 48 ? `${text.slice(0, 48)}...` : text;
}

function formatTime(value: string) {
  return value ? new Date(value).toLocaleString() : "-";
}

function handleEscClose(event: KeyboardEvent) {
  if (event.key !== "Escape") return;
  selectedAnnouncement.value = null;
  selectedTopic.value = null;
}

onMounted(async () => {
  await Promise.all([loadContextOptions(), loadAll(), loadAnalytics()]);
  window.addEventListener("keydown", handleEscClose);
});

onBeforeUnmount(() => {
  window.removeEventListener("keydown", handleEscClose);
});
</script>

<style scoped>
.two-col-layout,
.two-col,
.reply-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 16px;
}

.metrics-grid {
  display: grid;
  grid-template-columns: repeat(5, minmax(0, 1fr));
  gap: 12px;
}

.metric-card {
  border: 1px solid #e2e8f0;
  border-radius: 12px;
  padding: 12px;
  display: grid;
  gap: 8px;
  background: #f8fafc;
}

.metric-label {
  font-size: 12px;
  color: #64748b;
}

.metric-value {
  font-size: 20px;
  color: #0f172a;
}

.top-classes {
  margin-top: 12px;
  display: grid;
  gap: 8px;
}

.top-classes-list {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

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

.topic-card,
.posts-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.topic-card + .topic-card {
  margin-top: 20px;
  padding-top: 20px;
  border-top: 1px solid #e2e8f0;
}

.post-row {
  display: flex;
  gap: 10px;
  align-items: center;
  flex-wrap: wrap;
}

.post-content,
.topic-desc {
  color: #334155;
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

.tiny {
  padding: 4px 10px;
  font-size: 12px;
}

.danger {
  color: #b91c1c;
  border-color: #fecaca;
}

@media (max-width: 900px) {
  .metrics-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
  .two-col-layout,
  .two-col,
  .reply-grid {
    grid-template-columns: 1fr;
  }
}
</style>
