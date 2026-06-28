export type AssignmentType = "subjective" | "objective" | "choice" | "code";
export type ObjectiveResultMode = "immediate" | "manual_review";

export type CodeLanguage = "python" | "cpp" | "java";

export interface HomeworkTestCase {
  input: string;
  expected?: string;
  output?: string;
  weight?: number;
  is_file_io?: boolean;
}

export interface HomeworkAnswerItem {
  question_index: number;
  answer: string;
  language?: CodeLanguage;
}

export interface JudgeCaseDetail {
  case: number;
  ok: boolean;
  status?: string;
  input: string;
  expected: string;
  actual: string;
  stderr?: string;
  weight?: number;
  score?: number;
  is_file_io?: boolean;
  exit_code?: number;
  time_ms?: number;
  memory_kb?: number;
}

export interface JudgeReport {
  language?: string;
  passed: number;
  total: number;
  earned_score?: number;
  total_score?: number;
  score_rate?: number;
  details: JudgeCaseDetail[];
}

export interface HomeworkQuestion {
  title: string;
  prompt: string;
  options?: string[];
  correct_answer?: string;
  reference_answer?: string;
  rubric?: string;
  test_cases?: HomeworkTestCase[];
}

export interface HomeworkAssignment {
  id: string;
  title: string;
  description: string;
  assignment_type: AssignmentType;
  class_name: string;
  course_id: string;
  node_id: string;
  node_name: string;
  node_path: string[];
  chapter_context: string;
  objective_result_mode?: ObjectiveResultMode;
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
  answers: HomeworkAnswerItem[];
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
  course_id?: string;
  node_id?: string;
  node_name?: string;
  node_path?: string[];
  chapter_context?: string;
  objective_result_mode?: ObjectiveResultMode;
}

export interface HomeworkDraftResponse {
  ok: boolean;
  draft: {
    title: string;
    description: string;
    assignment_type: AssignmentType;
    course_id: string;
    node_id: string;
    node_name: string;
    node_path: string[];
    chapter_context: string;
    objective_result_mode?: ObjectiveResultMode;
    due_at?: string | null;
    allow_late: boolean;
    total_score: number;
    rubric: string;
    questions: HomeworkQuestion[];
  };
  generated_at: string;
  message?: string;
}

export interface HomeworkCourseNode {
  node_id: string;
  node_name: string;
  node_path: string[];
  depth: number;
}
