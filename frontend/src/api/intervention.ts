import { apiClient } from "./client";
import type {
  InterventionDiagnosis,
  InterventionPackage,
  InterventionTaskReferenceOptions,
  TeacherInterventionStudentOverview,
} from "../types/intervention";

export async function interventionTeacherStudentsOverview() {
  const { data } = await apiClient.get<{
    success: boolean;
    data: { teacher_username: string; students: TeacherInterventionStudentOverview[] };
  }>("/api/intervention/teacher/students-overview");
  return data;
}

export async function interventionTeacherDiagnose(studentUsernames: string[] = []) {
  const { data } = await apiClient.post<{
    success: boolean;
    data: { teacher_username: string; diagnosis: InterventionDiagnosis[] };
  }>("/api/intervention/teacher/diagnose", { student_usernames: studentUsernames });
  return data;
}

export async function interventionGenerateDraft(payload: {
  student_username: string;
  question_count?: number;
  difficulty?: string;
}) {
  const { data } = await apiClient.post<{ success: boolean; package: InterventionPackage }>(
    "/api/intervention/teacher/generate-draft",
    payload,
  );
  return data;
}

export async function interventionListTeacherPackages() {
  const { data } = await apiClient.get<{ success: boolean; packages: InterventionPackage[] }>(
    "/api/intervention/teacher/packages",
  );
  return data;
}

export async function interventionTeacherPackageDetail(packageId: string) {
  const { data } = await apiClient.get<{ success: boolean; package: InterventionPackage }>(
    `/api/intervention/teacher/packages/${encodeURIComponent(packageId)}`,
  );
  return data;
}

export async function interventionUpdateTeacherPackage(
  packageId: string,
  payload: {
    strategy_summary: string;
    recommended_concepts: string[];
    recommended_videos: string[];
    resource_tasks?: Array<{
      id?: string;
      resource_id?: number | null;
      title: string;
      resource_path?: string;
      resource_type?: string;
      node_id?: string;
      required?: boolean;
    }>;
    assignment_tasks?: Array<{
      id?: string;
      assignment_id: string;
      title: string;
      course_id?: string;
      node_id?: string;
      required?: boolean;
    }>;
    quiz_tasks?: Array<{
      id?: string;
      quiz_id: string;
      title: string;
      course_id?: string;
      node_id?: string;
      required?: boolean;
    }>;
    code_tasks?: Array<{
      id?: string;
      task_id: string;
      title: string;
      course_id?: string;
      node_id?: string;
      required?: boolean;
    }>;
    questions: Array<{
      id?: string;
      title: string;
      prompt: string;
      question_type: "fill_blank" | "single_choice" | "multiple_choice" | "code" | "subjective";
      options?: string[];
      correct_answer?: string;
      reference_answer: string;
      rubric: string;
      test_cases?: Array<{ input: string; expected: string }>;
      difficulty: string;
    }>;
  },
) {
  const { data } = await apiClient.put<{ success: boolean; package: InterventionPackage }>(
    `/api/intervention/teacher/packages/${encodeURIComponent(packageId)}`,
    payload,
  );
  return data;
}

export async function interventionPushTeacherPackage(packageId: string) {
  const { data } = await apiClient.post<{ success: boolean; package: InterventionPackage }>(
    `/api/intervention/teacher/packages/${encodeURIComponent(packageId)}/push`,
  );
  return data;
}

export async function interventionTeacherProgress() {
  const { data } = await apiClient.get<{
    success: boolean;
    rows: Array<{
      package_id: string;
      student_username: string;
      student_status: string;
      completion_rate: number;
      answered_questions?: number;
      total_questions?: number;
      completed_structured_tasks?: number;
      total_structured_tasks?: number;
      completed_items?: number;
      total_items?: number;
      student_note?: string;
      average_final_score?: number | null;
      average_ai_score?: number | null;
      average_teacher_score?: number | null;
      updated_at: string;
      pushed_at?: string;
    }>;
  }>("/api/intervention/teacher/progress");
  return data;
}

export async function interventionTaskReferenceOptions(courseId = "course_big_data") {
  const { data } = await apiClient.get<{ success: boolean; options: InterventionTaskReferenceOptions }>(
    "/api/intervention/teacher/task-reference-options",
    { params: { course_id: courseId } },
  );
  return data;
}

export async function interventionTeacherGradeQuestion(
  packageId: string,
  payload: { question_id: string; teacher_score: number; teacher_comment?: string },
) {
  const { data } = await apiClient.post<{ success: boolean; package: InterventionPackage }>(
    `/api/intervention/teacher/packages/${encodeURIComponent(packageId)}/grade`,
    payload,
  );
  return data;
}

export async function interventionStudentPackages() {
  const { data } = await apiClient.get<{ success: boolean; packages: InterventionPackage[] }>(
    "/api/intervention/student/packages",
  );
  return data;
}

export async function interventionStudentPackageDetail(packageId: string) {
  const { data } = await apiClient.get<{ success: boolean; package: InterventionPackage }>(
    `/api/intervention/student/packages/${encodeURIComponent(packageId)}`,
  );
  return data;
}

export async function interventionStudentDecision(
  packageId: string,
  payload: { decision: "accepted" | "declined"; note?: string },
) {
  const { data } = await apiClient.post<{ success: boolean; package: InterventionPackage }>(
    `/api/intervention/student/packages/${encodeURIComponent(packageId)}/decision`,
    payload,
  );
  return data;
}

export async function interventionStudentProgress(
  packageId: string,
  payload: { status: "in_progress" | "completed"; completion_rate: number; note?: string },
) {
  const { data } = await apiClient.post<{ success: boolean; package: InterventionPackage }>(
    `/api/intervention/student/packages/${encodeURIComponent(packageId)}/progress`,
    payload,
  );
  return data;
}

export async function interventionStudentUpdateTask(
  packageId: string,
  payload: {
    task_type: "resource" | "assignment" | "quiz" | "code";
    task_id: string;
    completed: boolean;
    note?: string;
  },
) {
  const { data } = await apiClient.post<{ success: boolean; package: InterventionPackage }>(
    `/api/intervention/student/packages/${encodeURIComponent(packageId)}/tasks`,
    payload,
  );
  return data;
}

export async function interventionStudentSaveAnswer(
  packageId: string,
  payload: { question_id: string; answer: string; note?: string },
) {
  const { data } = await apiClient.post<{ success: boolean; package: InterventionPackage }>(
    `/api/intervention/student/packages/${encodeURIComponent(packageId)}/answers`,
    payload,
  );
  return data;
}

