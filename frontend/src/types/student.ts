import {RadarMetric, RiskAlert, TechnicalLevel, TrendPoint, WeakNode} from "../api/client";
export type { CourseNode, KnowledgeGraphResponse } from "./knowledgeGraph";



export interface GraphVisualizationResponse {
    mocKgNodeDtoList: GraphVisualizationNode[];
    mocKgRelationDtoList?: GraphVisualizationRelation[];
}

export interface GraphVisualizationNode {
    id: number;
    parentId: number;
    nodeName: string;
    description?: string;
    flag?: number;
    childCount?: number;
    level?: number;
    mocKgNodeAvgStatisticsDto?: {
        avgMasteryRate?: number;
        avgCompletionRate?: number;
        avgLearnedTimeCount?: number;
    };
}

export interface GraphVisualizationRelation {
    fromNodeId: number;
    toNodeId: number;
    relationType?: number;
}

export interface LearningProgressResponse {
    chapters: LearningProgressGroup;
    sections: LearningProgressGroup;
    points: LearningProgressGroup;
}



export interface LearningProgressGroup {
    completed: number;
    total: number;
    progress: number;
}

export interface UserProfile {
    username: string;
    name: string;
    email: string;
    teacher: string;
    userType: string;
}

export interface PasswordForm {
    current_password: string;
    new_password: string;
}

export interface ProfileUpdatePayload {
    email: string;
    teacher: string;
    learning_goals: string[];
}

export interface ProfileResponse {
    message?: string;
    success?: boolean;
    detail?: string;
}

export interface UserAccount {
    username: string;
    user_type: string;
    user_data: Record<string, any>;
}

export interface LearningPlanEntry {
    date: string;
    topic: string;
    priority: string;
    materials: string[];
    deadline?: string;
}

export interface LearningPlanFile {
    filename: string;
    path: string;
    category?: string;
    updated_at?: string;
    data: LearningPlanEntry[];
}

export interface LearningPathNode {
    node_id: string;
    item_id?: string;
    title?: string;
    mastery_score: number;
    priority: number;
    llm_priority?: number | null;
    sequence_order?: number;
    item_type?: string;
    source?: string;
    evidence_level?: string;
    suggested_actions?: string[];
    resources?: LearningPathResource[];
    resource?: LearningPathResource;
    mapping_status?: string;
    reason?: string;
}

export interface LearningPathBasis {
    trigger_type?: LearningPathTriggerType | string;
    manual_goal?: string | null;
    diagnosis_report_id?: string | null;
    diagnosis_evidence_level?: string | null;
    diagnosis_confidence?: number | null;
    weak_node_count?: number;
    insufficient_node_count?: number;
    insufficient_nodes?: Array<{
        node_id: string;
        mastery_score?: number | null;
        evidence_level?: string;
        suggested_actions?: string[];
        reason?: string;
    }>;
    formal_node_rule?: string;
}

export type LearningPathNodeStatusValue = "pending" | "in_progress" | "completed" | "skipped";
export type LearningPathTriggerType =
    | "diagnosis"
    | "manual_goal"
    | "node_completed"
    | "new_course"
    | "intervention_completed";

export interface LearningPathNodeStatus {
    status_id: number;
    plan_id: number;
    plan_node_id?: number | null;
    username: string;
    user_id?: number | null;
    course_id?: string | null;
    node_id: string;
    item_type: string;
    source_type: string;
    status: LearningPathNodeStatusValue;
    mastery_before?: number | null;
    mastery_after?: number | null;
    started_at?: string | null;
    completed_at?: string | null;
    payload?: Record<string, any>;
    created_at?: string | null;
    updated_at?: string | null;
}

export interface LearningPathRefreshResult {
    triggered: boolean;
    trigger_type?: LearningPathTriggerType | string;
    path?: LearningPathResponse | null;
    error?: string | null;
}

export interface LearningPathNodeStatusUpdateResponse {
    success: boolean;
    node_status: LearningPathNodeStatus;
    path_refresh?: LearningPathRefreshResult;
    fivee_outcome?: {
        updated?: boolean;
        record_id?: number | null;
        effectiveness_score?: number | null;
        evidence_status?: string | null;
        mastery_update_policy?: string | null;
        reason?: string;
    } | null;
}

export interface LearningPathResource {
    type?: string;
    title?: string;
    url: string;
    source?: string;
    provider?: string | null;
    embed_url?: string | null;
    score?: number | null;
    reason?: string;
}

export interface LearningPathResponse {
    plan_id?: number;
    filename?: string;
    status?: string;
    message?: string;
    course_id?: string | null;
    version_no?: number;
    lifecycle_status?: string;
    trigger_type?: LearningPathTriggerType | string;
    trigger_reason?: string;
    manual_goal?: string | null;
    basis_report_id?: string | null;
    basis?: LearningPathBasis;
    generated_at?: string;
    updated_at?: string;
    llm_advice?: string;
    llm_order_reason?: string;
    weak_nodes?: LearningPathNode[];
    formal_path_nodes?: LearningPathNode[];
    supplemental_items?: LearningPathNode[];
    path_node_status?: LearningPathNodeStatus[];
}

export interface LearningPathVersionsResponse {
    versions: LearningPathResponse[];
    count: number;
}

export interface DiagnosisEvidenceTimelineItem {
    type: "quiz" | "homework" | "resource_learning" | string;
    type_label?: string;
    node_id?: string | null;
    occurred_at?: string | null;
    summary?: string;
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
    package_id?: string | null;
    teacher_username?: string | null;
    answered_questions?: number | null;
    total_questions?: number | null;
    teacher_graded?: boolean;
    stage?: string | null;
    effectiveness_score?: number | null;
    effectiveness_level?: string | null;
    evidence_status?: string | null;
    completion_rate?: number | null;
    interaction_count?: number | null;
    valid_interaction_count?: number | null;
    mastery_update_policy?: string | null;
}

export interface StudentDiagnosisEvidenceTimelineItem {
    type: "quiz" | "homework" | "resource_learning" | string;
    type_label?: string;
    node_id?: string | null;
    occurred_at?: string | null;
    title?: string | null;
    summary?: string;
    score?: number;
    total?: number;
    passed?: boolean;
    status?: string | null;
    resource_path?: string | null;
    progress_percent?: number;
    stage?: string | null;
    effectiveness_level?: string | null;
    evidence_status?: string | null;
    completion_rate?: number | null;
    mastery_update_policy?: string | null;
}

export interface StudentDiagnosisReport {
    report_id: string;
    username: string;
    user_id?: number | null;
    course_id: string;
    report_date: string;
    diagnosis_type: string;
    evidence_level: "sufficient" | "partial" | "insufficient" | string;
    confidence: number;
    persona_summary: string;
    student_view?: {
        summary?: string;
        evidence_level?: string;
        next_steps?: string[];
        evidence_timeline?: StudentDiagnosisEvidenceTimelineItem[];
    };
    teacher_view?: {
        weak_nodes?: Array<Record<string, unknown>>;
        all_nodes?: Array<Record<string, unknown>>;
        evidence_timeline?: DiagnosisEvidenceTimelineItem[];
        manual_correction_supported?: boolean;
    };
    weak_nodes?: Array<Record<string, unknown>>;
    generated_at?: string;
}

export interface StudentTwinSummary {
    username: string;
    last_updated: string;
    generated_at?: string;  // 新增：诊断生成时间
    overall_mastery: number;
    overall_risk_level?: string;  // 新增：整体风险等级 (high/medium/low)
    technical_level: TechnicalLevel;
    radar: RadarMetric[];
    weak_nodes: WeakNode[];
    chapter_practice?: ChapterPracticeEvidence[];
    knowledge_point_homework_evidence?: KnowledgePointHomeworkEvidence[];
    career_abilities?: CareerAbilityAttainment[];
    practice_summary?: {
        chapter_count: number;
        average_practice_score?: number | null;
        practice_level: string;
        coverage_node_count: number;
        coverage_evidence_count: number;
    };
    risk_alerts: RiskAlert[];
    trend: {
        trend_status: string;
        change: number;
        summary: string;
        points: TrendPoint[];
        attribution_points?: TrendAttributionPoint[];
    };
    node_summary: {
        total_nodes: number;
        weak_node_count: number;
        strong_node_count: number;
        average_progress: number;
        average_quiz_score: number;
        average_practice_score?: number | null;
        homework_coverage_node_count?: number;
    };
}

export interface TrendAttributionEvidence {
    type: string;
    node_id?: string | null;
    occurred_at?: string | null;
    title?: string | null;
    summary: string;
}

export interface TrendAttributionPoint {
    date: string;
    previous_date: string;
    previous_mastery: number;
    current_mastery: number;
    drop: number;
    evidence_level: "partial" | "insufficient" | string;
    evidence_status_label?: string;
    primary_reason?: string;
    snapshot_compare?: {
        previous?: {
            date?: string | null;
            overall_mastery?: number | null;
        };
        current?: {
            date?: string | null;
            overall_mastery?: number | null;
        };
        change?: number;
        drop?: number;
    };
    reason_summary: string;
    evidence_summary?: Array<{
        type: string;
        label: string;
        count: number;
        detail: string;
    }>;
    evidence: TrendAttributionEvidence[];
    suggested_actions: string[];
}

export interface CareerAbilityAttainment {
    ability_id: number;
    ability_name: string;
    ability_category?: string | null;
    position_id?: number | null;
    position_name?: string | null;
    position_type?: string | null;
    attainment_score: number;
    level: "待提升" | "基本达成" | "较好达成" | string;
    gap_nodes: CareerAbilityKnowledgeNode[];
}

export interface CareerAbilityKnowledgeNode {
    node_id: string;
    node_name?: string | null;
    node_path?: string[];
    mastery_score: number;
}

export interface ChapterPracticeEvidence {
    chapter: string;
    practice_score: number;
    practice_level: string;
    evidence_count: number;
    code_evidence_count: number;
    subjective_evidence_count: number;
    latest_evidence_at?: string | null;
    evidence_items?: Array<{
        assignment_id?: string;
        submission_id?: string;
        title?: string;
        assignment_type?: string;
        score_percent?: number;
        evidence_at?: string | null;
    }>;
    calculation_note?: string;
}

export interface KnowledgePointHomeworkEvidence {
    node_id: string;
    auxiliary_score: number;
    weighted_mastery_delta: number;
    evidence_count: number;
    latest_evidence_at?: string | null;
    calculation_note?: string;
}
