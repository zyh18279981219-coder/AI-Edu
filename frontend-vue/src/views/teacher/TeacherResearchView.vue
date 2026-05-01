<template>
  <div class="research-shell">
    <section class="hero-panel app-hero app-hero--teacher">
      <div class="app-hero-copy">
        <p class="eyebrow">Teaching Research</p>
        <h1>教研协同中心</h1>
        <p class="hero-desc">统一记录教研发帖、共享课件、集体备课等行为，自动回流教师六维图“专业投入”和“数字资源”。</p>
      </div>
      <div class="app-hero-actions">
        <button class="ghost-btn" type="button" :disabled="loading" @click="loadRecords">刷新</button>
      </div>
    </section>

    <section v-if="error" class="card-panel state-card error-state">{{ error }}</section>

    <section class="card-panel">
      <div class="section-head">
        <h3>新增教研记录</h3>
        <span class="muted">提交后会自动写入内部教研事件</span>
      </div>
      <div class="two-col">
        <label class="field">
          <span>活动类型</span>
          <select v-model="form.activity_type" class="input">
            <option value="research_post">教研发帖</option>
            <option value="shared_courseware">共享课件</option>
            <option value="co_preparation">集体备课</option>
          </select>
        </label>
        <label class="field">
          <span>发生时间</span>
          <input v-model="form.happened_at" class="input" type="datetime-local" />
        </label>
      </div>
      <label class="field">
        <span>标题</span>
        <input v-model="form.title" class="input" />
      </label>
      <label class="field">
        <span>描述</span>
        <textarea v-model="form.description" class="input input-textarea" rows="4" />
      </label>
      <div class="two-col">
        <label class="field">
          <span>资源链接</span>
          <input v-model="form.resource_link" class="input" placeholder="可选：共享文档或课件链接" />
        </label>
        <label class="field">
          <span>班级/教研组</span>
          <input v-model="form.class_name" class="input" placeholder="可选" />
        </label>
      </div>
      <label class="field">
        <span>课程ID</span>
        <input v-model="form.course_id" class="input" placeholder="可选" />
      </label>
      <button class="ghost-btn" type="button" :disabled="submitting" @click="submitRecord">
        {{ submitting ? "提交中..." : "保存教研记录" }}
      </button>
    </section>

    <section class="card-panel">
      <div class="section-head">
        <h3>教研记录列表</h3>
        <span class="muted">共 {{ records.length }} 条</span>
      </div>
      <div class="industry-table-wrap">
        <table class="industry-table">
          <thead>
          <tr>
            <th>类型</th>
            <th>标题</th>
            <th>说明</th>
            <th>资源</th>
            <th>班级/分组</th>
            <th>时间</th>
          </tr>
          </thead>
          <tbody>
          <tr v-for="item in records" :key="item.id">
            <td>{{ activityLabel(item.activity_type) }}</td>
            <td>{{ item.title }}</td>
            <td>{{ summarize(item.description) }}</td>
            <td>
              <a v-if="item.resource_link" :href="item.resource_link" target="_blank" rel="noreferrer">查看资源</a>
              <span v-else>-</span>
            </td>
            <td>{{ item.class_name || "-" }}</td>
            <td>{{ formatTime(item.happened_at) }}</td>
          </tr>
          <tr v-if="!records.length">
            <td colspan="6">暂无教研记录</td>
          </tr>
          </tbody>
        </table>
      </div>
    </section>
  </div>
</template>

<script setup lang="ts">
import { onMounted, reactive, ref } from "vue";
import { teachingCreateResearchRecord, teachingListResearchRecords } from "../../api/teaching";
import type { TeachingResearchRecord } from "../../types/teaching";

const loading = ref(false);
const submitting = ref(false);
const error = ref("");
const records = ref<TeachingResearchRecord[]>([]);

const form = reactive({
  activity_type: "research_post",
  title: "",
  description: "",
  resource_link: "",
  class_name: "",
  course_id: "",
  happened_at: "",
});

async function loadRecords() {
  loading.value = true;
  error.value = "";
  try {
    const data = await teachingListResearchRecords();
    records.value = data.records;
  } catch (err) {
    error.value = err instanceof Error ? err.message : "教研记录加载失败";
  } finally {
    loading.value = false;
  }
}

async function submitRecord() {
  if (!form.title.trim()) return;
  submitting.value = true;
  try {
    await teachingCreateResearchRecord({
      ...form,
      happened_at: form.happened_at ? new Date(form.happened_at).toISOString() : undefined,
    });
    form.activity_type = "research_post";
    form.title = "";
    form.description = "";
    form.resource_link = "";
    form.class_name = "";
    form.course_id = "";
    form.happened_at = "";
    await loadRecords();
  } catch (err) {
    error.value = err instanceof Error ? err.message : "保存教研记录失败";
  } finally {
    submitting.value = false;
  }
}

function formatTime(value: string) {
  return value ? new Date(value).toLocaleString() : "-";
}

function summarize(text: string) {
  const value = String(text || "");
  return value.length > 40 ? `${value.slice(0, 40)}...` : value || "-";
}

function activityLabel(value: string) {
  const map: Record<string, string> = {
    research_post: "教研发帖",
    shared_courseware: "共享课件",
    co_preparation: "集体备课",
  };
  return map[value] || value;
}

onMounted(loadRecords);
</script>

<style scoped>
.two-col {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 16px;
}

.field {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

@media (max-width: 900px) {
  .two-col {
    grid-template-columns: 1fr;
  }
}
</style>
