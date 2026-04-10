import {DashboardStudentSummary} from "../api/client";

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

export interface UploadResponse {
    message: string;
    paths?: string[];
    error?: string;
}

export interface TeacherTwinDimension {
    code: string;
    name: string;
    score: number;
    sub_items: Record<string, unknown>;
}

export interface TeacherTwinSummary {
    teacher_username: string;
    teacher_name: string;
    last_updated: string;
    overall_score: number;
    radar: Array<{ name: string; value: number }>;
    dimensions: TeacherTwinDimension[];
    teaching_strategy_suggestions: Array<{ dimension: string; advice: string }>;
    intervention_suggestions: Array<{ trigger: string; action: string }>;
    student_scope: {
        student_count: number;
        students_with_twin: number;
        students: string[];
    };
    missing_data_hooks: Array<{
        field: string;
        source: string;
        status: string;
        note: string;
    }>;
    data_sources: string[];
}
