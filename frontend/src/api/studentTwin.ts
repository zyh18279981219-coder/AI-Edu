import { apiClient, completeQuiz } from "./client";
import { fetchCurrentUser, logoutUser } from "./login";
import { generateLearningPlanFromQuiz } from "./student";

import type {
  AdminLlmLog,
  AdminStudentRecord,
  AdminTeacherRecord,
  QuizAnswerResponse,
  QuizQuestion,
  QuizStartResponse,
  QuizState,
  QuizSummaryResponse,
} from "./client";
import type { LearningPlanEntry } from "../types/student";
import type { IndustryChartRow, IndustryJob, IndustryResult } from "../types/industry";

export type {
  AdminLlmLog,
  AdminStudentRecord,
  AdminTeacherRecord,
  IndustryChartRow,
  IndustryJob,
  IndustryResult,
  LearningPlanEntry,
  QuizQuestion,
  QuizState,
};

export { fetchCurrentUser, logoutUser, completeQuiz, generateLearningPlanFromQuiz };

export async function fetchAdminTeachers() {
  const { data } = await apiClient.get<AdminTeacherRecord[]>("/api/teachers");
  return data;
}

export async function fetchAdminStudents() {
  const { data } = await apiClient.get<AdminStudentRecord[]>("/api/students");
  return data;
}

export async function fetchAdminLlmLogs() {
  const { data } = await apiClient.get<AdminLlmLog[]>("/api/llm-logs");
  return data;
}

export async function startQuiz(payload: { subject: string; lang_choice?: string }) {
  const { data } = await apiClient.post<QuizStartResponse>("/api/quiz/start", {
    subject: payload.subject,
    lang_choice: payload.lang_choice ?? "auto",
  });
  return data;
}

export async function answerQuiz(payload: { choice: string; state: QuizState }) {
  const { data } = await apiClient.post<QuizAnswerResponse>("/api/quiz/answer", payload);
  return data;
}

export async function generateQuizSummary(payload: {
  topic: string;
  score: number;
  total: number;
  user_answers: Array<Record<string, unknown>>;
  questions: Array<Record<string, unknown>>;
}) {
  const { data } = await apiClient.post<QuizSummaryResponse>("/api/quiz/summary", payload);
  return data;
}

