<template>
  <div class="teacher-shell">
    <section class="hero-panel teacher-hero">
      <div>
        <p class="eyebrow">Teacher Dashboard</p>
        <h1>班级学习概览与学生画像分析</h1>
        <p class="hero-desc">
          聚合班级整体掌握度、课程热度、学生画像和趋势数据，帮助教师更稳定地查看教学分析结果。
        </p>
      </div>
      <div class="teacher-hero-points">
        <div class="info-pill">班级概览</div>
        <div class="info-pill">学生画像</div>
        <div class="info-pill">课程热度</div>
        <div class="info-pill">教师孪生</div>
      </div>
    </section>

    <div class="teacher-tabbar">
      <button type="button" class="teacher-tab" :class="{ active: activeTab === 'overview' }"
              @click="switchTab('overview')">
        班级概览
      </button>
      <button type="button" class="teacher-tab" :class="{ active: activeTab === 'students' }"
              @click="switchTab('students')">
        学生画像
      </button>
      <button type="button" class="teacher-tab" :class="{ active: activeTab === 'heatmap' }"
              @click="switchTab('heatmap')">
        课程热度
      </button>
      <button type="button" class="teacher-tab" :class="{ active: activeTab === 'teacher-twin' }"
              @click="switchTab('teacher-twin')">
        教师孪生
      </button>
      <button type="button" class="teacher-tab" :class="{ active: activeTab === 'resources' }"
              @click="switchTab('resources')">
        课程资源
      </button>
    </div>

    <section v-if="loading" class="card-panel state-card">正在加载教师端数据...</section>
    <section v-else-if="error" class="card-panel state-card error-state">{{ error }}</section>

    <template v-else>
      <section v-if="activeTab === 'overview'" class="teacher-overview">
        <div class="metrics-grid-vue teacher-metrics-grid">
          <article class="card-panel metric-card-vue">
            <span class="metric-label">班级平均掌握度</span>
            <div class="metric-value">{{ overview?.class_avg_mastery ?? 0 }}%</div>
          </article>
          <article class="card-panel metric-card-vue">
            <span class="metric-label">学生人数</span>
            <div class="metric-value">{{ overview?.student_count ?? 0 }}</div>
          </article>
          <article class="card-panel metric-card-vue">
            <span class="metric-label">优秀人数</span>
            <div class="metric-value">{{ overview?.distribution.excellent ?? 0 }}</div>
          </article>
          <article class="card-panel metric-card-vue">
            <span class="metric-label">待提升人数</span>
            <div class="metric-value">{{ overview?.distribution.needs_improvement ?? 0 }}</div>
          </article>
        </div>

        <div class="industry-chart-grid two-up">
          <article class="card-panel industry-chart-card">
            <div class="section-head">
              <h3>掌握度分布</h3>
            </div>
            <div ref="distributionChartRef" class="industry-chart"></div>
          </article>
          <article class="card-panel industry-chart-card">
            <div class="section-head">
              <h3>知识点班级平均掌握度</h3>
            </div>
            <div ref="nodeBarChartRef" class="industry-chart"></div>
          </article>
        </div>
      </section>

      <section v-else-if="activeTab === 'students'" class="teacher-students">
        <article class="card-panel industry-table-card">
          <div class="section-head">
            <h3>学生列表</h3>
            <span class="muted">共 {{ students.length }} 名学生</span>
          </div>
          <div class="industry-table-wrap">
            <table class="industry-table">
              <thead>
              <tr>
                <th>用户名</th>
                <th>综合掌握度</th>
                <th>操作</th>
              </tr>
              </thead>
              <tbody>
              <tr v-for="student in students" :key="student.username">
                <td>{{ student.username }}</td>
                <td>
                    <span class="relevance-pill" :class="masteryClass(student.overall_mastery)">
                      {{ student.overall_mastery }}%
                    </span>
                </td>
                <td>
                  <button class="ghost-btn" type="button" @click="openStudentDetail(student.username)">查看详情</button>
                </td>
              </tr>
              </tbody>
            </table>
          </div>
        </article>

        <article v-if="selectedStudentDetail" class="card-panel teacher-detail-card">
          <div class="section-head">
            <div>
              <h3>{{ selectedStudentDetail.username }} 的学生画像</h3>
              <p class="hero-desc">这里会展示学生的知识点掌握情况、趋势和薄弱项。</p>
            </div>
            <button class="ghost-btn" type="button" @click="closeStudentDetail">关闭</button>
          </div>

          <div class="industry-chart-grid two-up">
            <article class="card-panel industry-chart-card">
              <div class="section-head">
                <h3>知识点掌握雷达图</h3>
              </div>
              <div ref="studentRadarChartRef" class="industry-chart"></div>
            </article>
            <article class="card-panel industry-chart-card">
              <div class="section-head">
                <h3>掌握度趋势（近 30 天）</h3>
              </div>
              <div ref="studentTrendChartRef" class="industry-chart"></div>
            </article>
          </div>

          <div class="card-panel teacher-weak-card">
            <div class="section-head">
              <h3>薄弱知识点</h3>
            </div>
            <ul class="message-list">
              <li v-for="node in selectedStudentDetail.weak_nodes" :key="`${node.node_id}-${node.priority}`">
                <strong>{{ node.node_id }}</strong>：掌握度 {{ node.mastery_score }}%，优先级 {{ node.priority }}
              </li>
              <li v-if="!selectedStudentDetail.weak_nodes.length">暂无明显薄弱知识点</li>
            </ul>
          </div>
        </article>
      </section>

      <section v-else-if="activeTab === 'heatmap'" class="teacher-heatmap">
        <div class="industry-chart-grid two-up">
          <article class="card-panel industry-chart-card">
            <div class="section-head">
              <h3>各知识点班级平均掌握度</h3>
            </div>
            <div ref="heatmapMasteryChartRef" class="industry-chart"></div>
          </article>
          <article class="card-panel industry-chart-card">
            <div class="section-head">
              <h3>各知识点学习人数</h3>
            </div>
            <div ref="heatmapCountChartRef" class="industry-chart"></div>
          </article>
        </div>
      </section>

      <section v-else-if="activeTab === 'teacher-twin'" class="teacher-twin">
        <div class="metrics-grid-vue teacher-metrics-grid">
          <article class="card-panel metric-card-vue">
            <span class="metric-label">教师总分</span>
            <div class="metric-value">{{ teacherTwin?.overall_score ?? 0 }}</div>
          </article>
          <article class="card-panel metric-card-vue">
            <span class="metric-label">覆盖学生数</span>
            <div class="metric-value">{{ teacherTwin?.student_scope.student_count ?? 0 }}</div>
          </article>
          <article class="card-panel metric-card-vue">
            <span class="metric-label">有孪生画像学生数</span>
            <div class="metric-value">{{ teacherTwin?.student_scope.students_with_twin ?? 0 }}</div>
          </article>
          <article class="card-panel metric-card-vue">
            <span class="metric-label">最近更新时间</span>
            <div class="metric-value" style="font-size: 1rem; font-weight: 600;">
              {{ teacherTwin?.last_updated ? new Date(teacherTwin.last_updated).toLocaleString() : '-' }}
            </div>
          </article>
        </div>

        <div class="industry-chart-grid two-up">
          <article class="card-panel industry-chart-card">
            <div class="section-head">
              <h3>教师数字能力六维雷达</h3>
            </div>
            <div ref="teacherTwinRadarChartRef" class="industry-chart"></div>
          </article>
          <article class="card-panel industry-table-card">
            <div class="section-head">
              <h3>六维明细分数</h3>
              <div style="display: flex; gap: 8px; align-items: center;">
                <span class="muted">自动根据系统数据更新</span>
                <button class="ghost-btn" type="button" @click="openTwinHelp">算法与子项说明</button>
              </div>
            </div>
            <div class="industry-table-wrap">
              <table class="industry-table">
                <thead>
                <tr>
                  <th>展开</th>
                  <th>维度</th>
                  <th>分数</th>
                  <th>子项数量</th>
                  <th>状态</th>
                </tr>
                </thead>
                <tbody>
                <template v-for="item in (teacherTwin?.dimensions ?? [])" :key="item.code">
                  <tr>
                    <td>
                      <button class="ghost-btn" type="button" @click="toggleDimensionExpand(item.code)">
                        {{ expandedDimensionCodes[item.code] ? '收起' : '展开' }}
                      </button>
                    </td>
                    <td>{{ item.name }}</td>
                    <td>{{ item.score }}</td>
                    <td>{{ getCurrentSubItemCount(item.sub_items) }} / {{ getExpectedSubItemCount(item.code) }}</td>
                    <td>
                      <span class="relevance-pill" :class="masteryClass(item.score)">
                        {{ item.score >= 80 ? '优势' : item.score >= 60 ? '稳定' : '待提升' }}
                      </span>
                    </td>
                  </tr>
                  <tr v-if="expandedDimensionCodes[item.code]">
                    <td colspan="5">
                      <div class="card-panel" style="padding: 10px; background: #f8fafc; border: 1px solid #e2e8f0;">
                        <table class="industry-table">
                          <thead>
                          <tr>
                            <th>子项</th>
                            <th>当前值</th>
                            <th>怎么得到</th>
                          </tr>
                          </thead>
                          <tbody>
                          <tr v-for="sub in getSubItemDetailRows(item.code, item.sub_items)" :key="item.code + '-' + sub.key">
                            <td>{{ sub.name }}</td>
                            <td>{{ sub.value }}</td>
                            <td>{{ sub.method }}</td>
                          </tr>
                          </tbody>
                        </table>
                      </div>
                    </td>
                  </tr>
                </template>
                </tbody>
              </table>
            </div>
          </article>
        </div>

        <article class="card-panel teacher-weak-card" v-if="teacherTwin?.data_diagnosis">
          <div class="section-head">
            <h3>数据完整度诊断</h3>
          </div>
          <ul class="message-list">
            <li>外部指标覆盖率：{{ ((teacherTwin.data_diagnosis.external_coverage_ratio || 0) * 100).toFixed(1) }}%</li>
            <li>{{ teacherTwin.data_diagnosis.summary }}</li>
          </ul>
        </article>

        <div class="industry-chart-grid two-up">
          <article class="card-panel teacher-weak-card">
            <div class="section-head">
              <h3>教学策略建议</h3>
              <button class="ghost-btn" type="button" :disabled="aiSuggestionsLoading" @click="requestAiSuggestions">
                {{ aiSuggestionsLoading ? 'AI生成中...' : 'AI生成建议' }}
              </button>
            </div>
            <ul class="message-list">
              <li v-for="item in (aiSuggestions?.teaching_strategy_suggestions ?? [])" :key="item.dimension + item.advice">
                <strong>{{ item.dimension }}：</strong>{{ item.advice }}
              </li>
              <li v-if="aiSuggestions?.message">{{ aiSuggestions.message }}</li>
              <li v-if="aiSuggestionsError">{{ aiSuggestionsError }}</li>
              <li v-if="!(aiSuggestions?.teaching_strategy_suggestions ?? []).length && !aiSuggestionsError">点击按钮后由 AI 生成建议</li>
            </ul>
          </article>
          <article class="card-panel teacher-weak-card">
            <div class="section-head">
              <h3>干预策略建议</h3>
              <span class="muted">按按钮触发 AI</span>
            </div>
            <ul class="message-list">
              <li v-for="item in (aiSuggestions?.intervention_suggestions ?? [])" :key="item.trigger + item.action">
                <strong>{{ item.trigger }}：</strong>{{ item.action }}
              </li>
              <li v-if="!(aiSuggestions?.intervention_suggestions ?? []).length">点击按钮后由 AI 生成建议</li>
            </ul>
          </article>
        </div>

        <article class="card-panel teacher-weak-card">
          <div class="section-head">
            <h3>缺失数据预留接口状态</h3>
            <span class="muted">用于后续自动对接教研区/批改明细等外部数据</span>
          </div>
          <ul class="message-list">
            <li v-for="item in (teacherTwin?.missing_data_hooks ?? [])" :key="item.field + item.source">
              <strong>{{ item.field }}</strong>（{{ item.status }}）- {{ item.note }}
            </li>
            <li v-if="!(teacherTwin?.missing_data_hooks ?? []).length">暂无缺失项</li>
          </ul>
        </article>
      </section>

      <section v-else class="teacher-resources">
        <article class="card-panel teacher-resource-card">
          <div class="section-head">
            <div>
              <h3>课程资源管理</h3>
              <p class="hero-desc">按课程知识结构查看资源，并直接上传或删除节点资料。</p>
            </div>
            <button class="ghost-btn" type="button" @click="loadKnowledgeGraph">刷新课程树</button>
          </div>

          <div v-if="uploadMessage" class="info-banner" :class="{ 'error-banner': uploadError }">
            {{ uploadMessage }}
          </div>

          <div class="teacher-tree">
            <div v-if="!knowledgeGraph" class="state-card">正在加载课程树...</div>
            <div v-else class="teacher-tree-root">
              <TeacherTreeNode
                  :node="knowledgeGraph"
                  :depth="0"
                  @upload="openUploadDialog"
                  @delete-resource="handleDeleteResource"
              />
            </div>
          </div>
        </article>
      </section>
    </template>

    <div v-if="uploadDialog.open" class="drawer-mask-vue" @click="closeUploadDialog"></div>
    <aside v-if="uploadDialog.open" class="industry-drawer teacher-upload-drawer">
      <div class="industry-drawer-head">
        <div>
          <p class="eyebrow">Upload Resource</p>
          <h3>上传资源到 {{ uploadDialog.nodeName }}</h3>
        </div>
        <button class="ghost-btn" type="button" @click="closeUploadDialog">关闭</button>
      </div>
      <div class="industry-drawer-body">
        <label class="field">
          <span>选择文件</span>
          <button type="button" class="ghost-btn" style="position: relative; width: 100%; display: flex; align-items: center; justify-content: center; min-height: 40px;">
            选择文件
            <input type="file" multiple accept=".pdf,.PDF,.doc,.docx,.ppt,.pptx" @change="handleFileSelect"
                   style="position: absolute; inset: 0; opacity: 0; cursor: pointer; width: 100%; height: 100%;"/>
          </button>
        </label>
        <ul v-if="uploadDialog.files.length" class="message-list">
          <li v-for="file in uploadDialog.files" :key="file.name">{{ file.name }}</li>
        </ul>
        <button class="primary-link button-like full-width" type="button"
                :disabled="!uploadDialog.files.length || uploading" @click="submitUpload">
          {{ uploading ? "上传中..." : "确认上传" }}
        </button>
      </div>
    </aside>

    <div v-if="twinHelpDialogOpen" class="drawer-mask-vue" @click="closeTwinHelp"></div>
    <aside v-if="twinHelpDialogOpen" class="industry-drawer teacher-upload-drawer" style="max-width: 840px; width: min(92vw, 840px);">
      <div class="industry-drawer-head">
        <div>
          <p class="eyebrow">Teacher Twin Help</p>
          <h3>六维算法与子项说明</h3>
        </div>
        <button class="ghost-btn" type="button" @click="closeTwinHelp">关闭</button>
      </div>
      <div class="industry-drawer-body" style="display: grid; gap: 12px;">
        <article class="card-panel teacher-weak-card" style="padding: 12px;">
          <div class="section-head">
            <h3>说明</h3>
          </div>
          <ul class="message-list">
            <li>每个维度固定 3 个子项；可点击“展开”查看子项值和计算方式。</li>
            <li>总分计算：六维平均分，即 $总分=\frac{\sum_{i=1}^{6}维度_i}{6}$。</li>
            <li>教学/干预建议默认不生成，点击“AI生成建议”才调用模型。</li>
          </ul>
        </article>

        <article class="card-panel industry-table-card" style="padding: 12px;">
          <div class="section-head">
            <h3>维度算法</h3>
          </div>
          <div class="industry-table-wrap">
            <table class="industry-table">
              <thead>
              <tr>
                <th>维度</th>
                <th>子项数</th>
                <th>子项名称</th>
                <th>计算逻辑</th>
              </tr>
              </thead>
              <tbody>
              <tr v-for="d in teacherTwinHelpRows" :key="d.code">
                <td>{{ d.name }}</td>
                <td>{{ d.expectedSubItemCount }}</td>
                <td>{{ d.subItems.join('、') }}</td>
                <td>{{ d.algorithm }}</td>
              </tr>
              </tbody>
            </table>
          </div>
        </article>
      </div>
    </aside>
  </div>
</template>

<script setup lang="ts">
import {computed, defineComponent, h, nextTick, onBeforeUnmount, onMounted, PropType, ref, watch} from "vue";
import {
  deleteTeacherResource,
  fetchClassOverview,
  generateTeacherTwinAiSuggestions,
  fetchTeacherHeatmap,
  fetchTeacherStudentDetail,
  fetchTeacherStudentTrend,
  fetchTeacherTwin,
  uploadTeacherResources,
} from "../../api/teacher";
import {init, type ECharts} from "../../lib/echarts";
import {fetchKnowledgeGraph} from "../../api/knowledgeGraph";
import {type CourseNode} from "../../types/knowledgeGraph"
import {
  type ClassOverviewResponse,
  type TeacherStudentDetail,
  type TeacherStudentTrend,
  type TeacherTwinAiSuggestionsResponse,
  type TeacherTwinSummary,
} from "../../types/teacher"
import {type HeatmapResponse} from "../../api/client"
import {KnowledgeGraphResponse} from "../../types/knowledgeGraph";

type TeacherTab = "overview" | "students" | "heatmap" | "teacher-twin" | "resources";

const activeTab = ref<TeacherTab>("overview");
const loading = ref(true);
const error = ref("");
const overview = ref<ClassOverviewResponse | null>(null);
const heatmapData = ref<HeatmapResponse | null>(null);
const teacherTwin = ref<TeacherTwinSummary | null>(null);
const knowledgeGraph = ref<KnowledgeGraphResponse | null>(null);
const selectedStudentDetail = ref<TeacherStudentDetail | null>(null);
const selectedStudentTrend = ref<TeacherStudentTrend | null>(null);
const uploadMessage = ref("");
const uploadError = ref(false);
const uploading = ref(false);
const twinHelpDialogOpen = ref(false);
const expandedDimensionCodes = ref<Record<string, boolean>>({});
const aiSuggestionsLoading = ref(false);
const aiSuggestionsError = ref("");
const aiSuggestions = ref<TeacherTwinAiSuggestionsResponse | null>(null);
const uploadDialog = ref<{ open: boolean; nodeName: string; files: File[] }>({
  open: false,
  nodeName: "",
  files: [],
});

const distributionChartRef = ref<HTMLDivElement | null>(null);
const nodeBarChartRef = ref<HTMLDivElement | null>(null);
const studentRadarChartRef = ref<HTMLDivElement | null>(null);
const studentTrendChartRef = ref<HTMLDivElement | null>(null);
const heatmapMasteryChartRef = ref<HTMLDivElement | null>(null);
const heatmapCountChartRef = ref<HTMLDivElement | null>(null);
const teacherTwinRadarChartRef = ref<HTMLDivElement | null>(null);

let distributionChart: ECharts | null = null;
let nodeBarChart: ECharts | null = null;
let studentRadarChart: ECharts | null = null;
let studentTrendChart: ECharts | null = null;
let heatmapMasteryChart: ECharts | null = null;
let heatmapCountChart: ECharts | null = null;
let teacherTwinRadarChart: ECharts | null = null;
let resizeTimer: number | null = null;

const students = computed(() => overview.value?.students ?? []);

const dimensionHelpMeta: Record<string, {
  name: string;
  expectedSubItemCount: number;
  subItems: string[];
  algorithm: string;
}> = {
  professional_engagement: {
    name: "专业投入",
    expectedSubItemCount: 3,
    subItems: ["平台活跃度", "教研协作行为", "系统功能探索度"],
    algorithm: "综合在线时长、登录频次、教研协作和高级功能使用情况。",
  },
  digital_resources: {
    name: "数字资源",
    expectedSubItemCount: 3,
    subItems: ["资源多样性指数", "资源迭代频率", "资源复用与共享"],
    algorithm: "综合资源类型丰富度、更新频率和被他人复用情况。",
  },
  teaching_learning: {
    name: "教学与学习",
    expectedSubItemCount: 3,
    subItems: ["在线互动频次", "教学节奏控制", "人机协同度"],
    algorithm: "综合教学互动、任务按时发布和 AI 推荐动作执行情况。",
  },
  assessment: {
    name: "评估",
    expectedSubItemCount: 3,
    subItems: ["评估方式多元化", "反馈及时性与深度", "数据驱动调整"],
    algorithm: "综合评估类型覆盖、批改反馈质量和测后补救动作。",
  },
  empowering_learners: {
    name: "赋能学习者",
    expectedSubItemCount: 3,
    subItems: ["个性化路径下发率", "干预策略实施", "学生学习主动性反哺"],
    algorithm: "综合个性化推送、风险干预和学生主动参与表现。",
  },
  facilitating_digital_competence: {
    name: "促进学习者数字能力",
    expectedSubItemCount: 3,
    subItems: ["数字化任务占比", "协作任务设计", "探究式学习配置"],
    algorithm: "综合数字化任务、协作任务和探究式学习配置比例。",
  },
};

const subItemExplainMeta: Record<string, Record<string, { name: string; source: string; method: string }>> = {
  professional_engagement: {
    platform_activity: { name: "平台活跃度", source: "sessions", method: "统计近 7 天会话时长与登录频次" },
    teaching_research_collaboration: { name: "教研协作行为", source: "user_states.teacher_ext", method: "读取 external-sync 注入的教研帖、共享课件、联合备课计数" },
    feature_exploration: { name: "系统功能探索度", source: "llm_logs.metadata.feature", method: "统计高级功能 feature 命中次数" },
  },
  digital_resources: {
    resource_diversity_index: { name: "资源多样性指数", source: "learning_plans.filename", method: "统计文件后缀格式数" },
    resource_iteration_frequency: { name: "资源迭代频率", source: "learning_plans.data.revision_count", method: "汇总 revision_count，无则按资源条目数估算" },
    resource_reuse_and_sharing: { name: "资源复用与共享", source: "user_states.teacher_ext", method: "读取 external-sync 注入的被引用次数" },
  },
  teaching_learning: {
    online_interaction_frequency: { name: "在线互动频次", source: "llm_logs.metadata + user_states.teacher_ext", method: "统计公告/讨论并结合回复率与响应时长" },
    teaching_rhythm_control: { name: "教学节奏控制", source: "user_states.teacher_ext.on_time_release_ratio", method: "读取按时发布率，缺失时用默认值" },
    human_ai_collaboration: { name: "人机协同度", source: "llm_logs.metadata.ai_recommendation/ai_executed", method: "执行率=执行动作数/推荐动作数" },
  },
  assessment: {
    assessment_diversification: { name: "评估方式多元化", source: "llm_logs.metadata.assessment_type", method: "统计评估类型去重数" },
    feedback_timeliness_and_depth: { name: "反馈及时性与深度", source: "llm_logs.metadata.feedback_text/grading_minutes", method: "计算平均反馈长度与平均批改耗时" },
    data_driven_adjustment: { name: "数据驱动调整", source: "llm_logs.metadata.action", method: "统计补救讲解/公告动作次数" },
  },
  empowering_learners: {
    personalized_path_dispatch_rate: { name: "个性化路径下发率", source: "user_states.teacher_ext + users(student)", method: "下发率=个性化推送次数/覆盖学生数" },
    intervention_strategy_execution: { name: "干预策略实施", source: "user_states.teacher_ext + twin_profiles", method: "执行率=干预次数/风险学生数" },
    student_initiative_feedback: { name: "学生学习主动性反哺", source: "llm_logs.metadata.student_username/initiated_by_student", method: "统计学生主动触发互动占比" },
  },
  facilitating_digital_competence: {
    digital_task_ratio: { name: "数字化任务占比", source: "user_states.teacher_ext 或 llm_logs.metadata.task_mode", method: "数字化任务数/总任务数" },
    collaborative_task_design: { name: "协作任务设计", source: "user_states.teacher_ext 或 llm_logs.metadata.task_group_mode", method: "协作任务数/总任务数" },
    inquiry_learning_configuration: { name: "探究式学习配置", source: "user_states.teacher_ext 或 llm_logs.metadata.task_type", method: "探究学习时长/总教学时长" },
  },
};

const teacherTwinHelpRows = computed(() => {
  return Object.entries(dimensionHelpMeta).map(([code, value]) => ({
    code,
    ...value,
  }));
});

function openTwinHelp() {
  twinHelpDialogOpen.value = true;
}

function closeTwinHelp() {
  twinHelpDialogOpen.value = false;
}

function getExpectedSubItemCount(code: string): number {
  return dimensionHelpMeta[code]?.expectedSubItemCount ?? 3;
}

function getSubItemNames(code: string): string[] {
  return dimensionHelpMeta[code]?.subItems ?? ["子项定义待补充"];
}

function getCurrentSubItemCount(subItems: Record<string, unknown> | undefined): number {
  if (!subItems || typeof subItems !== "object") return 0;
  return Object.keys(subItems).length;
}

function toggleDimensionExpand(code: string) {
  expandedDimensionCodes.value[code] = !expandedDimensionCodes.value[code];
}

function summarizeSubItemValue(value: unknown): string {
  if (value === null || value === undefined) return "-";
  if (typeof value === "number") return String(value);
  if (typeof value === "string") return value;
  if (Array.isArray(value)) return value.join("、");
  if (typeof value === "object") {
    const entries = Object.entries(value as Record<string, unknown>);
    const keyMap: Record<string, string> = {
      weekly_online_hours: "周在线时长",
      weekly_login_frequency: "周登录次数",
      posts: "教研发帖数",
      shared_courseware: "共享课件数",
      co_preparation_frequency: "联合备课频次",
      advanced_feature_usage_count: "高级功能使用次数",
      format_count: "资源格式数",
      formats: "资源格式",
      revision_count: "资源更新次数",
      resource_count: "资源总数",
      referenced_by_other_teachers: "被其他教师引用次数",
      announcements: "公告发布数",
      discussion_topics: "讨论话题数",
      teacher_reply_rate: "回复率",
      avg_response_minutes: "平均响应时长(分钟)",
      on_time_release_ratio: "按时发布率",
      session_count: "会话数",
      ai_recommended_actions: "AI推荐动作数",
      ai_executed_actions: "AI执行动作数",
      ai_execution_rate: "AI执行率",
      assessment_types: "评估类型",
      type_count: "评估类型数",
      subjective_feedback_count: "主观反馈条数",
      avg_feedback_length: "平均反馈长度",
      avg_grading_minutes: "平均批改时长(分钟)",
      remediation_actions: "补救教学动作数",
      personalized_push_count: "个性化推送次数",
      student_count: "覆盖学生数",
      dispatch_rate: "下发率",
      risk_intervention_count: "风险干预次数",
      at_risk_student_count: "风险学生数",
      execution_ratio: "执行率",
      non_forced_engagement: "学生主动参与度",
      digital_tasks: "数字化任务数",
      total_tasks: "总任务数",
      ratio: "占比",
      collaborative_tasks: "协作任务数",
      inquiry_learning_hours: "探究学习时长",
      total_teaching_hours: "总教学时长",
    };

    return entries
      .map(([k, v]) => {
        const label = keyMap[k] || k;
        if (Array.isArray(v)) {
          return `${label}: ${v.join("、")}`;
        }
        if (typeof v === "number" && (k.includes("ratio") || k.includes("rate"))) {
          return `${label}: ${(v * 100).toFixed(1)}%`;
        }
        return `${label}: ${String(v)}`;
      })
      .join("；");
  }
  return String(value);
}

function getSubItemDetailRows(code: string, subItems: Record<string, unknown> | undefined) {
  const explain = subItemExplainMeta[code] || {};
  const current = (subItems && typeof subItems === "object") ? subItems : {};
  const keys = Object.keys(current);
  if (!keys.length) {
    return [{ key: "none", name: "暂无", value: "暂无可用数据", source: "-", method: "-" }];
  }
  return keys.map((key) => {
    const meta = explain[key] || { name: key, source: "未知来源", method: "暂无说明" };
    return {
      key,
      name: meta.name,
      value: summarizeSubItemValue((current as Record<string, unknown>)[key]),
      source: meta.source,
      method: meta.method,
    };
  });
}

function disposeHiddenCharts() {
  if (activeTab.value !== "overview") {
    distributionChart?.dispose();
    nodeBarChart?.dispose();
    distributionChart = null;
    nodeBarChart = null;
  }
  if (activeTab.value !== "students") {
    studentRadarChart?.dispose();
    studentTrendChart?.dispose();
    studentRadarChart = null;
    studentTrendChart = null;
  }
  if (activeTab.value !== "heatmap") {
    heatmapMasteryChart?.dispose();
    heatmapCountChart?.dispose();
    heatmapMasteryChart = null;
    heatmapCountChart = null;
  }
  if (activeTab.value !== "teacher-twin") {
    teacherTwinRadarChart?.dispose();
    teacherTwinRadarChart = null;
  }
}

function safeRender(fn: () => void) {
  try {
    fn();
  } catch (err) {
    console.error("TeacherDashboard render failed:", err);
    error.value = err instanceof Error ? err.message : "教师页面渲染失败";
  }
}

function switchTab(tab: TeacherTab) {
  activeTab.value = tab;
}

const TeacherTreeNode: any = defineComponent({
  name: "TeacherTreeNode",
  props: {
    node: {
      type: Object as PropType<Record<string, unknown>>,
      required: true,
    },
    depth: {
      type: Number,
      default: 0,
    },
  },
  emits: ["upload", "delete-resource"],
  setup(props, {emit}) {
    const expanded = ref(props.depth < 1);

    const children = computed(() => {
      const direct =
          (props.node.children as CourseNode[] | undefined) ??
          (props.node.grandchildren as CourseNode[] | undefined) ??
          (props.node["great-grandchildren"] as CourseNode[] | undefined) ??
          [];
      return Array.isArray(direct) ? direct : [];
    });

    const resources = computed(() => {
      const raw = props.node.resource_path;
      if (Array.isArray(raw)) return raw;
      if (typeof raw === "string" && raw) return [raw];
      return [];
    });

    return (): any =>
        h("div", {class: "teacher-tree-node-wrap"}, [
          h("div", {class: ["teacher-tree-item", props.depth === 0 ? "root" : props.depth === 1 ? "level-1" : props.depth === 2 ? "level-2" : "level-3"]}, [
            children.value.length
                ? h(
                    "button",
                    {
                      class: "teacher-tree-toggle",
                      type: "button",
                      onClick: () => {
                        expanded.value = !expanded.value;
                      },
                    },
                    expanded.value ? "▾" : "▸",
                )
                : h("span", {class: "teacher-tree-toggle placeholder"}, "·"),
            h("span", {class: "teacher-tree-name"}, String(props.node.name ?? "未命名节点")),
            resources.value.length ? h("span", {class: "teacher-tree-count"}, `${resources.value.length} 个资源`) : null,
            props.depth > 0
                ? h(
                    "button",
                    {
                      class: "ghost-btn teacher-tree-upload",
                      type: "button",
                      onClick: () => emit("upload", String(props.node.name ?? "")),
                    },
                    "上传",
                )
                : null,
          ]),
          resources.value.length
              ? h(
                  "div",
                  {class: "teacher-resource-list"},
                  resources.value.map((resource, index) =>
                      h("div", {class: "teacher-resource-row", key: `${String(props.node.name ?? "")}-${index}`}, [
                        h("span", {class: "teacher-resource-name", title: resource}, resource.split("/").pop() || resource),
                        h(
                            "button",
                            {
                              class: "teacher-resource-delete",
                              type: "button",
                              onClick: () =>
                                  emit("delete-resource", {
                                    nodeName: String(props.node.name ?? ""),
                                    resourceIndex: index,
                                  }),
                            },
                            "删除",
                        ),
                      ]),
                  ),
              )
              : null,
          children.value.length && expanded.value
              ? h(
                  "div",
                  {class: "teacher-tree-children"},
                  children.value.map((child) =>
                      h(TeacherTreeNode, {
                        node: child,
                        depth: props.depth + 1,
                        onUpload: (nodeName: string) => emit("upload", nodeName),
                        onDeleteResource: (payload: {
                          nodeName: string;
                          resourceIndex: number
                        }) => emit("delete-resource", payload),
                      }),
                  ),
              )
              : null,
        ]);
  },
});

watch(
    () => [selectedStudentDetail.value, selectedStudentTrend.value],
    async () => {
      if (!selectedStudentDetail.value || activeTab.value !== "students") return;
      await nextTick();
      safeRender(renderStudentDetailCharts);
    },
    {deep: true},
);

watch(activeTab, async () => {
  await nextTick();
  disposeHiddenCharts();
  safeRender(renderActiveTabCharts);
});

async function loadTeacherData() {
  loading.value = true;
  error.value = "";
  try {
    const [overviewRes, heatmapRes, graphRes, teacherTwinRes] = await Promise.all([
      fetchClassOverview(),
      fetchTeacherHeatmap(),
      fetchKnowledgeGraph(),
      fetchTeacherTwin(),
    ]);
    overview.value = overviewRes;
    heatmapData.value = heatmapRes;
    knowledgeGraph.value = graphRes;
    teacherTwin.value = teacherTwinRes;
    aiSuggestions.value = null;
    aiSuggestionsError.value = "";
  } catch (err) {
    error.value = err instanceof Error ? err.message : "教师端数据加载失败";
  } finally {
    loading.value = false;
    await nextTick();
    safeRender(renderActiveTabCharts);
  }
}

async function requestAiSuggestions() {
  aiSuggestionsLoading.value = true;
  aiSuggestionsError.value = "";
  try {
    aiSuggestions.value = await generateTeacherTwinAiSuggestions();
  } catch (err) {
    aiSuggestionsError.value = err instanceof Error ? err.message : "AI 生成失败，请稍后重试";
  } finally {
    aiSuggestionsLoading.value = false;
  }
}

function renderActiveTabCharts() {
  if (activeTab.value === "overview" && overview.value) {
    renderOverviewCharts(overview.value);
  }
  if (activeTab.value === "heatmap" && heatmapData.value) {
    renderHeatmapCharts(heatmapData.value);
  }
  if (activeTab.value === "students" && selectedStudentDetail.value) {
    renderStudentDetailCharts();
  }
  if (activeTab.value === "teacher-twin" && teacherTwin.value) {
    renderTeacherTwinCharts(teacherTwin.value);
  }
}

async function openStudentDetail(username: string) {
  try {
    const [detail, trend] = await Promise.all([
      fetchTeacherStudentDetail(username),
      fetchTeacherStudentTrend(username),
    ]);
    selectedStudentDetail.value = detail;
    selectedStudentTrend.value = trend;
    activeTab.value = "students";
  } catch (err) {
    error.value = err instanceof Error ? err.message : "学生详情加载失败";
  }
}

function closeStudentDetail() {
  selectedStudentDetail.value = null;
  selectedStudentTrend.value = null;
}

async function loadKnowledgeGraph() {
  knowledgeGraph.value = await fetchKnowledgeGraph();
}

function openUploadDialog(nodeName: string) {
  uploadDialog.value = {open: true, nodeName, files: []};
}

function closeUploadDialog() {
  uploadDialog.value = {open: false, nodeName: "", files: []};
}

function handleFileSelect(event: Event) {
  const target = event.target as HTMLInputElement;
  uploadDialog.value.files = Array.from(target.files ?? []);
}

async function submitUpload() {
  if (!uploadDialog.value.nodeName || !uploadDialog.value.files.length) return;
  uploading.value = true;
  uploadMessage.value = "";
  uploadError.value = false;
  try {
    const data = await uploadTeacherResources(uploadDialog.value.nodeName, uploadDialog.value.files);
    uploadMessage.value = data.message || "上传完成";
    uploadError.value = Boolean(data.error);
    await loadKnowledgeGraph();
    closeUploadDialog();
  } catch (err) {
    uploadMessage.value = err instanceof Error ? err.message : "资源上传失败";
    uploadError.value = true;
  } finally {
    uploading.value = false;
  }
}

async function handleDeleteResource(payload: { nodeName: string; resourceIndex: number }) {
  try {
    await deleteTeacherResource(payload.nodeName, payload.resourceIndex);
    uploadMessage.value = "资源已删除";
    uploadError.value = false;
    await loadKnowledgeGraph();
  } catch (err) {
    uploadMessage.value = err instanceof Error ? err.message : "删除资源失败";
    uploadError.value = true;
  }
}

function masteryClass(score: number) {
  if (score >= 80) return "mastery-high";
  if (score >= 60) return "mastery-mid";
  return "mastery-low";
}

function renderOverviewCharts(data: ClassOverviewResponse) {
  if (distributionChartRef.value) {
    distributionChart ??= init(distributionChartRef.value);
    distributionChart.setOption({
      tooltip: {trigger: "item", formatter: "{b}: {c} 人 ({d}%)"},
      legend: {bottom: 0},
      series: [
        {
          type: "pie",
          radius: ["42%", "70%"],
          data: [
            {value: data.distribution.excellent ?? 0, name: "优秀（≥80）", itemStyle: {color: "#22c55e"}},
            {value: data.distribution.good ?? 0, name: "良好（60-79）", itemStyle: {color: "#3b82f6"}},
            {value: data.distribution.needs_improvement ?? 0, name: "待提升（<60）", itemStyle: {color: "#ef4444"}},
          ],
          label: {formatter: "{b}\n{c}人", color: "#334155"},
        },
      ],
    });
    distributionChart.resize();
  }

  if (nodeBarChartRef.value) {
    nodeBarChart ??= init(nodeBarChartRef.value);
    const rows = [...(data.node_avg_mastery ?? [])].sort((a, b) => a.avg_mastery - b.avg_mastery);
    nodeBarChart.setOption({
      tooltip: {trigger: "axis"},
      grid: {left: 120, right: 24, top: 18, bottom: 16},
      xAxis: {type: "value", max: 100, axisLabel: {formatter: "{value}%"}},
      yAxis: {
        type: "category",
        data: rows.map((item) => item.node_id),
        axisLabel: {width: 110, overflow: "truncate", fontSize: 12},
      },
      series: [
        {
          type: "bar",
          data: rows.map((item) => item.avg_mastery),
          itemStyle: {color: "#4f7cff", borderRadius: [0, 10, 10, 0]},
          label: {show: true, position: "right", formatter: "{c}%"},
        },
      ],
    });
    nodeBarChart.resize();
  }
}

function renderStudentDetailCharts() {
  if (!selectedStudentDetail.value) return;

  if (studentRadarChartRef.value) {
    studentRadarChart ??= init(studentRadarChartRef.value);
    const nodes = selectedStudentDetail.value.knowledge_nodes ?? [];
    studentRadarChart.setOption({
      tooltip: {},
      radar: {
        radius: "62%",
        indicator: nodes.map((node) => ({name: node.node_id, max: 100})),
      },
      series: [
        {
          type: "radar",
          data: [
            {
              value: nodes.map((node) => node.mastery_score),
              name: "掌握度",
              areaStyle: {opacity: 0.24},
              lineStyle: {color: "#2563eb"},
              itemStyle: {color: "#2563eb"},
            },
          ],
        },
      ],
    });
    studentRadarChart.resize();
  }

  if (studentTrendChartRef.value) {
    studentTrendChart ??= init(studentTrendChartRef.value);
    const trend = selectedStudentTrend.value?.trend ?? [];
    studentTrendChart.setOption({
      tooltip: {trigger: "axis"},
      grid: {left: 46, right: 24, top: 18, bottom: 40},
      xAxis: {
        type: "category",
        data: trend.map((item) => item.date),
        axisLabel: {rotate: 28, fontSize: 11},
      },
      yAxis: {type: "value", min: 0, max: 100, axisLabel: {formatter: "{value}%"}},
      series: [
        {
          type: "line",
          smooth: true,
          data: trend.map((item) => item.overall_mastery),
          lineStyle: {color: "#2563eb", width: 3},
          areaStyle: {color: "rgba(37, 99, 235, 0.14)"},
          symbolSize: 8,
        },
      ],
    });
    studentTrendChart.resize();
  }
}

function renderHeatmapCharts(data: HeatmapResponse) {
  const rows = [...(data.nodes ?? [])].sort((a, b) => a.avg_mastery - b.avg_mastery);
  const names = rows.map((item) => item.node_id);

  if (heatmapMasteryChartRef.value) {
    heatmapMasteryChart ??= init(heatmapMasteryChartRef.value);
    heatmapMasteryChart.setOption({
      tooltip: {
        trigger: "axis",
        formatter: (params: Array<{
          name: string;
          value: number
        }>) => `${params[0].name}<br/>平均掌握度：${params[0].value}%`,
      },
      grid: {left: 140, right: 24, top: 18, bottom: 16},
      xAxis: {type: "value", max: 100, axisLabel: {formatter: "{value}%"}},
      yAxis: {type: "category", data: names, axisLabel: {width: 120, overflow: "truncate", fontSize: 12}},
      series: [
        {
          type: "bar",
          data: rows.map((item) => item.avg_mastery),
          itemStyle: {
            borderRadius: [0, 10, 10, 0],
            color: (params: { value: number }) => {
              if (params.value >= 75) return "#22c55e";
              if (params.value >= 50) return "#f59e0b";
              return "#ef4444";
            },
          },
          label: {show: true, position: "right", formatter: "{c}%"},
        },
      ],
    });
    heatmapMasteryChart.resize();
  }

  if (heatmapCountChartRef.value) {
    heatmapCountChart ??= init(heatmapCountChartRef.value);
    heatmapCountChart.setOption({
      tooltip: {
        trigger: "axis",
        formatter: (params: Array<{
          name: string;
          value: number
        }>) => `${params[0].name}<br/>学习人数：${params[0].value} 人`,
      },
      grid: {left: 140, right: 24, top: 18, bottom: 16},
      xAxis: {type: "value", minInterval: 1},
      yAxis: {type: "category", data: names, axisLabel: {width: 120, overflow: "truncate", fontSize: 12}},
      series: [
        {
          type: "bar",
          data: rows.map((item) => item.student_count),
          itemStyle: {color: "#7a6ad8", borderRadius: [0, 10, 10, 0]},
          label: {show: true, position: "right", formatter: "{c} 人"},
        },
      ],
    });
    heatmapCountChart.resize();
  }
}

function renderTeacherTwinCharts(data: TeacherTwinSummary) {
  if (!teacherTwinRadarChartRef.value) return;
  teacherTwinRadarChart ??= init(teacherTwinRadarChartRef.value);
  const radar = data.radar ?? [];
  teacherTwinRadarChart.setOption({
    tooltip: {},
    radar: {
      radius: "64%",
      indicator: radar.map((item) => ({name: item.name, max: 100})),
      splitLine: {lineStyle: {color: "rgba(100, 116, 139, 0.35)"}},
      axisLine: {lineStyle: {color: "rgba(30, 64, 175, 0.35)"}},
    },
    series: [
      {
        type: "radar",
        data: [
          {
            value: radar.map((item) => item.value),
            name: "教师数字能力",
            areaStyle: {opacity: 0.26, color: "rgba(14, 116, 144, 0.35)"},
            lineStyle: {color: "#0e7490", width: 3},
            itemStyle: {color: "#0e7490"},
          },
        ],
      },
    ],
  });
  teacherTwinRadarChart.resize();
}

function handleResize() {
  if (resizeTimer) window.clearTimeout(resizeTimer);
  resizeTimer = window.setTimeout(() => {
    [distributionChart, nodeBarChart, studentRadarChart, studentTrendChart, heatmapMasteryChart, heatmapCountChart, teacherTwinRadarChart].forEach((chart) => chart?.resize());
  }, 120);
}

onMounted(async () => {
  await loadTeacherData();
  window.addEventListener("resize", handleResize);
});

onBeforeUnmount(() => {
  window.removeEventListener("resize", handleResize);
  [distributionChart, nodeBarChart, studentRadarChart, studentTrendChart, heatmapMasteryChart, heatmapCountChart, teacherTwinRadarChart].forEach((chart) => chart?.dispose());
});
</script>
