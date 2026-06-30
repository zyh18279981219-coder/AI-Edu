<template>
  <div class="intervention-shell">
    <section class="hero-panel app-hero app-hero--teacher">
      <div class="app-hero-copy">
        <p class="eyebrow">AI 干预</p>
        <h1>教师智能干预任务包</h1>
        <p class="hero-desc">
          教师根据诊断证据生成可编辑任务包，确认后推送给学生执行，并持续跟踪完成情况。
        </p>
      </div>
      <div class="app-hero-actions">
        <button class="ghost-btn" type="button" :disabled="loading" @click="loadAll">刷新</button>
        <button class="ghost-btn" type="button" :disabled="diagnosing" @click="runStage1">
          {{ diagnosing ? "识别中..." : "识别薄弱点" }}
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
                  {{ generatingStudent === item.student_username ? "生成中..." : "生成任务包草稿" }}
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
        <span class="muted">草稿可编辑，推送后学生可见</span>
      </div>
      <div v-if="!draftPackages.length" class="state-card">暂无草稿，请先为学生生成任务包。</div>
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

        <div class="task-edit-section">
          <div class="section-head compact">
            <strong>推荐资源任务</strong>
            <button class="ghost-btn" type="button" @click="addResourceTask(pkg.id)">添加资源</button>
          </div>
          <div
            v-for="(task, idx) in getDraft(pkg).resource_tasks"
            :key="task.id || `${pkg.id}-resource-${idx}`"
            class="task-edit-row"
          >
            <select
              class="input"
              :value="task.resource_id ?? ''"
              @change="applyResourceSelection(pkg.id, idx, ($event.target as HTMLSelectElement).value)"
            >
              <option value="">选择已启用资源</option>
              <option v-for="resource in enabledResourceOptions" :key="resource.resource_id" :value="resource.resource_id">
                {{ resource.title || resource.resource_path }} · {{ resource.node_name || resource.node_id }}
              </option>
            </select>
            <input v-model="task.title" class="input" placeholder="资源标题" />
            <input v-model="task.resource_path" class="input" placeholder="资源链接或路径" />
            <input v-model="task.node_id" class="input" placeholder="知识点ID" />
            <label class="task-check"><input v-model="task.required" type="checkbox" /> 必做</label>
            <button class="ghost-btn" type="button" @click="removeResourceTask(pkg.id, idx)">删除</button>
          </div>
          <div v-if="!getDraft(pkg).resource_tasks.length" class="state-card compact-state">暂无结构化资源任务</div>
        </div>

        <div class="task-edit-section">
          <div class="section-head compact">
            <strong>作业任务引用</strong>
            <button class="ghost-btn" type="button" @click="addAssignmentTask(pkg.id)">添加作业</button>
          </div>
          <div
            v-for="(task, idx) in getDraft(pkg).assignment_tasks"
            :key="task.id || `${pkg.id}-assignment-${idx}`"
            class="task-edit-row"
          >
            <select
              class="input"
              :value="task.assignment_id"
              @change="applyAssignmentSelection(pkg.id, idx, ($event.target as HTMLSelectElement).value)"
            >
              <option value="">选择已发布作业</option>
              <option v-for="assignment in publishedAssignmentOptions" :key="assignment.id" :value="assignment.id">
                {{ assignment.title }} · {{ assignment.node_name || assignment.node_id }}
              </option>
            </select>
            <input v-model="task.title" class="input" placeholder="作业标题" />
            <input v-model="task.course_id" class="input" placeholder="课程ID" />
            <input v-model="task.node_id" class="input" placeholder="知识点ID" />
            <label class="task-check"><input v-model="task.required" type="checkbox" /> 必做</label>
            <button class="ghost-btn" type="button" @click="removeAssignmentTask(pkg.id, idx)">删除</button>
          </div>
          <div v-if="!getDraft(pkg).assignment_tasks.length" class="state-card compact-state">暂无作业任务引用</div>
        </div>

        <div class="task-edit-section">
          <div class="section-head compact">
            <strong>测验任务引用</strong>
            <button class="ghost-btn" type="button" @click="addQuizTask(pkg.id)">添加测验</button>
          </div>
          <div
            v-for="(task, idx) in getDraft(pkg).quiz_tasks"
            :key="task.id || `${pkg.id}-quiz-${idx}`"
            class="task-edit-row simple-task-row"
          >
            <select
              class="input"
              :value="task.quiz_id"
              @change="applyQuizSelection(pkg.id, idx, ($event.target as HTMLSelectElement).value)"
            >
              <option value="">选择已发布测验</option>
              <option v-for="quiz in publishedQuizOptions" :key="quiz.quiz_id" :value="quiz.quiz_id">
                {{ quiz.title }} · {{ quiz.node_id || quiz.course_id }}
              </option>
            </select>
            <input v-model="task.quiz_id" class="input" placeholder="已发布测验ID" />
            <input v-model="task.title" class="input" placeholder="测验标题" />
            <input v-model="task.course_id" class="input" placeholder="课程ID" />
            <input v-model="task.node_id" class="input" placeholder="知识点ID" />
            <label class="task-check"><input v-model="task.required" type="checkbox" /> 必做</label>
            <button class="ghost-btn" type="button" @click="removeQuizTask(pkg.id, idx)">删除</button>
          </div>
          <div v-if="!getDraft(pkg).quiz_tasks.length" class="state-card compact-state">暂无测验任务引用</div>
        </div>

        <div class="task-edit-section">
          <div class="section-head compact">
            <strong>代码练习引用</strong>
            <button class="ghost-btn" type="button" @click="addCodeTask(pkg.id)">添加代码练习</button>
          </div>
          <div
            v-for="(task, idx) in getDraft(pkg).code_tasks"
            :key="task.id || `${pkg.id}-code-${idx}`"
            class="task-edit-row simple-task-row"
          >
            <select
              class="input"
              :value="task.task_id"
              @change="applyCodeTaskSelection(pkg.id, idx, ($event.target as HTMLSelectElement).value)"
            >
              <option value="">选择已发布代码练习</option>
              <option v-for="codeTask in publishedCodeTaskOptions" :key="codeTask.task_id" :value="codeTask.task_id">
                {{ codeTask.title }} · {{ codeTask.node_name || codeTask.node_id }}
              </option>
            </select>
            <input v-model="task.task_id" class="input" placeholder="已发布代码任务ID" />
            <input v-model="task.title" class="input" placeholder="代码练习标题" />
            <input v-model="task.course_id" class="input" placeholder="课程ID" />
            <input v-model="task.node_id" class="input" placeholder="知识点ID" />
            <label class="task-check"><input v-model="task.required" type="checkbox" /> 必做</label>
            <button class="ghost-btn" type="button" @click="removeCodeTask(pkg.id, idx)">删除</button>
          </div>
          <div v-if="!getDraft(pkg).code_tasks.length" class="state-card compact-state">暂无代码练习引用</div>
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
            <input v-model="q.correct_answer" class="input" placeholder="填空写标准答案；选择题写 A 或 A,C；编程题写核心预期" />
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
              <th>完成度（题目）</th>
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

    <section class="card-panel teacher-intervention-evidence-panel">
      <div class="section-head">
        <h3>诊断证据时间线</h3>
        <span class="muted">资源学习、作业与测验回流</span>
      </div>
      <div v-if="!diagnosis.length" class="state-card">暂无诊断证据，请先识别薄弱点。</div>
      <div v-for="item in diagnosis" :key="`${item.student_username}-evidence`" class="teacher-intervention-evidence-card">
        <div class="section-head compact">
          <div>
            <strong>{{ item.student_username }}</strong>
            <span class="muted">
              证据等级 {{ item.evidence_level || "-" }} · 置信度 {{ formatPercentValue(item.confidence) }}
            </span>
          </div>
          <span class="muted">最近 {{ item.evidence_timeline?.length || 0 }} 条</span>
        </div>
        <div class="teacher-intervention-evidence-list">
          <div
            v-for="event in topEvidence(item)"
            :key="`${item.student_username}-${event.type}-${event.node_id || ''}-${event.occurred_at || ''}-${event.resource_path || event.title || ''}`"
            class="teacher-intervention-evidence-row"
          >
            <span class="teacher-intervention-evidence-type">{{ evidenceTypeLabel(event.type) }}</span>
            <span class="teacher-intervention-evidence-node">{{ event.node_id || "未绑定知识点" }}</span>
            <span class="teacher-intervention-evidence-summary">{{ evidenceSummary(event) }}</span>
            <span class="teacher-intervention-evidence-time">{{ formatTime(event.occurred_at || undefined) }}</span>
          </div>
          <div v-if="!topEvidence(item).length" class="teacher-intervention-evidence-empty">暂无可展示证据</div>
        </div>
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
  interventionTaskReferenceOptions,
  interventionUpdateTeacherPackage,
} from "../../api/intervention";
import type {
  InterventionDiagnosis,
  InterventionPackage,
  InterventionQuestion,
  InterventionTaskReferenceOptions,
  TeacherInterventionStudentOverview,
} from "../../types/intervention";
import type { DiagnosisEvidenceTimelineItem } from "../../types/student";
import { homeworkListAssignments } from "../../api/homework";
import { fetchCourseDigitalTwinResources } from "../../api/teacher";
import type { HomeworkAssignment } from "../../types/homework";
import type { CourseDigitalTwinResource } from "../../types/teacher";

const loading = ref(false);
const diagnosing = ref(false);
const error = ref("");
const generatingStudent = ref("");
const savingId = ref("");
const pushingId = ref("");

const students = ref<TeacherInterventionStudentOverview[]>([]);
const diagnosis = ref<InterventionDiagnosis[]>([]);
const packages = ref<InterventionPackage[]>([]);
const courseResources = ref<CourseDigitalTwinResource[]>([]);
const homeworkAssignments = ref<HomeworkAssignment[]>([]);
const taskReferenceOptions = ref<InterventionTaskReferenceOptions | null>(null);
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
      resource_tasks: Array<{
        id?: string;
        resource_id?: number | null;
        title: string;
        resource_path: string;
        resource_type: string;
        node_id: string;
        required: boolean;
      }>;
      assignment_tasks: Array<{
        id?: string;
        assignment_id: string;
        title: string;
        course_id: string;
        node_id: string;
        required: boolean;
      }>;
      quiz_tasks: Array<{
        id?: string;
        quiz_id: string;
        title: string;
        course_id: string;
        node_id: string;
        required: boolean;
      }>;
      code_tasks: Array<{
        id?: string;
        task_id: string;
        title: string;
        course_id: string;
        node_id: string;
        required: boolean;
      }>;
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

const enabledResourceOptions = computed(() =>
  taskReferenceOptions.value?.resources?.length
    ? taskReferenceOptions.value.resources.map((item) => ({
        resource_id: item.resource_id,
        course_id: item.course_id,
        node_id: item.node_id,
        node_name: item.node_name || "",
        title: item.title || item.resource_path,
        resource_path: item.resource_path,
        resource_type: item.resource_type || "resource",
        resource_source: item.resource_type || "resource",
        quality_status: "",
        review_status: "enabled",
        is_enabled: true,
        is_deleted: false,
      }))
    : courseResources.value.filter((item) => item.is_enabled && !item.is_deleted && item.review_status !== "rejected"),
);

const publishedAssignmentOptions = computed(() =>
  taskReferenceOptions.value?.assignments?.length
    ? taskReferenceOptions.value.assignments.map((item) => ({
        id: item.assignment_id,
        title: item.title,
        description: "",
        assignment_type: item.assignment_type as HomeworkAssignment["assignment_type"],
        class_name: "",
        course_id: item.course_id,
        node_id: item.node_id,
        node_name: item.node_name || "",
        node_path: [],
        chapter_context: "",
        allow_late: true,
        total_score: 100,
        rubric: "",
        questions: [],
        created_by: "",
        created_at: "",
        status: "published" as const,
      }))
    : homeworkAssignments.value.filter((item) => item.status === "published"),
);

const publishedQuizOptions = computed(() => taskReferenceOptions.value?.quizzes ?? []);

const publishedCodeTaskOptions = computed(() => taskReferenceOptions.value?.code_tasks ?? []);

function formatTime(value?: string) {
  if (!value) return "-";
  return new Date(value).toLocaleString();
}

function formatPercentValue(value?: number | null) {
  if (value === undefined || value === null) return "-";
  return `${Number(value || 0).toFixed(1)}%`;
}

function topEvidence(item: InterventionDiagnosis) {
  return (item.evidence_timeline || []).slice(0, 5);
}

function evidenceTypeLabel(type?: string) {
  const mapping: Record<string, string> = {
    quiz: "测验",
    homework: "作业",
    resource_learning: "资源学习",
  };
  return mapping[type || ""] || "学习证据";
}

function evidenceSummary(item: DiagnosisEvidenceTimelineItem) {
  if (item.type === "quiz") {
    return `得分 ${Number(item.score ?? 0).toFixed(1)} / ${Number(item.total ?? 0).toFixed(1)}`;
  }
  if (item.type === "homework") {
    return `${item.title || "作业"}：${item.status || "已提交"}`;
  }
  if (item.type === "resource_learning") {
    const progress = Number(item.progress_percent ?? 0).toFixed(0);
    const duration = Math.round(Number(item.duration_seconds ?? 0) / 60);
    return `${item.event_type || "学习"}，进度 ${progress}%${duration > 0 ? `，约 ${duration} 分钟` : ""}`;
  }
  return "学习证据已记录";
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
        resource_tasks: (pkg.resource_tasks || []).map((item) => ({
          id: item.id,
          resource_id: item.resource_id ?? null,
          title: item.title || "",
          resource_path: item.resource_path || "",
          resource_type: item.resource_type || "",
          node_id: item.node_id || "",
          required: item.required !== false,
        })),
        assignment_tasks: (pkg.assignment_tasks || []).map((item) => ({
          id: item.id,
          assignment_id: item.assignment_id || "",
          title: item.title || "",
          course_id: item.course_id || "",
          node_id: item.node_id || "",
          required: item.required !== false,
        })),
        quiz_tasks: (pkg.quiz_tasks || []).map((item) => ({
          id: item.id,
          quiz_id: item.quiz_id || "",
          title: item.title || "",
          course_id: item.course_id || "",
          node_id: item.node_id || "",
          required: item.required !== false,
        })),
        code_tasks: (pkg.code_tasks || []).map((item) => ({
          id: item.id,
          task_id: item.task_id || "",
          title: item.title || "",
          course_id: item.course_id || "",
          node_id: item.node_id || "",
          required: item.required !== false,
        })),
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
    const [overviewRes, diagnoseRes, packageRes, progressRes, referenceRes, resourceRes, homeworkRes] = await Promise.all([
      interventionTeacherStudentsOverview(),
      interventionTeacherDiagnose(),
      interventionListTeacherPackages(),
      interventionTeacherProgress(),
      interventionTaskReferenceOptions("course_big_data"),
      fetchCourseDigitalTwinResources("course_big_data"),
      homeworkListAssignments(true),
    ]);
    students.value = overviewRes.data.students || [];
    diagnosis.value = diagnoseRes.data.diagnosis || [];
    packages.value = packageRes.packages || [];
    progressRows.value = progressRes.rows || [];
    taskReferenceOptions.value = referenceRes.options || null;
    courseResources.value = resourceRes.resources || [];
    homeworkAssignments.value = homeworkRes.assignments || [];
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
      resource_tasks: draft.resource_tasks
        .filter((item) => item.title.trim() || item.resource_path.trim())
        .map((item) => ({
          ...item,
          title: item.title.trim() || item.resource_path.trim(),
          resource_path: item.resource_path.trim(),
          resource_type: item.resource_type.trim(),
          node_id: item.node_id.trim(),
        })),
      assignment_tasks: draft.assignment_tasks
        .filter((item) => item.assignment_id.trim() || item.title.trim())
        .map((item) => ({
          ...item,
          assignment_id: item.assignment_id.trim(),
          title: item.title.trim() || item.assignment_id.trim(),
          course_id: item.course_id.trim(),
          node_id: item.node_id.trim(),
        })),
      quiz_tasks: draft.quiz_tasks
        .filter((item) => item.quiz_id.trim() || item.title.trim())
        .map((item) => ({
          ...item,
          quiz_id: item.quiz_id.trim(),
          title: item.title.trim() || item.quiz_id.trim(),
          course_id: item.course_id.trim(),
          node_id: item.node_id.trim(),
        })),
      code_tasks: draft.code_tasks
        .filter((item) => item.task_id.trim() || item.title.trim())
        .map((item) => ({
          ...item,
          task_id: item.task_id.trim(),
          title: item.title.trim() || item.task_id.trim(),
          course_id: item.course_id.trim(),
          node_id: item.node_id.trim(),
        })),
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

function addResourceTask(packageId: string) {
  const draft = draftMap.value[packageId];
  if (!draft) return;
  draft.resource_tasks.push({
    id: `resource-${Date.now()}`,
    resource_id: null,
    title: "",
    resource_path: "",
    resource_type: "video",
    node_id: "",
    required: true,
  });
}

function removeResourceTask(packageId: string, index: number) {
  draftMap.value[packageId]?.resource_tasks.splice(index, 1);
}

function applyResourceSelection(packageId: string, index: number, value: string) {
  const draft = draftMap.value[packageId];
  const task = draft?.resource_tasks[index];
  if (!task) return;
  const resourceId = Number(value || 0);
  const resource = enabledResourceOptions.value.find((item) => item.resource_id === resourceId);
  if (!resource) {
    task.resource_id = null;
    return;
  }
  task.resource_id = resource.resource_id;
  task.title = resource.title || resource.resource_path;
  task.resource_path = resource.resource_path;
  task.resource_type = resource.resource_type || resource.resource_source || "resource";
  task.node_id = resource.node_id || "";
}

function addAssignmentTask(packageId: string) {
  const draft = draftMap.value[packageId];
  if (!draft) return;
  draft.assignment_tasks.push({
    id: `assignment-${Date.now()}`,
    assignment_id: "",
    title: "",
    course_id: "course_big_data",
    node_id: "",
    required: true,
  });
}

function removeAssignmentTask(packageId: string, index: number) {
  draftMap.value[packageId]?.assignment_tasks.splice(index, 1);
}

function applyAssignmentSelection(packageId: string, index: number, assignmentId: string) {
  const draft = draftMap.value[packageId];
  const task = draft?.assignment_tasks[index];
  if (!task) return;
  const assignment = publishedAssignmentOptions.value.find((item) => item.id === assignmentId);
  if (!assignment) {
    task.assignment_id = assignmentId;
    return;
  }
  task.assignment_id = assignment.id;
  task.title = assignment.title;
  task.course_id = assignment.course_id;
  task.node_id = assignment.node_id;
}

function addQuizTask(packageId: string) {
  const draft = draftMap.value[packageId];
  if (!draft) return;
  draft.quiz_tasks.push({
    id: `quiz-${Date.now()}`,
    quiz_id: "",
    title: "",
    course_id: "course_big_data",
    node_id: "",
    required: true,
  });
}

function removeQuizTask(packageId: string, index: number) {
  draftMap.value[packageId]?.quiz_tasks.splice(index, 1);
}

function applyQuizSelection(packageId: string, index: number, quizId: string) {
  const draft = draftMap.value[packageId];
  const task = draft?.quiz_tasks[index];
  if (!task) return;
  const quiz = publishedQuizOptions.value.find((item) => item.quiz_id === quizId);
  if (!quiz) {
    task.quiz_id = quizId;
    return;
  }
  task.quiz_id = quiz.quiz_id;
  task.title = quiz.title;
  task.course_id = quiz.course_id;
  task.node_id = quiz.node_id || "";
}

function addCodeTask(packageId: string) {
  const draft = draftMap.value[packageId];
  if (!draft) return;
  draft.code_tasks.push({
    id: `code-${Date.now()}`,
    task_id: "",
    title: "",
    course_id: "course_big_data",
    node_id: "",
    required: true,
  });
}

function removeCodeTask(packageId: string, index: number) {
  draftMap.value[packageId]?.code_tasks.splice(index, 1);
}

function applyCodeTaskSelection(packageId: string, index: number, taskId: string) {
  const draft = draftMap.value[packageId];
  const task = draft?.code_tasks[index];
  if (!task) return;
  const codeTask = publishedCodeTaskOptions.value.find((item) => item.task_id === taskId);
  if (!codeTask) {
    task.task_id = taskId;
    return;
  }
  task.task_id = codeTask.task_id;
  task.title = codeTask.title;
  task.course_id = codeTask.course_id;
  task.node_id = codeTask.node_id || "";
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
  border: none; box-shadow: 0 4px 12px rgba(0,0,0,0.03); padding: 16px;
  border-radius: 10px;
  padding: 10px;
  margin-top: 10px;
  background: #fff;
}

.task-edit-section {
  display: grid;
  gap: 8px;
  margin-top: 12px;
}

.task-edit-row {
  display: grid;
  grid-template-columns: minmax(160px, 1.1fr) minmax(140px, 1fr) minmax(180px, 1.4fr) minmax(120px, 0.8fr) auto auto;
  gap: 8px;
  align-items: center;
  padding: 10px;
  border-radius: 10px;
  background: #fff;
  border: 1px solid #e2e8f0;
}

.task-edit-section + .task-edit-section .task-edit-row {
  grid-template-columns: minmax(170px, 1.2fr) minmax(150px, 1fr) minmax(120px, 0.8fr) minmax(120px, 0.8fr) auto auto;
}

.task-check {
  display: inline-flex;
  gap: 6px;
  align-items: center;
  white-space: nowrap;
  color: #475569;
  font-size: 13px;
}

.compact-state {
  padding: 10px;
}

.teacher-intervention-evidence-card {
  border: 1px solid #e2e8f0;
  border-radius: 12px;
  padding: 12px;
  margin-top: 10px;
  background: #f8fafc;
}

.teacher-intervention-evidence-list {
  display: grid;
  gap: 8px;
}

.teacher-intervention-evidence-row {
  display: grid;
  grid-template-columns: 88px minmax(120px, 1fr) minmax(160px, 2fr) 150px;
  gap: 10px;
  align-items: center;
  padding: 8px 10px;
  border-radius: 12px;
  background: #fff;
  border: none; box-shadow: 0 4px 12px rgba(0,0,0,0.03); padding: 16px;
  font-size: 13px;
}

.teacher-intervention-evidence-type {
  color: #1d4ed8;
  font-weight: 700;
}

.teacher-intervention-evidence-node,
.teacher-intervention-evidence-time,
.teacher-intervention-evidence-empty {
  color: #64748b;
}

.teacher-intervention-evidence-summary {
  color: #0f172a;
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
  border-radius: 12px;
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

  .task-edit-row,
  .task-edit-section + .task-edit-section .task-edit-row {
    grid-template-columns: 1fr;
  }
}
</style>

