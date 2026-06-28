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
    evidence_level?: string;
    confidence?: number;
    reason_type?: string;
    teacher_explanation?: string;
    suggested_actions?: string[];
    latest_evidence_at?: string | null;
}

export interface TeacherDiagnosisEvidenceTimelineItem {
    type: "quiz" | "homework" | "resource_learning" | string;
    node_id?: string | null;
    occurred_at?: string | null;
    score?: number;
    total?: number;
    passed?: boolean;
    title?: string | null;
    assignment_type?: string | null;
    status?: string | null;
    resource_id?: number | null;
    resource_path?: string | null;
    event_type?: string | null;
    duration_seconds?: number;
    progress_percent?: number;
    is_completed?: boolean;
}

export interface TeacherStudentDiagnosisSummary {
    report_id?: string;
    course_id?: string;
    evidence_level?: string;
    confidence?: number;
    persona_summary?: string;
    weak_nodes?: TeacherWeakNode[];
    evidence_timeline?: TeacherDiagnosisEvidenceTimelineItem[];
    manual_correction_supported?: boolean;
}

export interface TeacherStudentDetail {
    username: string;
    overall_mastery: number;
    knowledge_nodes: Array<{
        node_id: string;
        mastery_score: number;
    }>;
    weak_nodes: TeacherWeakNode[];
    diagnosis?: TeacherStudentDiagnosisSummary | null;
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
    suggestion_generation: {
        mode: string;
        is_ai_generated: boolean;
        note: string;
    };
    data_diagnosis: {
        external_metrics_present: string[];
        external_metrics_missing: string[];
        external_coverage_ratio: number;
        summary: string;
    };
    missing_data_hooks: Array<{
        field: string;
        source: string;
        status: string;
        note: string;
    }>;
    data_sources: string[];
}

export interface TeacherTwinAiSuggestionsResponse {
    mode: string;
    is_ai_generated: boolean;
    teaching_strategy_suggestions: Array<{ dimension: string; advice: string }>;
    intervention_suggestions: Array<{ trigger: string; action: string }>;
    message?: string;
}

export interface TeacherTwinDrilldownResponse {
    teacher_username: string;
    dimension: {
        code: string;
        name: string;
        score: number;
        sub_items: Record<string, unknown>;
    };
    window_days: number;
    coverage_ratio: number;
    evidence_count: number;
    evidence_items: Array<{
        event_type: string;
        created_at: string;
        student_username?: string | null;
        target_id?: string | null;
        summary: string;
        payload: Record<string, unknown>;
    }>;
}

export interface CourseDigitalTwinSummary {
    course_id: string;
    course_name: string;
    description?: string | null;
    lifecycle_status: "draft" | "published" | "archived" | string;
    published_at?: string | null;
    published_by?: string | null;
    created_at?: string | null;
    updated_at?: string | null;
    node_count: number;
    leaf_node_count?: number;
    resource_count: number;
    enabled_resource_count?: number;
    external_resource_count?: number;
    pending_or_disabled_resource_count?: number;
}

export interface CourseGraphNode {
    name?: string;
    node_id?: string;
    id?: string;
    resource_path?: string | string[];
    children?: CourseGraphNode[];
    grandchildren?: CourseGraphNode[];
    "great-grandchildren"?: CourseGraphNode[];
    [key: string]: unknown;
}

export interface CourseDigitalTwinResource {
    resource_id: number;
    course_id: string;
    node_id: string;
    node_name?: string | null;
    resource_path: string;
    resource_type?: string | null;
    title?: string | null;
    resource_source: string;
    quality_status: string;
    review_status: string;
    is_enabled: boolean;
    is_deleted: boolean;
    created_at?: string | null;
    updated_at?: string | null;
}

export interface CourseInitialGraphResponse {
    success: boolean;
    course_id: string;
    lifecycle_status: string;
    graph_data: CourseGraphNode;
    validation: {
        node_count: number;
        leaf_node_count: number;
        max_depth: number;
    };
    resource_bind_result?: {
        leaf_nodes: number;
        attached_resources: number;
        skipped_leaf_nodes: number;
    } | null;
    review_marked_count: number;
    sync_result: {
        nodes: number;
        resources: number;
    };
    summary: CourseDigitalTwinSummary;
}

export interface CourseResourceBindResponse {
    success: boolean;
    course_id: string;
    graph_data: CourseGraphNode;
    bind_result: {
        leaf_nodes: number;
        attached_resources: number;
        skipped_leaf_nodes: number;
    };
    review_marked_count: number;
    sync_result: {
        nodes: number;
        resources: number;
    };
    summary: CourseDigitalTwinSummary;
    resources: CourseDigitalTwinResource[];
}
