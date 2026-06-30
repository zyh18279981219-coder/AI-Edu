import type { DiagnosisEvidenceTimelineItem } from "./student";

export interface InterventionWeakNode {
  node_id: string;
  mastery_score: number;
  progress: number;
  quiz_score?: number | null;
  reason: string;
}

export interface InterventionDiagnosis {
  student_username: string;
  overall_mastery: number;
  weak_nodes: InterventionWeakNode[];
  diagnosis_report_id?: string | null;
  evidence_level?: string | null;
  confidence?: number | null;
  evidence_timeline?: DiagnosisEvidenceTimelineItem[];
  homework_snapshot: {
    submission_count: number;
    graded_count: number;
    average_score?: number | null;
  };
}

export interface InterventionQuestion {
  id: string;
  title: string;
  prompt: string;
  question_type: "fill_blank" | "single_choice" | "multiple_choice" | "code" | "subjective";
  options?: string[];
  correct_answer?: string;
  reference_answer: string;
  rubric: string;
  test_cases?: Array<{ input: string; expected: string }>;
  difficulty: string;
}

export interface InterventionQuestionAnswer {
  question_id: string;
  question_title: string;
  question_type?: "fill_blank" | "single_choice" | "multiple_choice" | "code" | "subjective";
  answer: string;
  note?: string;
  status: "pending" | "completed";
  updated_at: string;
}

export interface InterventionQuestionGrade {
  question_id: string;
  question_title: string;
  question_type?: "fill_blank" | "single_choice" | "multiple_choice" | "code" | "subjective";
  ai_score?: number | null;
  ai_feedback?: string;
  ai_detail?: {
    total_score: number;
    criteria: Array<{ name: string; score: number; full_score: number; reason: string }>;
    match?: {
      normalized_answer: string;
      expected: string;
      is_correct: boolean;
    };
    code?: {
      case_passed: number;
      case_total: number;
      case_details: Array<{ index: number; ok: boolean; input: string; expected: string; actual: string; reason: string }>;
    };
  };
  teacher_score?: number | null;
  teacher_comment?: string;
  final_score?: number | null;
  status: string;
  ai_graded_at?: string | null;
  teacher_graded_at?: string | null;
  updated_at: string;
}

export interface InterventionResourceTask {
  id?: string;
  resource_id?: number | null;
  title: string;
  resource_path?: string;
  resource_type?: string;
  node_id?: string;
  required?: boolean;
  status?: "pending" | "completed";
  completed_at?: string;
  note?: string;
}

export interface InterventionAssignmentTask {
  id?: string;
  assignment_id: string;
  title: string;
  course_id?: string;
  node_id?: string;
  required?: boolean;
  status?: "pending" | "completed";
  completed_at?: string;
  note?: string;
}

export interface InterventionQuizTask {
  id?: string;
  quiz_id: string;
  title: string;
  course_id?: string;
  node_id?: string;
  required?: boolean;
  status?: "pending" | "completed";
  completed_at?: string;
  note?: string;
}

export interface InterventionCodeTask {
  id?: string;
  task_id: string;
  title: string;
  course_id?: string;
  node_id?: string;
  required?: boolean;
  status?: "pending" | "completed";
  completed_at?: string;
  note?: string;
}

export interface InterventionPackage {
  id: string;
  teacher_username: string;
  student_username: string;
  stage?: "draft" | "pushed";
  strategy_summary: string;
  recommended_concepts: string[];
  recommended_videos: string[];
  resource_tasks?: InterventionResourceTask[];
  assignment_tasks?: InterventionAssignmentTask[];
  quiz_tasks?: InterventionQuizTask[];
  code_tasks?: InterventionCodeTask[];
  questions: InterventionQuestion[];
  diagnosis: InterventionDiagnosis;
  student_status: "pending" | "accepted" | "declined" | "in_progress" | "completed";
  student_note?: string;
  answers?: InterventionQuestionAnswer[];
  grades?: InterventionQuestionGrade[];
  score_summary?: {
    question_count: number;
    graded_questions: number;
    average_final_score?: number | null;
    average_ai_score?: number | null;
    average_teacher_score?: number | null;
    updated_at: string;
  };
  progress?: {
    completion_rate: number;
    answered_questions?: number;
    total_questions?: number;
    completed_structured_tasks?: number;
    total_structured_tasks?: number;
    completed_items?: number;
    total_items?: number;
    status: string;
    updated_at: string;
  };
  created_at: string;
  updated_at: string;
  pushed_at?: string | null;
}

export interface InterventionTaskReferenceOptions {
  course_id: string;
  resources: Array<{
    resource_id: number;
    course_id: string;
    node_id: string;
    node_name?: string | null;
    title?: string | null;
    resource_path: string;
    resource_type?: string | null;
  }>;
  assignments: Array<{
    assignment_id: string;
    task_id?: string;
    title: string;
    course_id: string;
    node_id: string;
    node_name?: string | null;
    assignment_type: string;
    status: string;
  }>;
  quizzes: Array<{
    definition_id: string;
    quiz_id: string;
    title: string;
    course_id: string;
    node_id: string;
    status: string;
    question_count?: number;
    published_at?: string | null;
    updated_at?: string | null;
  }>;
  code_tasks: Array<{
    assignment_id: string;
    task_id: string;
    title: string;
    course_id: string;
    node_id: string;
    node_name?: string | null;
    assignment_type: string;
    status: string;
  }>;
}

export interface TeacherInterventionStudentOverview {
  student_username: string;
  student_user_id?: number;
  overall_mastery: number;
  weak_node_count: number;
  weak_nodes_preview: InterventionWeakNode[];
  homework_submission_count: number;
  homework_average_score?: number | null;
}

