<template>
  <div class="homework-shell">
    <section class="card-panel homework-hero">
      <div>
        <p class="eyebrow">作业中心</p>
        <h1>作业列表</h1>
        <p class="hero-desc">AI 出题已提升为主入口，支持主观题/客观题/选择题/代码题并可快速弹窗创建。</p>
      </div>
      <div class="actions-row">
        <button class="ghost-btn" type="button" @click="router.push({ name: 'teacher-homework-new' })">新建作业</button>
        <button class="ghost-btn emphasis" type="button" @click="openQuickAIModal">AI一键出题</button>
      </div>
    </section>

    <section class="card-panel ai-promo">
      <div>
        <h3>AI 智能出题</h3>
        <p class="muted">输入主题即可生成完整作业草稿，支持四种题型与可编辑题目结构。</p>
      </div>
      <div class="actions-row">
        <button class="ghost-btn emphasis" type="button" @click="openQuickAIModal">立即生成草稿</button>
      </div>
    </section>

    <section class="card-panel">
      <div class="section-head">
        <h3>我的作业</h3>
        <button class="ghost-btn" type="button" @click="loadAssignments">刷新</button>
      </div>

      <div class="industry-table-wrap">
        <table class="industry-table">
          <thead>
            <tr>
              <th>标题</th>
              <th>类型</th>
              <th>状态</th>
              <th>课程</th>
              <th>章节</th>
              <th>班级</th>
              <th>题目数</th>
              <th>截止时间</th>
              <th>操作</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="item in assignments" :key="item.id">
              <td>{{ item.title }}</td>
              <td>{{ typeLabel(item.assignment_type) }}</td>
              <td>{{ statusLabel(item.status) }}</td>
              <td>{{ item.course_id || "-" }}</td>
              <td>{{ item.node_name || "-" }}</td>
              <td>{{ item.class_name || "-" }}</td>
              <td>{{ item.questions?.length ?? 0 }}</td>
              <td>{{ formatTime(item.due_at) }}</td>
              <td class="actions-cell">
                <button class="ghost-btn small" type="button" @click="openPreview(item)">查看</button>
                <button class="ghost-btn small" type="button" @click="router.push({ name: 'teacher-homework-edit', params: { assignmentId: item.id } })">
                  编辑
                </button>
                <button class="ghost-btn small" type="button" @click="openSubmissionsDrawer(item)">
                  批改
                </button>
                <button v-if="item.status === 'draft'" class="ghost-btn small" type="button" @click="openStatusConfirm(item, 'publish')">发布</button>
                <button v-if="item.status === 'published'" class="ghost-btn small" type="button" @click="openStatusConfirm(item, 'close')">关闭</button>
                <button v-if="item.status === 'closed'" class="ghost-btn small" type="button" @click="openStatusConfirm(item, 'reopen')">重开</button>
              </td>
            </tr>
            <tr v-if="!assignments.length">
              <td colspan="9">暂无作业</td>
            </tr>
          </tbody>
        </table>
      </div>
    </section>

    <section v-if="notice" class="card-panel state-card">{{ notice }}</section>
    <section v-if="error" class="card-panel state-card error-state">{{ error }}</section>

    <div v-if="previewVisible && previewAssignment" class="modal-mask" @click.self="previewVisible = false">
      <div class="modal-card">
        <div class="section-head">
          <h3>作业预览</h3>
          <button class="ghost-btn" type="button" @click="previewVisible = false">关闭</button>
        </div>
        <p><strong>标题：</strong>{{ previewAssignment.title }}</p>
        <p><strong>描述：</strong>{{ previewAssignment.description || '无' }}</p>
        <p><strong>状态：</strong>{{ statusLabel(previewAssignment.status) }}</p>
        <p><strong>课程：</strong>{{ previewAssignment.course_id || '-' }}</p>
        <p><strong>章节：</strong>{{ previewAssignment.node_name || '-' }}</p>
        <div v-for="(q, idx) in previewAssignment.questions" :key="idx" class="question-card">
          <p><strong>{{ idx + 1 }}. {{ q.title }}</strong></p>
          <p class="multiline">{{ q.prompt }}</p>
        </div>
      </div>
    </div>

    <div v-if="statusDialog.visible" class="modal-mask" @click.self="statusDialog.visible = false">
      <div class="modal-card compact">
        <h3>确认操作</h3>
        <p>{{ statusDialog.message }}</p>
        <div class="actions-row">
          <button class="ghost-btn" type="button" @click="statusDialog.visible = false">取消</button>
          <button class="ghost-btn" type="button" @click="confirmStatusChange">确认</button>
        </div>
      </div>
    </div>

    <div v-if="quickAIModal.visible" class="modal-mask" @click.self="quickAIModal.visible = false">
      <div class="modal-card">
        <div class="section-head">
          <h3>AI 一键出题</h3>
          <button class="ghost-btn" type="button" @click="quickAIModal.visible = false">关闭</button>
        </div>

        <div class="form-grid">
          <label>
            主题
            <input v-model="quickAIModal.topic" class="input" type="text" placeholder="例如：哈希表冲突处理" />
          </label>
          <label>
            题型
            <select v-model="quickAIModal.assignment_type" class="input">
              <option value="subjective">主观题</option>
              <option value="objective">客观题（判断）</option>
              <option value="choice">选择题（单/多选）</option>
              <option value="code">代码题</option>
            </select>
          </label>
          <label v-if="quickAIModal.assignment_type === 'objective' || quickAIModal.assignment_type === 'choice'">
            判题结果展示
            <select v-model="quickAIModal.objective_result_mode" class="input">
              <option value="immediate">学生提交后自动判题并显示结果（默认）</option>
              <option value="manual_review">教师批改后再显示结果</option>
            </select>
          </label>
          <label>
            难度
            <select v-model="quickAIModal.difficulty" class="input">
              <option value="简单">简单</option>
              <option value="中等">中等</option>
              <option value="困难">困难</option>
            </select>
          </label>
          <label>
            班级
            <select v-model="quickAIModal.class_name" class="input">
              <option value="">未指定班级</option>
              <option v-for="className in classOptions" :key="className" :value="className">{{ className }}</option>
            </select>
          </label>
          <label>
            课程ID
            <select v-model.trim="quickAIModal.course_id" class="input" @change="loadQuickCourseNodes">
              <option v-for="courseId in courseOptions" :key="courseId" :value="courseId">{{ courseId }}</option>
            </select>
          </label>
          <label>
            关联章节
            <select v-model="quickAIModal.node_id" class="input" @change="onQuickNodeChange">
              <option value="">不关联章节</option>
              <option v-for="node in quickCourseNodes" :key="node.node_id" :value="node.node_id">
                {{ node.node_path.join(" > ") }}
              </option>
            </select>
          </label>
        </div>
        <label class="full-width">
          章节上下文（用于AI出题）
          <textarea
            v-model="quickAIModal.chapter_context"
            class="input input-textarea"
            rows="3"
            placeholder="例如：本章重点、能力目标、常见误区"
          />
        </label>

        <div class="actions-row">
          <button class="ghost-btn" type="button" :disabled="quickAIModal.loading" @click="generateQuickDraft">
            {{ quickAIModal.loading ? "生成中..." : "生成草稿" }}
          </button>
          <button class="ghost-btn" type="button" :disabled="!quickAIModal.draft || quickAIModal.creating" @click="createQuickAssignment(false)">
            {{ quickAIModal.creating ? "创建中..." : "创建为草稿" }}
          </button>
          <button class="ghost-btn" type="button" :disabled="!quickAIModal.draft || quickAIModal.creating" @click="createQuickAssignment(true)">
            {{ quickAIModal.creating ? "发布中..." : "创建并发布" }}
          </button>
        </div>

        <div v-if="quickAIModal.draft" class="question-card">
          <p><strong>{{ quickAIModal.draft.title }}</strong></p>
          <p>{{ quickAIModal.draft.description || '无简介' }}</p>
          <div v-for="(q, idx) in quickAIModal.draft.questions" :key="idx" class="question-card nested">
            <p><strong>{{ idx + 1 }}. {{ q.title }}</strong></p>
            <p class="multiline">{{ q.prompt }}</p>
          </div>
        </div>
      </div>
    </div>

    <div v-if="submissionsDrawer.visible" class="drawer-mask" @click.self="submissionsDrawer.visible = false">
      <aside class="drawer-panel">
        <div class="section-head">
          <h3>提交列表</h3>
          <button class="ghost-btn" type="button" @click="submissionsDrawer.visible = false">关闭</button>
        </div>
        <p v-if="submissionsDrawer.assignment">
          <strong>{{ submissionsDrawer.assignment.title }}</strong>
          <span class="muted">（{{ typeLabel(submissionsDrawer.assignment.assignment_type) }}）</span>
        </p>

        <section v-if="submissionsDrawer.loading" class="state-card">加载中...</section>
        <div v-else class="industry-table-wrap">
          <table class="industry-table">
            <thead>
              <tr>
                <th>学生</th>
                <th>提交时间</th>
                <th>状态</th>
                <th>得分</th>
                <th>操作</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="s in submissionsDrawer.submissions" :key="s.id">
                <td>{{ s.student_username }}</td>
                <td>{{ formatTime(s.submitted_at) }}</td>
                <td>{{ s.status }}</td>
                <td>{{ s.teacher_score ?? s.ai_score ?? '-' }}</td>
                <td>
                  <button class="ghost-btn small" type="button" @click="openGradeDrawer(s.id)">查看判题</button>
                </td>
              </tr>
              <tr v-if="!submissionsDrawer.submissions.length">
                <td colspan="5">暂无提交</td>
              </tr>
            </tbody>
          </table>
        </div>
      </aside>
    </div>

    <div v-if="gradeDrawer.visible" class="drawer-mask" @click.self="gradeDrawer.visible = false">
      <aside class="drawer-panel grade-drawer">
        <div class="section-head">
          <h3>判题详情</h3>
          <button class="ghost-btn" type="button" @click="gradeDrawer.visible = false">关闭</button>
        </div>

        <section v-if="gradeDrawer.loading" class="state-card">加载中...</section>
        <template v-else-if="gradeDrawer.submission && gradeDrawer.assignment">
          <div class="summary-grid">
            <div><strong>学生：</strong>{{ gradeDrawer.submission.student_username }}</div>
            <div><strong>题型：</strong>{{ typeLabel(gradeDrawer.assignment.assignment_type) }}</div>
            <div><strong>提交时间：</strong>{{ formatTime(gradeDrawer.submission.submitted_at) }}</div>
            <div><strong>状态：</strong>{{ gradeDrawer.submission.status }}</div>
          </div>

          <div class="question-card" v-for="(q, idx) in gradeDrawer.assignment.questions" :key="`grade-${idx}`">
            <p><strong>题目 {{ idx + 1 }}：{{ q.title }}</strong></p>
            <p class="multiline">{{ q.prompt }}</p>
            <label class="full-width">学生作答</label>
            <template v-if="gradeDrawer.assignment.assignment_type === 'code'">
              <div class="answer-meta">
                <span class="meta-chip">语言：{{ answerLanguageLabel(idx) }}</span>
              </div>
              <MonacoEditor
                :value="getAnswerByIndex(idx)"
                :language="editorLanguageByIndex(idx)"
                theme="vs-dark"
                :options="codePreviewOptions"
                :height="'240px'"
                class="code-preview"
              />
            </template>
            <div v-else class="answer-box multiline">{{ getAnswerByIndex(idx) || '（该题未作答）' }}</div>
          </div>

          <section v-if="gradeDrawer.assignment.assignment_type === 'code'" class="question-card">
            <div class="section-head compact">
              <h3>代码题自动判题</h3>
              <button class="ghost-btn" type="button" :disabled="gradeDrawer.gradingAI" @click="runAiGrade">
                {{ gradeDrawer.gradingAI ? '审查中...' : 'AI 审查代码' }}
              </button>
            </div>
            <p><strong>系统评分：</strong>{{ gradeDrawer.submission.teacher_score ?? gradeDrawer.submission.ai_score ?? '-' }}</p>
            <p><strong>判题摘要：</strong>{{ gradeDrawer.submission.ai_feedback || gradeDrawer.submission.teacher_comment || '-' }}</p>
            <p v-if="currentJudgeReport"><strong>通过率：</strong>{{ judgePassText(currentJudgeReport) }}</p>

            <div class="industry-table-wrap" v-if="currentJudgeReport && currentJudgeReport.details.length">
              <table class="industry-table">
                <thead>
                  <tr>
                    <th>#</th>
                    <th>结果</th>
                    <th>输入</th>
                    <th>期望</th>
                    <th>实际</th>
                    <th>错误信息</th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="detail in currentJudgeReport.details" :key="detail.case">
                    <td>{{ detail.case }}</td>
                    <td>
                      <span :class="['verdict-chip', detail.ok ? 'ok' : 'fail']">{{ detail.ok ? 'Accepted' : 'Wrong Answer' }}</span>
                    </td>
                    <td><pre class="oj-pre">{{ detail.input }}</pre></td>
                    <td><pre class="oj-pre">{{ detail.expected }}</pre></td>
                    <td><pre class="oj-pre">{{ detail.actual }}</pre></td>
                    <td><pre class="oj-pre">{{ detail.stderr || '-' }}</pre></td>
                  </tr>
                </tbody>
              </table>
            </div>
          </section>

          <template v-else>
            <section class="question-card">
              <div class="section-head compact">
                <h3>AI 辅助批改</h3>
                <button class="ghost-btn" type="button" :disabled="gradeDrawer.gradingAI" @click="runAiGrade">
                  {{ gradeDrawer.gradingAI ? '生成中...' : '生成 AI 建议' }}
                </button>
              </div>
              <p><strong>AI建议分：</strong>{{ gradeDrawer.submission.ai_score ?? '-' }}</p>
              <p><strong>AI评语：</strong></p>
              <div class="answer-box multiline">{{ gradeDrawer.submission.ai_feedback || '暂无' }}</div>
            </section>

            <section class="question-card">
              <div class="section-head compact">
                <h3>教师终审</h3>
                <button class="ghost-btn" type="button" @click="useAISuggestion">采用 AI 建议</button>
              </div>
              <label class="full-width">
                终审分数
                <input v-model.number="gradeDrawer.score" class="input" type="number" min="0" step="0.1" />
              </label>
              <label class="full-width">
                终审评语
                <textarea v-model="gradeDrawer.comment" class="input input-textarea" rows="5" />
              </label>
              <div class="actions-row">
                <button class="ghost-btn" type="button" :disabled="gradeDrawer.saving" @click="saveFinalGrade">
                  {{ gradeDrawer.saving ? '保存中...' : '保存终审结果' }}
                </button>
              </div>
            </section>
          </template>
        </template>
      </aside>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from "vue";
import MonacoEditor from "@guolao/vue-monaco-editor";
import { useRouter } from "vue-router";
import {
  homeworkAiGrade,
  homeworkCloseStatus,
  homeworkGenerateDraft,
  homeworkGetSubmission,
  homeworkListAssignments,
  homeworkListCourseNodes,
  homeworkListSubmissions,
  homeworkFinalGrade,
  homeworkPublishAssignment,
  homeworkPublishStatus,
  homeworkReopenStatus,
} from "../../api/homework";
import type { HomeworkAssignment, HomeworkCourseNode, HomeworkQuestion, HomeworkSubmission } from "../../types/homework";

const router = useRouter();
const assignments = ref<HomeworkAssignment[]>([]);
const quickCourseNodes = ref<HomeworkCourseNode[]>([]);
const notice = ref("");
const error = ref("");

const previewVisible = ref(false);
const previewAssignment = ref<HomeworkAssignment | null>(null);

const submissionsDrawer = reactive({
  visible: false,
  loading: false,
  assignment: null as HomeworkAssignment | null,
  submissions: [] as HomeworkSubmission[],
});

type JudgeCaseDetail = {
  case: number;
  ok: boolean;
  input: string;
  expected: string;
  actual: string;
  stderr?: string;
};

type JudgeReport = {
  passed: number;
  total: number;
  pass_rate?: number;
  score_rate?: number;
  details: JudgeCaseDetail[];
};

const codePreviewOptions = {
  readOnly: true,
  minimap: { enabled: false },
  fontSize: 13,
  lineNumbers: "on" as const,
  automaticLayout: true,
  scrollBeyondLastLine: false,
};

const gradeDrawer = reactive({
  visible: false,
  loading: false,
  gradingAI: false,
  saving: false,
  submission: null as HomeworkSubmission | null,
  assignment: null as HomeworkAssignment | null,
  score: 0,
  comment: "",
});

const currentJudgeReport = computed(() => parseJudgeReport(gradeDrawer.submission?.ai_rationale));
const courseOptions = computed(() => {
  const values = assignments.value.map((item) => String(item.course_id || "").trim()).filter(Boolean);
  const unique = Array.from(new Set(values));
  return unique.length ? unique : ["course_big_data"];
});
const classOptions = computed(() => {
  const values = assignments.value.map((item) => String(item.class_name || "").trim()).filter(Boolean);
  return Array.from(new Set(values));
});

const quickAIModal = reactive({
  visible: false,
  loading: false,
  creating: false,
  topic: "",
  assignment_type: "subjective" as "subjective" | "objective" | "choice" | "code",
  objective_result_mode: "immediate" as "immediate" | "manual_review",
  difficulty: "中等",
  class_name: "",
  course_id: "course_big_data",
  node_id: "",
  node_name: "",
  node_path: [] as string[],
  chapter_context: "",
  draft: null as null | {
    title: string;
    description: string;
    assignment_type: "subjective" | "objective" | "choice" | "code";
    course_id: string;
    node_id: string;
    node_name: string;
    node_path: string[];
    chapter_context: string;
    objective_result_mode?: "immediate" | "manual_review";
    due_at?: string | null;
    allow_late: boolean;
    total_score: number;
    rubric: string;
    questions: HomeworkQuestion[];
  },
});

const statusDialog = reactive({
  visible: false,
  assignmentId: "",
  action: "publish" as "publish" | "close" | "reopen",
  message: "",
});

function formatTime(value?: string | null) {
  if (!value) return "-";
  return new Date(value).toLocaleString();
}

function statusLabel(value: string) {
  if (value === "published") return "已发布";
  if (value === "closed") return "已关闭";
  return "草稿";
}

function typeLabel(value: string) {
  if (value === "code") return "代码题";
  if (value === "objective") return "客观题（判断）";
  if (value === "choice") return "选择题";
  return "主观题";
}

function resetMessage() {
  notice.value = "";
  error.value = "";
}

function parseJudgeReport(raw?: string): JudgeReport | null {
  const text = String(raw || "").trim();
  if (!text.startsWith("{")) {
    return null;
  }
  try {
    const parsed = JSON.parse(text) as Record<string, unknown>;
    const detailsRaw = Array.isArray(parsed.details) ? parsed.details : [];
    const details = detailsRaw
      .filter((item): item is Record<string, unknown> => typeof item === "object" && item !== null)
      .map((item) => ({
        case: Number(item.case ?? 0),
        ok: Boolean(item.ok),
        input: String(item.input ?? ""),
        expected: String(item.expected ?? ""),
        actual: String(item.actual ?? ""),
        stderr: String(item.stderr ?? ""),
      }));
    return {
      passed: Number(parsed.passed ?? 0),
      total: Number(parsed.total ?? 0),
      pass_rate: Number(parsed.pass_rate ?? 0),
      score_rate: Number(parsed.score_rate ?? 0),
      details,
    };
  } catch {
    return null;
  }
}

function judgePassText(report: JudgeReport) {
  const ratio = report.total > 0
    ? report.passed / report.total
    : (typeof report.score_rate === "number" ? report.score_rate : (report.pass_rate || 0));
  return `${report.passed}/${report.total} (${Math.round(Math.max(0, ratio) * 100)}%)`;
}

function getAnswerByIndex(index: number) {
  if (!gradeDrawer.submission?.answers) return "";
  const found = gradeDrawer.submission.answers.find((item) => Number(item.question_index) === index);
  return found ? String(found.answer ?? "") : "";
}

function getAnswerLanguageByIndex(index: number) {
  if (!gradeDrawer.submission?.answers) return "python";
  const found = gradeDrawer.submission.answers.find((item) => Number(item.question_index) === index);
  const raw = String(found?.language || "").toLowerCase();
  if (raw === "java") return "java";
  if (raw === "cpp" || raw === "c++") return "cpp";
  return "python";
}

function editorLanguageByIndex(index: number) {
  const lang = getAnswerLanguageByIndex(index);
  if (lang === "java") return "java";
  if (lang === "cpp") return "cpp";
  return "python";
}

function answerLanguageLabel(index: number) {
  const lang = getAnswerLanguageByIndex(index);
  if (lang === "java") return "Java";
  if (lang === "cpp") return "C++";
  return "Python";
}

async function loadAssignments() {
  resetMessage();
  try {
    const res = await homeworkListAssignments(true);
    assignments.value = res.assignments;
  } catch (e) {
    error.value = e instanceof Error ? e.message : "加载作业失败";
  }
}

async function loadQuickCourseNodes() {
  try {
    const res = await homeworkListCourseNodes(quickAIModal.course_id || "course_big_data");
    quickCourseNodes.value = res.nodes || [];
  } catch {
    quickCourseNodes.value = [];
  }
}

function onQuickNodeChange() {
  const target = quickCourseNodes.value.find((item) => item.node_id === quickAIModal.node_id);
  if (!target) {
    quickAIModal.node_name = "";
    quickAIModal.node_path = [];
    return;
  }
  quickAIModal.node_name = target.node_name;
  quickAIModal.node_path = target.node_path;
  if (!quickAIModal.chapter_context.trim()) {
    quickAIModal.chapter_context = `章节路径：${target.node_path.join(" > ")}`;
  }
}

function openPreview(item: HomeworkAssignment) {
  previewAssignment.value = item;
  previewVisible.value = true;
}

async function openSubmissionsDrawer(item: HomeworkAssignment) {
  submissionsDrawer.visible = true;
  submissionsDrawer.assignment = item;
  submissionsDrawer.loading = true;
  try {
    const res = await homeworkListSubmissions(item.id);
    submissionsDrawer.submissions = res.submissions;
  } catch (e) {
    error.value = e instanceof Error ? e.message : "加载提交列表失败";
  } finally {
    submissionsDrawer.loading = false;
  }
}

async function openGradeDrawer(submissionId: string) {
  gradeDrawer.visible = true;
  gradeDrawer.loading = true;
  try {
    const res = await homeworkGetSubmission(submissionId);
    gradeDrawer.submission = res.submission;
    gradeDrawer.assignment = res.assignment;
    gradeDrawer.score = res.submission.teacher_score ?? res.submission.ai_score ?? 0;
    gradeDrawer.comment = res.submission.teacher_comment || res.submission.ai_feedback || "";
  } catch (e) {
    error.value = e instanceof Error ? e.message : "加载判题详情失败";
  } finally {
    gradeDrawer.loading = false;
  }
}

function useAISuggestion() {
  if (!gradeDrawer.submission) return;
  gradeDrawer.score = gradeDrawer.submission.ai_score ?? gradeDrawer.score;
  gradeDrawer.comment = gradeDrawer.submission.ai_feedback || gradeDrawer.comment;
}

async function runAiGrade() {
  if (!gradeDrawer.submission) return;
  gradeDrawer.gradingAI = true;
  try {
    await homeworkAiGrade(gradeDrawer.submission.id);
    await openGradeDrawer(gradeDrawer.submission.id);
  } catch (e) {
    error.value = e instanceof Error ? e.message : "AI 批改失败";
  } finally {
    gradeDrawer.gradingAI = false;
  }
}

async function saveFinalGrade() {
  if (!gradeDrawer.submission) return;
  gradeDrawer.saving = true;
  try {
    await homeworkFinalGrade(gradeDrawer.submission.id, gradeDrawer.score, gradeDrawer.comment);
    notice.value = "终审结果已保存";
    await openGradeDrawer(gradeDrawer.submission.id);
    if (submissionsDrawer.assignment) {
      await openSubmissionsDrawer(submissionsDrawer.assignment);
    }
  } catch (e) {
    error.value = e instanceof Error ? e.message : "保存终审失败";
  } finally {
    gradeDrawer.saving = false;
  }
}

function openStatusConfirm(item: HomeworkAssignment, action: "publish" | "close" | "reopen") {
  statusDialog.visible = true;
  statusDialog.assignmentId = item.id;
  statusDialog.action = action;
  statusDialog.message = `${action === 'publish' ? '发布' : action === 'close' ? '关闭' : '重开'}作业《${item.title}》？`;
}

async function confirmStatusChange() {
  try {
    if (statusDialog.action === "publish") {
      await homeworkPublishStatus(statusDialog.assignmentId);
      notice.value = "作业已发布";
    } else if (statusDialog.action === "close") {
      await homeworkCloseStatus(statusDialog.assignmentId);
      notice.value = "作业已关闭";
    } else {
      await homeworkReopenStatus(statusDialog.assignmentId);
      notice.value = "作业已重开";
    }
    statusDialog.visible = false;
    await loadAssignments();
  } catch (e) {
    error.value = e instanceof Error ? e.message : "状态更新失败";
  }
}


function openQuickAIModal() {
  quickAIModal.visible = true;
  quickAIModal.draft = null;
  quickAIModal.topic = "";
  quickAIModal.course_id = courseOptions.value.includes("course_big_data") ? "course_big_data" : (courseOptions.value[0] || "course_big_data");
  quickAIModal.node_id = "";
  quickAIModal.node_name = "";
  quickAIModal.node_path = [];
  quickAIModal.chapter_context = "";
  quickAIModal.objective_result_mode = "immediate";
  loadQuickCourseNodes();
}

async function generateQuickDraft() {
  if (!quickAIModal.topic.trim()) {
    error.value = "请先输入主题";
    return;
  }
  quickAIModal.loading = true;
  try {
    const res = await homeworkGenerateDraft({
      topic: quickAIModal.topic,
      assignment_type: quickAIModal.assignment_type,
      difficulty: quickAIModal.difficulty,
      class_name: quickAIModal.class_name,
      course_id: quickAIModal.course_id,
      node_id: quickAIModal.node_id,
      node_name: quickAIModal.node_name,
      node_path: quickAIModal.node_path,
      chapter_context: quickAIModal.chapter_context,
      objective_result_mode: quickAIModal.objective_result_mode,
    });
    quickAIModal.draft = res.draft;
    notice.value = res.ok ? "AI 草稿生成成功" : "AI 不可用，已返回兜底草稿";
  } catch (e) {
    error.value = e instanceof Error ? e.message : "AI 草稿生成失败";
  } finally {
    quickAIModal.loading = false;
  }
}

async function createQuickAssignment(publishNow: boolean) {
  if (!quickAIModal.draft) return;
  quickAIModal.creating = true;
  try {
    await homeworkPublishAssignment({
      title: quickAIModal.draft.title,
      description: quickAIModal.draft.description,
      assignment_type: quickAIModal.draft.assignment_type,
      class_name: quickAIModal.class_name,
      course_id: quickAIModal.course_id,
      node_id: quickAIModal.node_id,
      node_name: quickAIModal.node_name,
      node_path: quickAIModal.node_path,
      chapter_context: quickAIModal.chapter_context,
      objective_result_mode: quickAIModal.draft.objective_result_mode || quickAIModal.objective_result_mode,
      due_at: null,
      allow_late: false,
      total_score: quickAIModal.draft.total_score,
      rubric: quickAIModal.draft.rubric,
      questions: quickAIModal.draft.questions.map(
        (item) =>
          ({
            title: String(item.title || ""),
            prompt: String(item.prompt || ""),
            options: Array.isArray(item.options) ? item.options.map((x) => String(x)) : [],
            correct_answer: String(item.correct_answer || ""),
            reference_answer: String(item.reference_answer || ""),
            rubric: String(item.rubric || ""),
            test_cases: Array.isArray(item.test_cases) ? item.test_cases : [],
          }) satisfies HomeworkQuestion,
      ),
      publish_now: publishNow,
    });
    quickAIModal.visible = false;
    notice.value = publishNow ? "作业已创建并发布" : "作业草稿已创建";
    await loadAssignments();
  } catch (e) {
    error.value = e instanceof Error ? e.message : "快速创建失败";
  } finally {
    quickAIModal.creating = false;
  }
}

onMounted(loadAssignments);
</script>

<style scoped>
.homework-shell {
  display: grid;
  gap: 16px;
}

.homework-hero {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 12px;
}

.actions-row {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
}

.ai-promo {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  background: linear-gradient(135deg, #f0f9ff 0%, #ecfeff 100%);
  border: 1px solid #bae6fd;
}

.ghost-btn.emphasis {
  border-color: #0284c7;
  color: #075985;
  font-weight: 700;
}

.actions-cell {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.ghost-btn.small {
  padding: 4px 8px;
}

.modal-mask {
  position: fixed;
  z-index: 99;
  inset: 0;
  background: rgba(0, 0, 0, 0.35);
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 16px;
}

.drawer-mask {
  position: fixed;
  z-index: 120;
  inset: 0;
  background: rgba(2, 6, 23, 0.22);
  display: flex;
  justify-content: flex-end;
}

.drawer-panel {
  width: min(920px, 96vw);
  height: 100vh;
  background: #ffffff;
  border-left: 1px solid #dbe3ee;
  padding: 16px;
  overflow: auto;
  box-shadow: -16px 0 36px rgba(2, 6, 23, 0.16);
}

.grade-drawer {
  width: min(1120px, 98vw);
}

.summary-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 8px 12px;
}

.verdict-chip {
  display: inline-block;
  padding: 3px 8px;
  border-radius: 999px;
  font-size: 12px;
  font-weight: 700;
}

.verdict-chip.ok {
  color: #065f46;
  background: #d1fae5;
}

.verdict-chip.fail {
  color: #991b1b;
  background: #fee2e2;
}

.oj-pre {
  white-space: pre-wrap;
  margin: 0;
  max-width: 280px;
}

.answer-box {
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  padding: 10px;
  background: #fafafa;
}

.code-preview {
  border: 1px solid #1f2937;
  border-radius: 8px;
  overflow: hidden;
}

.answer-meta {
  margin-bottom: 8px;
}

.meta-chip {
  display: inline-flex;
  align-items: center;
  border: 1px solid #d4dbe7;
  border-radius: 999px;
  padding: 4px 10px;
  font-size: 12px;
  color: #334155;
  background: #f8fbff;
}

.full-width {
  display: block;
  margin-top: 8px;
}

.input-textarea {
  resize: vertical;
}

.modal-card {
  width: min(860px, 96vw);
  max-height: 86vh;
  overflow: auto;
  background: #fff;
  border-radius: 12px;
  padding: 14px;
}

.modal-card.compact {
  width: min(420px, 92vw);
}

.form-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 10px;
}

.input {
  width: 100%;
  border: 1px solid #d0d7de;
  border-radius: 8px;
  padding: 8px 10px;
  margin-top: 6px;
}

.question-card {
  border: 1px solid #e8eef6;
  border-radius: 10px;
  padding: 10px;
  margin-top: 10px;
}

.question-card.nested {
  margin-top: 8px;
  background: #fafcff;
}

.multiline {
  white-space: pre-wrap;
}

@media (max-width: 900px) {
  .form-grid {
    grid-template-columns: 1fr;
  }

  .ai-promo {
    flex-direction: column;
    align-items: flex-start;
  }

  .summary-grid {
    grid-template-columns: 1fr;
  }
}
</style>
