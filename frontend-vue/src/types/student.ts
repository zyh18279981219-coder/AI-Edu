import {RadarMetric, RiskAlert, TechnicalLevel, TrendPoint, WeakNode} from "../api/client";



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
    resources?: Array<{ title?: string; url: string }>;
}

export interface LearningPathResponse {
    status?: string;
    message?: string;
    generated_at?: string;
    llm_advice?: string;
    llm_order_reason?: string;
    weak_nodes?: LearningPathNode[];
}

export interface StudentTwinSummary {
    username: string;
    last_updated: string;
    overall_mastery: number;
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