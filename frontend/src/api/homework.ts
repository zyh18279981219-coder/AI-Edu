import { apiClient } from "./client";
import {
  HomeworkAnswerItem,
  HomeworkAssignment,
  HomeworkCourseNode,
  HomeworkDraftRequest,
  HomeworkDraftResponse,
  HomeworkKnowledgePointCoverage,
  HomeworkQuestion,
  HomeworkQuestionGenerateRequest,
  HomeworkSubmission,
} from "../types/homework";

export async function homeworkGenerateQuestions(payload: HomeworkQuestionGenerateRequest) {
  const { data } = await apiClient.post<{ success: boolean; questions: HomeworkQuestion[] }>(
    "/api/homework/ai/generate-questions",
    payload,
  );
  return data;
}

export async function homeworkPublishAssignment(payload: {
  title: string;
  description: string;
  assignment_type: "subjective" | "objective" | "choice" | "code";
  class_name: string;
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
  covered_knowledge_points?: HomeworkKnowledgePointCoverage[];
  publish_now?: boolean;
}) {
  const { data } = await apiClient.post<{ success: boolean; assignment: HomeworkAssignment }>(
    "/api/homework/assignments",
    payload,
  );
  return data;
}

export async function homeworkGenerateDraft(payload: HomeworkDraftRequest) {
  const { data } = await apiClient.post<{ success: boolean } & HomeworkDraftResponse>(
    "/api/homework/ai/generate-draft",
    payload,
  );
  return data;
}

export async function homeworkListAssignments(onlyMine = true) {
  const { data } = await apiClient.get<{ success: boolean; assignments: HomeworkAssignment[] }>(
    "/api/homework/assignments",
    { params: { only_mine: onlyMine } },
  );
  return data;
}

export async function homeworkListAssignmentsByFilter(payload: {
  only_mine?: boolean;
  course_id?: string;
  node_id?: string;
  node_name?: string;
}) {
  const { data } = await apiClient.get<{ success: boolean; assignments: HomeworkAssignment[] }>(
    "/api/homework/assignments",
    {
      params: {
        only_mine: payload.only_mine ?? false,
        course_id: payload.course_id,
        node_id: payload.node_id,
        node_name: payload.node_name,
      },
    },
  );
  return data;
}

export async function homeworkGetAssignment(assignmentId: string) {
  const { data } = await apiClient.get<{ success: boolean; assignment: HomeworkAssignment }>(
    `/api/homework/assignments/${encodeURIComponent(assignmentId)}`,
  );
  return data;
}

export async function homeworkUpdateAssignment(
  assignmentId: string,
  payload: {
    title: string;
    description: string;
    assignment_type: "subjective" | "objective" | "choice" | "code";
    class_name: string;
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
    covered_knowledge_points?: HomeworkKnowledgePointCoverage[];
  },
) {
  const { data } = await apiClient.put<{ success: boolean; assignment: HomeworkAssignment }>(
    `/api/homework/assignments/${encodeURIComponent(assignmentId)}`,
    payload,
  );
  return data;
}

export async function homeworkPublishStatus(assignmentId: string) {
  const { data } = await apiClient.post<{ success: boolean; assignment: HomeworkAssignment }>(
    `/api/homework/assignments/${encodeURIComponent(assignmentId)}/publish`,
  );
  return data;
}

export async function homeworkCloseStatus(assignmentId: string) {
  const { data } = await apiClient.post<{ success: boolean; assignment: HomeworkAssignment }>(
    `/api/homework/assignments/${encodeURIComponent(assignmentId)}/close`,
  );
  return data;
}

export async function homeworkReopenStatus(assignmentId: string) {
  const { data } = await apiClient.post<{ success: boolean; assignment: HomeworkAssignment }>(
    `/api/homework/assignments/${encodeURIComponent(assignmentId)}/reopen`,
  );
  return data;
}

export async function homeworkListAssignmentsForStudent() {
  return homeworkListAssignmentsByFilter({ only_mine: false });
}

export async function homeworkListAssignmentsForNode(payload: {
  course_id: string;
  node_id?: string;
  node_name?: string;
}) {
  const { data } = await apiClient.get<{ success: boolean; assignments: HomeworkAssignment[] }>(
    "/api/homework/assignments",
    {
      params: {
        only_mine: false,
        course_id: payload.course_id,
        node_id: payload.node_id,
        node_name: payload.node_name,
      },
    },
  );
  return data;
}

export async function homeworkListCourseNodes(courseId = "course_big_data") {
  const { data } = await apiClient.get<{ success: boolean; course_id: string; nodes: HomeworkCourseNode[] }>(
    "/api/homework/course-nodes",
    { params: { course_id: courseId } },
  );
  return data;
}

export async function homeworkSubmitAssignment(assignmentId: string, answers: HomeworkAnswerItem[]) {
  const { data } = await apiClient.post<{ success: boolean; submission: HomeworkSubmission }>(
    `/api/homework/assignments/${encodeURIComponent(assignmentId)}/submissions`,
    { answers },
  );
  return data;
}

export async function homeworkListMySubmissions(assignmentId?: string) {
  const { data } = await apiClient.get<{ success: boolean; submissions: HomeworkSubmission[] }>(
    "/api/homework/my-submissions",
    { params: { assignment_id: assignmentId } },
  );
  return data;
}

export async function homeworkListSubmissions(assignmentId: string) {
  const { data } = await apiClient.get<{ success: boolean; submissions: HomeworkSubmission[] }>(
    `/api/homework/assignments/${encodeURIComponent(assignmentId)}/submissions`,
  );
  return data;
}

export async function homeworkGetSubmission(submissionId: string) {
  const { data } = await apiClient.get<{
    success: boolean;
    submission: HomeworkSubmission;
    assignment: HomeworkAssignment;
  }>(`/api/homework/submissions/${encodeURIComponent(submissionId)}`);
  return data;
}

export async function homeworkAiGrade(submissionId: string) {
  const { data } = await apiClient.post<{ success: boolean; submission: HomeworkSubmission }>(
    `/api/homework/submissions/${encodeURIComponent(submissionId)}/ai-grade`,
    { force_regenerate: true },
  );
  return data;
}

export async function homeworkFinalGrade(submissionId: string, teacherScore: number, teacherComment: string) {
  const { data } = await apiClient.post<{ success: boolean; submission: HomeworkSubmission }>(
    `/api/homework/submissions/${encodeURIComponent(submissionId)}/final-grade`,
    {
      teacher_score: teacherScore,
      teacher_comment: teacherComment,
    },
  );
  return data;
}
