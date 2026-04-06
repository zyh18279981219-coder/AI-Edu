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
