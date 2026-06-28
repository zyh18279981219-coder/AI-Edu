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
    mastery_score: number;
    priority: number;
    llm_priority?: number | null;
    sequence_order?: number;
    item_type?: string;
    source?: string;
    evidence_level?: string;
    suggested_actions?: string[];
    resources?: LearningPathResource[];
}

export type LearningPathNodeStatusValue = "pending" | "in_progress" | "completed" | "skipped" | string;

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
    status?: string;
    message?: string;
    generated_at?: string;
    llm_advice?: string;
    llm_order_reason?: string;
    weak_nodes?: LearningPathNode[];
    formal_path_nodes?: LearningPathNode[];
    path_node_status?: LearningPathNodeStatus[];
}

export interface DiagnosisEvidenceTimelineItem {
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
    risk_alerts: RiskAlert[];
    trend: {
        trend_status: string;
        change: number;
        summary: string;
        points: TrendPoint[];
    };
    node_summary: {
        total_nodes: number;
        weak_node_count: number;
        strong_node_count: number;
        average_progress: number;
        average_quiz_score: number;
    };
}
