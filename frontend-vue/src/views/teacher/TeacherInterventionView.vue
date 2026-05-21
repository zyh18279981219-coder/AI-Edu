<template>
  <div class="intervention-shell">
    <section class="hero-panel app-hero app-hero--teacher">
      <div class="app-hero-copy">
        <p class="eyebrow">AI 干预</p>
        <h1>AI 干预任务包</h1>
        <p class="hero-desc">
          阶段 1 先识别每位学生薄弱点，阶段 2 再生成可编辑任务包，教师确认后推送给对应学生。
        </p>
      </div>
      <div class="app-hero-actions">
        <button class="ghost-btn" type="button" :disabled="loading" @click="loadAll">刷新</button>
        <button class="ghost-btn" type="button" :disabled="diagnosing" @click="runStage1">
          {{ diagnosing ? "识别中..." : "阶段1：识别薄弱点" }}
        </button>
      </div>
    </section>

    <section v-if="error" class="card-panel state-card error-state">{{ error }}</section>

    <section class="card-panel">
      <div class="section-head">
        <h3>学生概览</h3>
        <span class="muted">共 {{ students.length }} 人</span>
      </div>
      <div class="industry-table-wrap">
        <table class="industry-table">
          <thead>
            <tr>
              <th>学生</th>
              <th>总体掌握度</th>
              <th>薄弱点数量</th>
              <th>作业提交数</th>
              <th>作业均分</th>
              <th>操作</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="item in students" :key="item.student_username">
              <td>{{ item.student_username }}</td>
              <td>{{ item.overall_mastery }}%</td>
              <td>{{ diagnosisMap[item.student_username]?.weak_nodes?.length ?? item.weak_node_count }}</td>
              <td>{{ item.homework_submission_count }}</td>
              <td>{{ item.homework_average_score ?? "-" }}</td>
              <td>
                <button
                  class="ghost-btn"
                  type="button"
                  :disabled="generatingStudent === item.student_username"
                  @click="generateForStudent(item.student_username)"
                >
                  {{ generatingStudent === item.student_username ? "生成中..." : "阶段2：AI生成任务包" }}
                </button>
              </td>
            </tr>
            <tr v-if="!students.length">
              <td colspan="6">暂无学生数据</td>
            </tr>
          </tbody>
        </table>
      </div>
    </section>

    <section class="card-panel">
      <div class="section-head">
        <h3>任务包草稿（教师可编辑）</h3>
        <span class="muted">仅草稿可编辑，推送后学生可见</span>
      </div>
      <div v-if="!draftPackages.length" class="state-card">暂无草稿，请先对学生执行阶段2生成。</div>
      <div v-for="pkg in draftPackages" :key="pkg.id" class="draft-card">
        <div class="section-head compact">
          <div>
            <strong>{{ pkg.student_username }}</strong>
            <span class="muted"> · 包ID {{ pkg.id.slice(0, 8) }}</span>
          </div>
          <div class="actions-row">
            <button class="ghost-btn" type="button" :disabled="savingId === pkg.id" @click="savePackage(pkg.id)">
              {{ savingId === pkg.id ? "保存中..." : "保存草稿" }}
            </button>
            <button class="ghost-btn" type="button" :disabled="pushingId === pkg.id" @click="pushPackage(pkg.id)">
              {{ pushingId === pkg.id ? "推送中..." : "推送给学生" }}
            </button>
          </div>
        </div>

        <label class="field">
          <span>教学策略</span>
          <textarea v-model="getDraft(pkg).strategy_summary" class="input input-textarea" rows="3" />
        </label>

        <div class="two-col">
          <label class="field">
            <span>基础概念（每行一条）</span>
            <textarea v-model="getDraft(pkg).conceptsText" class="input input-textarea" rows="4" />
          </label>
          <label class="field">
            <span>基础视频建议（每行一条）</span>
            <textarea v-model="getDraft(pkg).videosText" class="input input-textarea" rows="4" />
          </label>
        </div>

        <div class="question-block" v-for="(q, idx) in getDraft(pkg).questions" :key="q.id || `${pkg.id}-${idx}`">
          <div class="section-head compact">
            <strong>题目 {{ idx + 1 }}</strong>
          </div>
          <label class="field">
            <span>题型</span>
            <select v-model="q.question_type" class="input">
              <option value="fill_blank">填空题</option>
              <option value="single_choice">单选题</option>
              <option value="multiple_choice">多选题</option>
              <option value="code">编程题</option>
              <option value="subjective">主观题</option>
            </select>
          </label>
          <label class="field">
            <span>标题</span>
            <input v-model="q.title" class="input" />
          </label>
          <label class="field">
            <span>题干</span>
            <textarea v-model="q.prompt" class="input input-textarea" rows="3" />
          </label>
          <label class="field" v-if="q.question_type === 'single_choice' || q.question_type === 'multiple_choice'">
            <span>选项（每行一个，建议 A. xxx 格式）</span>
            <textarea v-model="q.optionsText" class="input input-textarea" rows="4" />
          </label>
          <label class="field" v-if="q.question_type !== 'subjective'">
            <span>标准答案</span>
            <input v-model="q.correct_answer" class="input" placeholder="填空写标准答案；选择题写 A 或 A,C；编程写核心预期" />
          </label>
          <label class="field" v-if="q.question_type === 'code'">
            <span>测试用例（每行一条：输入 => 期望）</span>
            <textarea v-model="q.testCasesText" class="input input-textarea" rows="4" placeholder="1 2 => 3" />
          </label>
          <div class="two-col">
            <label class="field">
              <span>参考答案</span>
              <textarea v-model="q.reference_answer" class="input input-textarea" rows="3" />
            </label>
            <label class="field">
              <span>评分细则</span>
              <textarea v-model="q.rubric" class="input input-textarea" rows="3" />
            </label>
          </div>
        </div>
      </div>
    </section>

    <section class="card-panel">
      <div class="section-head">
        <h3>学生执行进度</h3>
      </div>
      <div class="industry-table-wrap">
        <table class="industry-table">
          <thead>
            <tr>
              <th>包ID</th>
              <th>学生</th>
              <th>状态</th>
              <th>完成度(题数)</th>
              <th>评分概览</th>
              <th>备注</th>
              <th>更新时间</th>
              <th>操作</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="row in progressRows" :key="row.package_id">
              <td>{{ row.package_id.slice(0, 8) }}</td>
              <td>{{ row.student_username }}</td>
              <td>{{ statusLabel(row.student_status) }}</td>
              <td>{{ Math.round((row.completion_rate || 0) * 100) }}% ({{ row.answered_questions || 0 }}/{{ row.total_questions || 0 }})</td>
              <td>AI {{ row.average_ai_score ?? "-" }} / 教师 {{ row.average_teacher_score ?? "-" }} / 最终 {{ row.average_final_score ?? "-" }}</td>
              <td>{{ row.student_note || "-" }}</td>
              <td>{{ formatTime(row.updated_at) }}</td>
              <td>
                <button class="ghost-btn" type="button" @click="goDetail(row.package_id)">查看详情与判题</button>
              </td>
            </tr>
            <tr v-if="!progressRows.length">
              <td colspan="8">暂未推送任务包</td>
            </tr>
          </tbody>
        </table>
      </div>
    </section>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import { useRouter } from "vue-router";
import {
  interventionGenerateDraft,
  interventionListTeacherPackages,
  interventionPushTeacherPackage,
  interventionTeacherDiagnose,
  interventionTeacherProgress,
  interventionTeacherStudentsOverview,
  interventionUpdateTeacherPackage,
} from "../../api/intervention";
import type {
  InterventionDiagnosis,
  InterventionPackage,
  InterventionQuestion,
  TeacherInterventionStudentOverview,
} from "../../types/intervention";

const loading = ref(false);
const diagnosing = ref(false);
const error = ref("");
const generatingStudent = ref("");
const savingId = ref("");
const pushingId = ref("");

const students = ref<TeacherInterventionStudentOverview[]>([]);
const diagnosis = ref<InterventionDiagnosis[]>([]);
const packages = ref<InterventionPackage[]>([]);
const progressRows = ref<
  Array<{
    package_id: string;
    student_username: string;
    student_status: string;
    completion_rate: number;
    answered_questions?: number;
    total_questions?: number;
    student_note?: string;
    average_final_score?: number | null;
    average_ai_score?: number | null;
    average_teacher_score?: number | null;
    updated_at: string;
  }>
>([]);
const router = useRouter();

const draftMap = ref<
  Record<
    string,
    {
      strategy_summary: string;
      conceptsText: string;
      videosText: string;
        questions: Array<{
          id?: string;
          title: string;
          prompt: string;
          question_type: "fill_blank" | "single_choice" | "multiple_choice" | "code" | "subjective";
          optionsText: string;
          correct_answer: string;
          reference_answer: string;
          rubric: string;
          testCasesText: string;
          difficulty: string;
        }>;
      }
  >
>({});

const diagnosisMap = computed(() =>
  Object.fromEntries(diagnosis.value.map((item) => [item.student_username, item])),
);

const draftPackages = computed(() => packages.value.filter((item) => item.stage === "draft"));

function formatTime(value?: string) {
  if (!value) return "-";
  return new Date(value).toLocaleString();
}

function statusLabel(status: string) {
  if (status === "accepted") return "已接受";
  if (status === "declined") return "暂不做";
  if (status === "in_progress") return "进行中";
  if (status === "completed") return "已完成";
  return "待处理";
}

function linesToList(text: string) {
  return text
    .split(/\r?\n/g)
    .map((x) => x.trim())
    .filter(Boolean);
}

function parseTestCases(text: string) {
  return linesToList(text)
    .map((line) => {
      const parts = line.split("=>");
      if (parts.length < 2) return null;
      const input = parts[0].trim();
      const expected = parts.slice(1).join("=>").trim();
      if (!input && !expected) return null;
      return { input, expected };
    })
    .filter((x): x is { input: string; expected: string } => !!x);
}

function formatQuestionForDraft(q: InterventionQuestion) {
  return {
    id: q.id,
    title: q.title,
    prompt: q.prompt,
    question_type: q.question_type || "subjective",
    optionsText: (q.options || []).join("\n"),
    correct_answer: q.correct_answer || "",
    reference_answer: q.reference_answer,
    rubric: q.rubric,
    testCasesText: (q.test_cases || []).map((item) => `${item.input} => ${item.expected}`).join("\n"),
    difficulty: q.difficulty || "中等",
  };
}

function ensureDraftMap(items: InterventionPackage[]) {
  for (const pkg of items) {
    if (pkg.stage !== "draft") continue;
    if (draftMap.value[pkg.id]) continue;
      draftMap.value[pkg.id] = {
        strategy_summary: pkg.strategy_summary || "",
        conceptsText: (pkg.recommended_concepts || []).join("\n"),
        videosText: (pkg.recommended_videos || []).join("\n"),
        questions: (pkg.questions || []).map((q) => formatQuestionForDraft(q)),
      };
    }
  }

function getDraft(pkg: InterventionPackage) {
  if (!draftMap.value[pkg.id]) {
    ensureDraftMap([pkg]);
  }
  return draftMap.value[pkg.id];
}

async function loadAll() {
  loading.value = true;
  error.value = "";
  try {
    const [overviewRes, diagnoseRes, packageRes, progressRes] = await Promise.all([
      interventionTeacherStudentsOverview(),
      interventionTeacherDiagnose(),
      interventionListTeacherPackages(),
      interventionTeacherProgress(),
    ]);
    students.value = overviewRes.data.students || [];
    diagnosis.value = diagnoseRes.data.diagnosis || [];
    packages.value = packageRes.packages || [];
    progressRows.value = progressRes.rows || [];
    ensureDraftMap(packages.value);
  } catch (e) {
    error.value = e instanceof Error ? e.message : "加载失败";
  } finally {
    loading.value = false;
  }
}

async function runStage1() {
  diagnosing.value = true;
  error.value = "";
  try {
    const res = await interventionTeacherDiagnose();
    diagnosis.value = res.data.diagnosis || [];
  } catch (e) {
    error.value = e instanceof Error ? e.message : "薄弱点识别失败";
  } finally {
    diagnosing.value = false;
  }
}

async function generateForStudent(studentUsername: string) {
  generatingStudent.value = studentUsername;
  error.value = "";
  try {
    await interventionGenerateDraft({
      student_username: studentUsername,
      question_count: 3,
      difficulty: "中等",
    });
    await loadAll();
  } catch (e) {
    error.value = e instanceof Error ? e.message : "生成任务包失败";
  } finally {
    generatingStudent.value = "";
  }
}

async function savePackage(packageId: string) {
  const draft = draftMap.value[packageId];
  if (!draft) return;
  savingId.value = packageId;
  error.value = "";
  try {
    await interventionUpdateTeacherPackage(packageId, {
      strategy_summary: draft.strategy_summary,
      recommended_concepts: linesToList(draft.conceptsText),
      recommended_videos: linesToList(draft.videosText),
      questions: draft.questions.map((q) => ({
        id: q.id,
        title: q.title,
        prompt: q.prompt,
        question_type: q.question_type,
        options: linesToList(q.optionsText),
        correct_answer: q.correct_answer,
        reference_answer: q.reference_answer,
        rubric: q.rubric,
        test_cases: parseTestCases(q.testCasesText),
        difficulty: q.difficulty,
      })),
    });
    await loadAll();
  } catch (e) {
    error.value = e instanceof Error ? e.message : "保存失败";
  } finally {
    savingId.value = "";
  }
}

async function pushPackage(packageId: string) {
  pushingId.value = packageId;
  error.value = "";
  try {
    await savePackage(packageId);
    await interventionPushTeacherPackage(packageId);
    await loadAll();
  } catch (e) {
    error.value = e instanceof Error ? e.message : "推送失败";
  } finally {
    pushingId.value = "";
  }
}

function goDetail(packageId: string) {
  router.push({ name: "teacher-intervention-detail", params: { packageId } });
}

onMounted(loadAll);
</script>

<style scoped>
.intervention-shell {
  display: grid;
  gap: 16px;
}

.draft-card {
  border: 1px solid #e2e8f0;
  border-radius: 12px;
  padding: 12px;
  margin-bottom: 12px;
  background: #f8fafc;
}

.question-block {
  border: 1px solid #dbe4f0;
  border-radius: 10px;
  padding: 10px;
  margin-top: 10px;
  background: #fff;
}

.field {
  display: grid;
  gap: 6px;
  margin-top: 10px;
}

.two-col {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 10px;
}

.input {
  width: 100%;
  border: 1px solid #d0d7de;
  border-radius: 8px;
  padding: 8px 10px;
  font-size: 14px;
}

.input-textarea {
  resize: vertical;
  line-height: 1.6;
}

@media (max-width: 900px) {
  .two-col {
    grid-template-columns: 1fr;
  }
}
</style>

