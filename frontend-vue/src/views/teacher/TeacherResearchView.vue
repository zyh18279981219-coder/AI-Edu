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
          <select v-model="form.class_name" class="input">
            <option value="">未指定</option>
            <option v-for="item in classOptions" :key="item.value" :value="item.value">{{ item.label }}</option>
          </select>
        </label>
      </div>
      <label class="field">
        <span>课程</span>
        <select v-model="form.course_id" class="input">
          <option value="">未指定</option>
          <option v-for="item in courseOptions" :key="item.value" :value="item.value">{{ item.label }}</option>
        </select>
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
            <th>发生时间</th>
            <th>创建时间</th>
            <th>最后修改</th>
            <th>操作</th>
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
            <td>{{ formatTime(item.created_at) }}</td>
            <td>{{ formatTime(item.updated_at) }}</td>
            <td>
              <button class="ghost-btn tiny" type="button" @click="beginEdit(item)">编辑</button>
              <button class="ghost-btn tiny danger" type="button" @click="deleteRecord(item.id)">删除</button>
            </td>
          </tr>
          <tr v-if="!records.length">
            <td colspan="9">暂无教研记录</td>
          </tr>
          </tbody>
        </table>
      </div>
    </section>

    <div v-if="editingId" class="modal-mask" @click.self="cancelEdit">
      <div class="modal-card">
        <div class="section-head">
          <h3>编辑教研记录</h3>
          <button class="ghost-btn" type="button" @click="cancelEdit">关闭</button>
        </div>
        <div class="two-col">
          <label class="field">
            <span>活动类型</span>
            <select v-model="editingForm.activity_type" class="input">
              <option value="research_post">教研发帖</option>
              <option value="shared_courseware">共享课件</option>
              <option value="co_preparation">集体备课</option>
            </select>
          </label>
          <label class="field">
            <span>发生时间</span>
            <input v-model="editingForm.happened_at" class="input" type="datetime-local" />
          </label>
        </div>
        <label class="field">
          <span>标题</span>
          <input v-model="editingForm.title" class="input" />
        </label>
        <label class="field">
          <span>描述</span>
          <textarea v-model="editingForm.description" class="input input-textarea" rows="4" />
        </label>
        <div class="two-col">
          <label class="field">
            <span>资源链接</span>
            <input v-model="editingForm.resource_link" class="input" />
          </label>
          <label class="field">
            <span>班级/教研组</span>
            <select v-model="editingForm.class_name" class="input">
              <option value="">未指定</option>
              <option v-for="item in classOptions" :key="item.value" :value="item.value">{{ item.label }}</option>
            </select>
          </label>
        </div>
        <label class="field">
          <span>课程</span>
          <select v-model="editingForm.course_id" class="input">
            <option value="">未指定</option>
            <option v-for="item in courseOptions" :key="item.value" :value="item.value">{{ item.label }}</option>
          </select>
        </label>
        <button class="ghost-btn" type="button" @click="saveEdit">保存修改</button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted, reactive, ref } from "vue";
import {
  teachingCreateResearchRecord,
  teachingDeleteResearchRecord,
  teachingGetResearchContextOptions,
  teachingListResearchRecords,
  teachingUpdateResearchRecord,
} from "../../api/teaching";
import type { TeachingContextOption, TeachingResearchRecord } from "../../types/teaching";

const loading = ref(false);
const submitting = ref(false);
const error = ref("");
const records = ref<TeachingResearchRecord[]>([]);
const classOptions = ref<TeachingContextOption[]>([]);
const courseOptions = ref<TeachingContextOption[]>([]);
const editingId = ref("");
const editingForm = reactive({
  activity_type: "research_post",
  title: "",
  description: "",
  resource_link: "",
  class_name: "",
  course_id: "",
  happened_at: "",
});

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

async function loadContextOptions() {
  try {
    const data = await teachingGetResearchContextOptions();
    classOptions.value = data.class_options;
    courseOptions.value = data.course_options;
    if (!form.class_name && classOptions.value.length) {
      form.class_name = classOptions.value[0].value;
    }
    if (!form.course_id && courseOptions.value.length) {
      form.course_id = courseOptions.value[0].value;
    }
  } catch (err) {
    error.value = err instanceof Error ? err.message : "班级/课程选项加载失败";
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

function beginEdit(item: TeachingResearchRecord) {
  editingId.value = item.id;
  editingForm.activity_type = item.activity_type;
  editingForm.title = item.title;
  editingForm.description = item.description || "";
  editingForm.resource_link = item.resource_link || "";
  editingForm.class_name = item.class_name || "";
  editingForm.course_id = item.course_id || "";
  editingForm.happened_at = item.happened_at ? new Date(item.happened_at).toISOString().slice(0, 16) : "";
}

function cancelEdit() {
  editingId.value = "";
}

async function saveEdit() {
  if (!editingId.value) return;
  try {
    await teachingUpdateResearchRecord(editingId.value, {
      ...editingForm,
      happened_at: editingForm.happened_at ? new Date(editingForm.happened_at).toISOString() : undefined,
    });
    editingId.value = "";
    await loadRecords();
  } catch (err) {
    error.value = err instanceof Error ? err.message : "更新教研记录失败";
  }
}

async function deleteRecord(recordId: string) {
  if (!confirm("确认删除该教研记录吗？")) return;
  try {
    await teachingDeleteResearchRecord(recordId);
    if (editingId.value === recordId) editingId.value = "";
    await loadRecords();
  } catch (err) {
    error.value = err instanceof Error ? err.message : "删除教研记录失败";
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

onMounted(async () => {
  await Promise.all([loadContextOptions(), loadRecords()]);
});
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
  width: min(880px, 92vw);
  max-height: 86vh;
  overflow: auto;
  border-radius: 18px;
  padding: 20px;
  background: #ffffff;
  box-shadow: 0 24px 60px rgba(15, 23, 42, 0.24);
  display: grid;
  gap: 14px;
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
  .two-col {
    grid-template-columns: 1fr;
  }
}
</style>
