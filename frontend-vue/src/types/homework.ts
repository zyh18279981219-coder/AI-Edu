export type AssignmentType = "subjective" | "objective" | "choice" | "code";

export interface HomeworkQuestion {
  title: string;
  prompt: string;
  options?: string[];
  correct_answer?: string;
  reference_answer?: string;
  rubric?: string;
  test_cases?: Array<Record<string, unknown>>;
}

export interface HomeworkAssignment {
  id: string;
  title: string;
  description: string;
  assignment_type: AssignmentType;
  class_name: string;
  due_at?: string | null;
  allow_late: boolean;
  total_score: number;
  rubric: string;
  questions: HomeworkQuestion[];
  created_by: string;
  created_at: string;
  status: "draft" | "published" | "closed";
}

export interface HomeworkSubmission {
  id: string;
  assignment_id: string;
  student_username: string;
  answers: Array<Record<string, unknown>>;
  submitted_at: string;
  status: "submitted" | "graded";
  ai_score?: number | null;
  ai_feedback?: string;
  ai_rationale?: string;
  teacher_score?: number | null;
  teacher_comment?: string;
  graded_at?: string | null;
  grader_username?: string;
}

export interface HomeworkQuestionGenerateRequest {
  topic: string;
  assignment_type: AssignmentType;
  count: number;
  difficulty: string;
  language: string;
  extra_requirements: string;
}

export interface HomeworkDraftRequest {
  assignment_type: AssignmentType;
  topic: string;
  difficulty: string;
  class_name: string;
}

export interface HomeworkDraftResponse {
  ok: boolean;
  draft: {
    title: string;
    description: string;
    assignment_type: AssignmentType;
    due_at?: string | null;
    allow_late: boolean;
    total_score: number;
    rubric: string;
    questions: HomeworkQuestion[];
  };
  generated_at: string;
  message?: string;
}
