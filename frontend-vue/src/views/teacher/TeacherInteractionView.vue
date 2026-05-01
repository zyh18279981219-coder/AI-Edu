<template>
  <div class="interaction-shell">
    <section class="hero-panel app-hero app-hero--teacher">
      <div class="app-hero-copy">
        <p class="eyebrow">Teaching Interaction</p>
        <h1>教学互动中心</h1>
        <p class="hero-desc">教师可在此创建公告、发起讨论、记录学生提问与教师回复，所有行为会自动回流教师六维图。</p>
      </div>
      <div class="app-hero-actions">
        <button class="ghost-btn" type="button" :disabled="loading" @click="loadAll">刷新</button>
      </div>
    </section>

    <section v-if="error" class="card-panel state-card error-state">{{ error }}</section>

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
            <input v-model="announcementForm.class_name" class="input" placeholder="如：大数据1班" />
          </label>
          <label class="field">
            <span>课程ID</span>
            <input v-model="announcementForm.course_id" class="input" placeholder="如：course_big_data" />
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
            <input v-model="topicForm.class_name" class="input" placeholder="如：大数据1班" />
          </label>
          <label class="field">
            <span>课程ID</span>
            <input v-model="topicForm.course_id" class="input" placeholder="如：course_big_data" />
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
        <span class="muted">共 {{ announcements.length }} 条</span>
      </div>
      <div class="industry-table-wrap">
        <table class="industry-table">
          <thead>
          <tr>
            <th>标题</th>
            <th>班级</th>
            <th>课程</th>
            <th>发布时间</th>
            <th>内容摘要</th>
          </tr>
          </thead>
          <tbody>
          <tr v-for="item in announcements" :key="item.id">
            <td>{{ item.title }}</td>
            <td>{{ item.class_name || "-" }}</td>
            <td>{{ item.course_id || "-" }}</td>
            <td>{{ formatTime(item.published_at) }}</td>
            <td>{{ summarize(item.content) }}</td>
          </tr>
          <tr v-if="!announcements.length">
            <td colspan="5">暂无公告</td>
          </tr>
          </tbody>
        </table>
      </div>
    </section>

    <section class="card-panel">
      <div class="section-head">
        <h3>讨论区</h3>
        <span class="muted">可登记学生提问与教师回复</span>
      </div>
      <div v-if="!topics.length" class="state-card">暂无讨论话题</div>
      <div v-for="topic in topics" :key="topic.id" class="topic-card">
        <div class="section-head compact">
          <div>
            <strong>{{ topic.title }}</strong>
            <span class="muted"> · {{ topic.class_name || "未指定班级" }} · 学生提问 {{ topic.student_question_count }} · 教师回复 {{ topic.teacher_reply_count }}</span>
          </div>
        </div>
        <p class="topic-desc">{{ topic.content }}</p>

        <div class="posts-list">
          <div v-for="post in topic.posts || []" :key="post.id" class="post-row">
            <span class="relevance-pill" :class="post.author_role === 'teacher' ? 'mastery-high' : 'mastery-low'">
              {{ post.author_role === "teacher" ? "教师回复" : "学生提问" }}
            </span>
            <strong>{{ post.author_username }}</strong>
            <span class="muted">{{ formatTime(post.created_at) }}</span>
            <span class="post-content">{{ post.content }}</span>
            <span v-if="post.response_minutes !== null && post.response_minutes !== undefined" class="muted">
              响应 {{ post.response_minutes }} 分钟
            </span>
          </div>
          <div v-if="!(topic.posts || []).length" class="muted">暂无跟帖</div>
        </div>

        <div class="reply-grid">
          <label class="field">
            <span>登记学生提问</span>
            <input v-model="studentQuestionForms[topic.id].author_username" class="input" placeholder="学生用户名" />
            <textarea v-model="studentQuestionForms[topic.id].content" class="input input-textarea" rows="2" placeholder="学生提问内容" />
            <button class="ghost-btn" type="button" :disabled="postingTopicId === topic.id" @click="submitStudentQuestion(topic.id)">
              记录学生提问
            </button>
          </label>

          <label class="field">
            <span>登记教师回复</span>
            <textarea v-model="teacherReplyForms[topic.id]" class="input input-textarea" rows="2" placeholder="教师回复内容" />
            <button class="ghost-btn" type="button" :disabled="postingTopicId === topic.id" @click="submitTeacherReply(topic.id)">
              记录教师回复
            </button>
          </label>
        </div>
      </div>
    </section>
  </div>
</template>

<script setup lang="ts">
import { onMounted, reactive, ref } from "vue";
import {
  teachingCreateAnnouncement,
  teachingCreatePost,
  teachingCreateTopic,
  teachingListAnnouncements,
  teachingListTopics,
} from "../../api/teaching";
import type { TeachingAnnouncement, TeachingDiscussionTopic } from "../../types/teaching";

const loading = ref(false);
const error = ref("");
const submittingAnnouncement = ref(false);
const submittingTopic = ref(false);
const postingTopicId = ref("");

const announcements = ref<TeachingAnnouncement[]>([]);
const topics = ref<TeachingDiscussionTopic[]>([]);

const announcementForm = reactive({
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
  } catch (err) {
    error.value = err instanceof Error ? err.message : "记录教师回复失败";
  } finally {
    postingTopicId.value = "";
  }
}

function summarize(value: string) {
  const text = String(value || "");
  return text.length > 48 ? `${text.slice(0, 48)}...` : text;
}

function formatTime(value: string) {
  return value ? new Date(value).toLocaleString() : "-";
}

onMounted(loadAll);
</script>

<style scoped>
.two-col-layout,
.two-col,
.reply-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 16px;
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

@media (max-width: 900px) {
  .two-col-layout,
  .two-col,
  .reply-grid {
    grid-template-columns: 1fr;
  }
}
</style>
