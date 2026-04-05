import axios from "axios";
import { apiClient } from "./client";

export interface TechnicalLevel {
  label: string;
  code: string;
  description: string;
}

export interface RadarMetric {
  name: string;
  value: number;
}

export interface RiskAlert {
  code: string;
  level: string;
  title: string;
  detail: string;
}

export interface WeakNode {
  node_id: string;
  node_path: string[];
  mastery_score: number;
  progress: number;
  quiz_score: number;
}

export interface TrendPoint {
  date: string;
  overall_mastery: number;
}

export interface StudentTwinSummary {
  username: string;
  last_updated: string;
  overall_mastery: number;
  technical_level: TechnicalLevel;
  radar: RadarMetric[];
  weak_nodes: WeakNode[];
  risk_alerts: RiskAlert[];
  trend: {
    trend_status: string;
    change: number;
    summary: string;
    points: TrendPoint[];
  };
  node_summary: {
    total_nodes: number;
    weak_node_count: number;
    strong_node_count: number;
    average_progress: number;
    average_quiz_score: number;
  };
}

export interface LearningPlanEntry {
  date: string;
  topic: string;
  priority: string;
  materials: string[];
  deadline?: string;
}

export interface LearningPlanFile {
  filename: string;
  path: string;
  category?: string;
  updated_at?: string;
  data: LearningPlanEntry[];
}

export interface LearningPathNode {
  node_id: string;
  mastery_score: number;
  priority: number;
  llm_priority?: number | null;
  resources?: Array<{ title?: string; url: string }>;
}

export interface LearningPathResponse {
  status?: string;
  message?: string;
  generated_at?: string;
  llm_advice?: string;
  llm_order_reason?: string;
  weak_nodes?: LearningPathNode[];
}

export interface CourseNode {
  id?: number;
  name: string;
  flag?: string;
  description?: string;
  resource_path?: string[] | string;
  grandchildren?: CourseNode[];
  "great-grandchildren"?: CourseNode[];
}

export interface KnowledgeGraphResponse {
  name?: string;
  flag?: string;
  children?: CourseNode[];
}

export interface LearningProgressGroup {
  completed: number;
  total: number;
  progress: number;
}

export interface LearningProgressResponse {
  chapters: LearningProgressGroup;
  sections: LearningProgressGroup;
  points: LearningProgressGroup;
}

export interface GraphVisualizationNode {
  id: number;
  parentId: number;
  nodeName: string;
  description?: string;
  flag?: number;
  childCount?: number;
  level?: number;
  mocKgNodeAvgStatisticsDto?: {
    avgMasteryRate?: number;
    avgCompletionRate?: number;
    avgLearnedTimeCount?: number;
  };
}

export interface GraphVisualizationRelation {
  fromNodeId: number;
  toNodeId: number;
  relationType?: number;
}

export interface GraphVisualizationResponse {
  mocKgNodeDtoList: GraphVisualizationNode[];
  mocKgRelationDtoList?: GraphVisualizationRelation[];
}

export interface ChatResponse {
  response: string;
  used_fallback?: boolean;
  used_retriever?: boolean;
}

export interface SummaryResponse {
  summary?: string;
  used_retriever?: boolean;
}

export interface QuizQuestion {
  topic: string;
  question: string;
  correct: string;
}

export interface QuizState {
  subject: string;
  language: string;
  questions: QuizQuestion[];
  index: number;
  scores: Record<string, [number, number]>;
  correct_total: number;
}

export interface QuizStartResponse {
  question: QuizQuestion;
  state: QuizState;
  used_retriever?: boolean;
}

export interface QuizAnswerResponse {
  finished: boolean;
  is_correct?: boolean;
  correct_answer?: string;
  next_question?: QuizQuestion;
  results?: string;
  state: QuizState;
}

export interface QuizSummaryResponse {
  summary: string;
}

export interface DashboardStudentSummary {
  username: string;
  overall_mastery: number;
}

export interface ClassOverviewResponse {
  class_avg_mastery: number;
  student_count: number;
  distribution: {
    excellent: number;
    good: number;
    needs_improvement: number;
  };
  students: DashboardStudentSummary[];
  node_avg_mastery: Array<{
    node_id: string;
    avg_mastery: number;
  }>;
}

export interface TeacherWeakNode {
  node_id: string;
  mastery_score: number;
  priority: number;
}

export interface TeacherStudentDetail {
  username: string;
  overall_mastery: number;
  knowledge_nodes: Array<{
    node_id: string;
    mastery_score: number;
  }>;
  weak_nodes: TeacherWeakNode[];
}

export interface TeacherStudentTrend {
  username: string;
  trend: Array<{
    date: string;
    overall_mastery: number;
  }>;
}

export interface HeatmapNodeRow {
  node_id: string;
  avg_mastery: number;
  student_count: number;
}

export interface HeatmapResponse {
  nodes: HeatmapNodeRow[];
}

export interface UploadResponse {
  message: string;
  paths?: string[];
  error?: string;
}

export interface AdminTeacherRecord {
  username: string;
  name: string;
  email?: string;
  students: string[];
}

export interface AdminStudentPreference {
  course_type?: Array<{ name?: string }>;
}

export interface AdminStudentRecord {
  username: string;
  stu_name: string;
  email?: string;
  img?: string;
  teacher?: string;
  learning_goals?: string[];
  preference?: AdminStudentPreference;
}

export interface AdminLlmLog {
  timestamp: string;
  module?: string;
  metadata?: Record<string, unknown>;
  request?: {
    model?: string;
    messages?: Array<{ role: string; content: string }>;
  };
  response?: {
    usage?: {
      prompt_tokens?: number;
      completion_tokens?: number;
      total_tokens?: number;
    };
    choices?: Array<{
      message?: {
        content?: string;
      };
    }>;
  };
}

export interface IndustryStatusResponse {
  ok: boolean;
  messages: string[];
  countries: string[];
  cities: string[];
  city_map: Record<string, string[]>;
  sources: string[];
}

export interface IndustryTaskMeta {
  step?: number;
  current?: number;
  total?: number;
  raw_count?: number;
  title?: string;
  countries?: string[];
  parallel?: boolean;
}

export interface IndustryJob {
  title: string;
  company: string;
  salary: string;
  experience: string;
  education: string;
  location: string;
  source: string;
  description: string;
  requirements: string;
  relevance_score: number;
  relevance_reasons: string[];
  skills: string[];
  skill_evidence: Array<{ name?: string; evidence?: string }>;
  market_country?: string;
}

export interface IndustryChartRow {
  name: string;
  value: number;
}

export interface IndustryResult {
  jobs: IndustryJob[];
  metrics: {
    jobs_total: number;
    jobs_analyzed: number;
    skills_total: number;
    sources_total: number;
  };
  summary: Record<string, unknown>;
  raw_count: number;
  source_counts: Record<string, number>;
  relevance_summary: {
    input_count?: number;
    requested_count?: number;
    threshold?: number;
    threshold_kept_count?: number;
    selected_count?: number;
    dropped_count?: number;
    backfilled_count?: number;
    strict_threshold?: boolean;
    fetch_rounds?: number;
    final_fetch_limit?: number;
    max_fetch_limit?: number;
    completed_target?: boolean;
    country?: string;
    city?: string;
    search_terms?: string[];
    parallel?: boolean;
    included_countries?: string[];
  };
  relevance_message: string;
  warnings: string[];
  charts: {
    skill_ranking: IndustryChartRow[];
    job_distribution: IndustryChartRow[];
    experience_distribution: IndustryChartRow[];
    education_distribution: IndustryChartRow[];
    skill_heatmap: unknown;
  };
}

export interface IndustryTask {
  task_id: string;
  task_type: "analyze" | "reanalyze";
  status: string;
  message: string;
  meta?: IndustryTaskMeta;
  result?: IndustryResult | null;
  error?: string | null;
  cancel_requested?: boolean;
}

export interface IndustryAnalyzePayload {
  keyword: string;
  country: string;
  city: string;
  include_global: boolean;
  job_limit: number;
  relevance_threshold: number;
  sources: string[];
  fetch_desc: boolean;
}

export async function fetchCurrentUser() {
  const { data } = await apiClient.get("/current-user");
  return data as {
    username: string;
    user_type: string;
    user_data: Record<string, unknown>;
  };
}

export async function loginUser(payload: {
  username: string;
  password: string;
  user_type: "student" | "teacher" | "admin";
}) {
  const { data } = await apiClient.post("/auth/login", payload);
  return data as {
    success: boolean;
    message: string;
    user: {
      username: string;
      user_type: string;
      user_data: Record<string, unknown>;
    };
  };
}

export async function logoutUser() {
  const { data } = await apiClient.post("/logout");
  return data as { success: boolean; message: string };
}

export async function updateStudentProfile(payload: {
  learning_goals?: string[];
  email?: string;
  teacher?: string;
  preference?: Record<string, unknown>;
}) {
  const { data } = await apiClient.post("/update-profile", payload);
  return data as { success: boolean; message: string };
}

export async function changeStudentPassword(payload: {
  current_password: string;
  new_password: string;
}) {
  const { data } = await apiClient.post("/change-password", payload);
  return data as { success: boolean; message: string };
}

export async function fetchStudentTwin(username: string) {
  const { data } = await apiClient.get<StudentTwinSummary>(`/digital-twin/student-profile/${encodeURIComponent(username)}`);
  return data;
}

export async function refreshStudentTwin(username: string) {
  const { data } = await apiClient.post(`/digital-twin/collect/${encodeURIComponent(username)}`);
  return data;
}

export async function fetchLanguages() {
  const { data } = await apiClient.get<string[]>("/languages");
  return data;
}

export async function fetchLearningPlans() {
  const { data } = await apiClient.get<LearningPlanFile[]>("/learning-plans");
  return data;
}

export async function createLearningPlan(payload: {
  name: string;
  goals: string;
  lang_choice: string;
  priority: string;
  deadline_days: number;
}) {
  const { data } = await apiClient.post("/learning-plan", payload);
  return data as {
    message: string;
    plan: LearningPlanEntry[];
  };
}

export async function fetchCurrentLearningPath(username: string) {
  try {
    const { data } = await apiClient.get<LearningPathResponse>(
      `/digital-twin/path/${encodeURIComponent(username)}/current`,
    );
    return data;
  } catch (error) {
    if (axios.isAxiosError(error)) {
      const detail =
        typeof error.response?.data === "string"
          ? error.response.data
          : (error.response?.data as { detail?: string } | undefined)?.detail;
      throw new Error(detail || "学习路径加载失败，请稍后重试。");
    }
    throw error;
  }
}

export async function generateLearningPath(username: string) {
  try {
    const { data } = await apiClient.post<LearningPathResponse>(
      `/digital-twin/path/generate/${encodeURIComponent(username)}`,
      undefined,
    );
    return data;
  } catch (error) {
    if (axios.isAxiosError(error)) {
      if (error.code === "ECONNABORTED") {
        throw new Error("个性化学习路径重新规划超时，请稍后重试。若持续较慢，我可以继续帮你优化后端生成速度。");
      }
      const detail =
        typeof error.response?.data === "string"
          ? error.response.data
          : (error.response?.data as { detail?: string } | undefined)?.detail;
      throw new Error(detail || "个性化学习路径生成失败，请稍后重试。");
    }
    throw error;
  }
}

export async function fetchKnowledgeGraph() {
  const { data } = await apiClient.get<KnowledgeGraphResponse>("/knowledge-graph");
  return data;
}

export async function fetchGraphVisualization() {
  const { data } = await apiClient.get<GraphVisualizationResponse>("/graph-visualization");
  return data;
}

export async function fetchLearningProgress() {
  const { data } = await apiClient.get<LearningProgressResponse>("/learning-progress");
  return data;
}

export async function uploadTeacherResources(nodeName: string, files: File[]) {
  const formData = new FormData();
  files.forEach((file) => formData.append("files", file));
  formData.append("node_name", nodeName);
  const { data } = await apiClient.post<UploadResponse>("/upload", formData, {
    headers: { "Content-Type": "multipart/form-data" },
  });
  return data;
}

export async function deleteTeacherResource(nodeName: string, resourceIndex: number) {
  const { data } = await apiClient.post<{ success: boolean; message: string }>("/delete-resource", {
    node_name: nodeName,
    resource_index: resourceIndex,
  });
  return data;
}

export async function fetchClassOverview() {
  const { data } = await apiClient.get<ClassOverviewResponse>("/dashboard/class-overview");
  return data;
}

export async function fetchTeacherStudentDetail(username: string) {
  const { data } = await apiClient.get<TeacherStudentDetail>(`/dashboard/student/${encodeURIComponent(username)}`);
  return data;
}

export async function fetchTeacherStudentTrend(username: string) {
  const { data } = await apiClient.get<TeacherStudentTrend>(`/dashboard/student/${encodeURIComponent(username)}/trend`);
  return data;
}

export async function fetchTeacherStudents() {
  const { data } = await apiClient.get<Array<Record<string, unknown>>>("/students");
  return data;
}

export async function fetchTeacherHeatmap() {
  const { data } = await apiClient.get<HeatmapResponse>("/heatmap");
  return data;
}

export async function fetchAdminTeachers() {
  const { data } = await apiClient.get<AdminTeacherRecord[]>("/teachers");
  return data;
}

export async function fetchAdminStudents() {
  const { data } = await apiClient.get<AdminStudentRecord[]>("/students");
  return data;
}

export async function fetchAdminLlmLogs() {
  const { data } = await apiClient.get<AdminLlmLog[]>("/llm-logs");
  return data;
}

export async function selectPdfForChat(pdfPath: string) {
  const { data } = await apiClient.post("/pdf/select", { pdf_path: pdfPath });
  return data as { success: boolean; pdf_path: string };
}

export async function sendCourseChat(payload: {
  message: string;
  history: Array<[string, string]>;
  lang_choice?: string;
}) {
  try {
    const { data } = await apiClient.post<ChatResponse>(
      "/chat",
      {
        message: payload.message,
        history: payload.history,
        lang_choice: payload.lang_choice ?? "auto",
      },
    );
    return data;
  } catch (error) {
    if (axios.isAxiosError(error)) {
      if (error.code === "ECONNABORTED") {
        throw new Error("AI 助教响应超时，请稍后重试，或换一个更短的问题。");
      }
      const detail =
        typeof error.response?.data === "string"
          ? error.response.data
          : (error.response?.data as { detail?: string } | undefined)?.detail;
      throw new Error(detail || "AI 助教暂时不可用，请稍后重试。");
    }
    throw error;
  }
}

export async function generateCourseSummary(topic: string) {
  const { data } = await apiClient.post<SummaryResponse>("/summary", {
    topic,
    lang_choice: "auto",
  });
  return data;
}

export async function startQuiz(payload: { subject: string; lang_choice?: string }) {
  const { data } = await apiClient.post<QuizStartResponse>(
    "/quiz/start",
    {
      subject: payload.subject,
      lang_choice: payload.lang_choice ?? "auto",
    },
  );
  return data;
}

export async function answerQuiz(payload: { choice: string; state: QuizState }) {
  const { data } = await apiClient.post<QuizAnswerResponse>("/quiz/answer", payload);
  return data;
}

export async function generateQuizSummary(payload: {
  topic: string;
  score: number;
  total: number;
  user_answers: Array<Record<string, unknown>>;
  questions: Array<Record<string, unknown>>;
}) {
  const { data } = await apiClient.post<QuizSummaryResponse>("/quiz/summary", payload);
  return data;
}

export async function generateLearningPlanFromQuiz(payload: {
  name: string;
  state: QuizState;
  lang_choice?: string;
}) {
  const { data } = await apiClient.post<{ message: string; plan: LearningPlanEntry[] }>("/learning-plan/from-quiz", {
    name: payload.name,
    state: payload.state,
    lang_choice: payload.lang_choice ?? "auto",
  });
  return data;
}

export async function completeQuiz(payload: { node_name: string; score: number; total: number }) {
  const { data } = await apiClient.post<{ success: boolean; message?: string; passed?: boolean }>("/quiz/complete", payload);
  return data;
}

export async function fetchIndustryStatus() {
  const { data } = await apiClient.get<IndustryStatusResponse>("/industry-intelligence/status");
  return data;
}

export async function fetchCurrentIndustryTask() {
  const { data } = await apiClient.get<{ task: IndustryTask | null }>("/industry-intelligence/current");
  return data.task;
}

export async function fetchIndustryTask(taskId: string) {
  const { data } = await apiClient.get<IndustryTask>(`/industry-intelligence/tasks/${encodeURIComponent(taskId)}`);
  return data;
}

export async function startIndustryAnalysis(payload: IndustryAnalyzePayload) {
  const { data } = await apiClient.post<{ success: boolean; task_id: string }>("/industry-intelligence/analyze", payload);
  return data;
}

export async function reanalyzeIndustryJobs(jobs: IndustryJob[]) {
  const { data } = await apiClient.post<{ success: boolean; task_id: string }>("/industry-intelligence/reanalyze", {
    jobs,
  });
  return data;
}

export async function cancelIndustryTask(taskId: string) {
  const { data } = await apiClient.post<{ success: boolean; task: IndustryTask }>(
    `/industry-intelligence/tasks/${encodeURIComponent(taskId)}/cancel`,
  );
  return data;
}
