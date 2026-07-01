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
    stage?: string | null;
    effectiveness_score?: number | null;
    completion_rate?: number | null;
    interaction_count?: number | null;
    valid_interaction_count?: number | null;
    mastery_update_policy?: string | null;
    summary?: string;
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

export interface QuizDefinitionQuestion {
    topic?: string | null;
    question: string;
    correct: string;
}

export interface QuizDefinition {
    definition_id: string;
    course_id: string;
    node_id: string;
    title: string;
    status: "draft" | "published" | string;
    questions: QuizDefinitionQuestion[];
    created_by?: string | null;
    created_at?: string | null;
    updated_by?: string | null;
    updated_at?: string | null;
    published_at?: string | null;
    version_no?: number;
}

export interface CourseCareerPosition {
    position_id: number;
    course_id: string;
    position_name: string;
    position_type?: string | null;
    target_rank?: number;
    source_keyword?: string | null;
}

export interface CourseCareerAbility {
    ability_id: number;
    position_id: number;
    position_name?: string | null;
    ability_name: string;
    ability_category?: string | null;
    demand_level?: string | null;
    support_level?: string | null;
    source_evidence?: Record<string, unknown>;
}

export interface CourseAbilityMapping {
    mapping_id: number;
    course_id: string;
    node_id: string;
    node_name?: string | null;
    node_path?: string[];
    ability_id: number;
    ability_name: string;
    ability_category?: string | null;
    position_id: number;
    position_name: string;
    position_type?: string | null;
    support_weight?: number;
    support_level?: string | null;
    match_reason?: string | null;
    evidence?: Record<string, unknown>;
    review_status: string;
    reviewed_by?: number | null;
    reviewed_at?: string | null;
    created_at?: string | null;
    updated_at?: string | null;
}

export interface CourseAbilityMappingCandidateResult {
    course_id: string;
    generated: number;
    rejected?: Array<Record<string, unknown>>;
    skipped?: Array<Record<string, unknown>>;
    candidate_count?: number;
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

export interface CourseStructureUpsertResponse {
    success: boolean;
    course_id: string;
    lifecycle_status: string;
    validation: {
        node_count: number;
        leaf_node_count: number;
        max_depth: number;
    };
    sync_result: {
        nodes: number;
        resources: number;
    };
    summary: CourseDigitalTwinSummary;
}

export interface CourseRuntimeEvaluationMetricMap {
    total_nodes?: number;
    total_leaf_nodes?: number;
    structure_complete_nodes?: number;
    structure_score?: number;
    valid_resource_nodes?: number;
    resource_coverage_rate?: number;
    resource_event_nodes?: number;
    resource_click_rate?: number;
    resource_completion_rate?: number;
    resource_avg_progress_percent?: number;
    resource_score?: number;
    published_quiz_definition_nodes?: number;
    published_quiz_definition_coverage_rate?: number;
    valid_quiz_nodes?: number;
    valid_assessment_nodes?: number;
    assessment_coverage_rate?: number;
    assessment_score?: number;
    mastery_score?: number;
    total_abilities?: number;
    supported_abilities?: number;
    ability_support_rate?: number;
    ability_score?: number;
    course_health_score?: number;
    [key: string]: unknown;
}

export interface CourseRuntimeNodeIssue {
    node_id?: string | null;
    node_name?: string | null;
    node_path?: string[];
    issue_type?: string;
    missing_categories?: string[];
    resource_count?: number;
    valid_resource_count?: number;
    quiz_participant_count?: number;
    required_participant_count?: number;
    quiz_attempt_count?: number;
    risk_level?: string;
    k_risk?: number;
    avg_mastery?: number | null;
    avg_quiz_percent?: number | null;
    avg_study_minutes?: number | null;
    reason?: string;
    suggested_action?: string;
    [key: string]: unknown;
}

export interface CourseRuntimeChapterRisk {
    chapter?: string;
    high_risk_node_count?: number;
    evidence_sufficient_node_count?: number;
    chapter_risk_rate?: number;
    reason?: string;
    suggested_action?: string;
    [key: string]: unknown;
}

export interface CourseRuntimeAbilityGap {
    ability_id?: number;
    ability_name?: string | null;
    position_id?: number;
    position_name?: string | null;
    position_type?: string | null;
    gap_type?: string;
    a_sup?: number | null;
    missing_mastery_nodes?: string[];
    reason?: string;
    suggested_action?: string;
    [key: string]: unknown;
}

export interface CourseRuntimeActionItem {
    type: string;
    priority: "high" | "medium" | "low" | string;
    title: string;
    count: number;
}

export interface CourseRuntimeUnavailableMetric {
    metric: string;
    reason: string;
    required_data?: string;
}

export interface CourseRuntimeEvaluation {
    course_id: string;
    course_name: string;
    lifecycle_status: string;
    published_at?: string | null;
    published_by?: string | null;
    formula_version?: string;
    window_days: number;
    min_quiz_attempts: number;
    observed_class_size?: number;
    required_participant_count?: number;
    metrics: CourseRuntimeEvaluationMetricMap;
    sections: {
        structure_quality?: {
            score?: number;
            issues?: CourseRuntimeNodeIssue[];
        };
        resource_coverage_and_effectiveness?: {
            score?: number;
            resource_gaps?: CourseRuntimeNodeIssue[];
            resource_quality_issues?: CourseRuntimeNodeIssue[];
            resource_learning_events?: Record<string, unknown>;
        };
        assessment_evidence_and_learning_effect?: {
            score?: number;
            knowledge_point_evidence_gaps?: CourseRuntimeNodeIssue[];
            chapter_practice_stats?: Array<Record<string, unknown>>;
            chapter_practice_gaps?: Array<Record<string, unknown>>;
            homework_coverage_by_node?: Record<string, unknown>;
        };
        runtime_weak_points?: {
            risk_nodes?: CourseRuntimeNodeIssue[];
            chapter_risks?: CourseRuntimeChapterRisk[];
        };
        career_ability_support?: {
            score?: number;
            ability_results?: Array<Record<string, unknown>>;
            ability_gaps?: CourseRuntimeAbilityGap[];
        };
        [key: string]: unknown;
    };
    formulas?: Record<string, string>;
    thresholds?: Record<string, string>;
    unavailable_metrics?: CourseRuntimeUnavailableMetric[];
    action_items?: CourseRuntimeActionItem[];
    generated_at?: string | null;
}
