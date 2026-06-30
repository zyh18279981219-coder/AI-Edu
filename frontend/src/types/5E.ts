export interface ChatResponse {
    role: string,
    content: string,
    buttons?: Button[],
    resources?: Resource[],
    tests?: Test[],
    timestamp: number,
}

export interface Button {
    show_text: string,
    send_text: string,
}

export interface Resource {
    show_text: string,
    id: string,
}

export interface Test {
    show_text: string,
    id: string,
}

export interface FiveEDimensionScores {
    stage_completion?: number | null;
    valid_interaction?: number | null;
    learning_gain?: number | null;
    learning_transfer?: number | null;
}

export interface FiveEStageDistributionItem {
    stage: string;
    count: number;
}

export interface FiveELowEffectivenessNode {
    node_id: string;
    course_id?: string | null;
    student_count: number;
    record_count: number;
    avg_effectiveness_score: number;
    avg_completion_rate: number;
    avg_valid_interaction_rate: number;
    evidence_status?: string | null;
    latest_stage?: string | null;
    latest_calculated_at?: string | null;
}

export interface FiveEEffectivenessEvidence {
    record_id?: number | null;
    student_username?: string | null;
    course_id?: string | null;
    node_id?: string | null;
    stage?: string | null;
    effectiveness_score?: number | null;
    effectiveness_level?: string | null;
    evidence_status?: string | null;
    dimension_scores?: FiveEDimensionScores;
    completion_rate?: number | null;
    interaction_count?: number | null;
    valid_interaction_count?: number | null;
    calculated_at?: string | null;
    summary?: string;
    student_feedback?: string;
    mastery_update_policy?: string | null;
}

export interface FiveEStudentView {
    show_numeric_score: boolean;
    summary: string;
    effectiveness_level?: string | null;
    evidence_status?: string | null;
    next_steps?: string[];
}

export interface FiveETeacherView {
    summary: string;
    dimension_scores?: FiveEDimensionScores;
    evidence_policy?: string;
}

export interface FiveEEffectivenessSummary {
    status: "ok" | "empty" | string;
    course_id?: string | null;
    student_username?: string | null;
    record_count: number;
    scored_record_count?: number;
    outcome_supported_count?: number;
    process_only_count?: number;
    insufficient_evidence_count?: number;
    overall_effectiveness_score?: number | null;
    effectiveness_level?: string | null;
    evidence_status?: string | null;
    dimension_scores?: FiveEDimensionScores;
    low_score_threshold: number;
    low_effectiveness_nodes: FiveELowEffectivenessNode[];
    stage_distribution: FiveEStageDistributionItem[];
    recent_evidence: FiveEEffectivenessEvidence[];
    student_view?: FiveEStudentView;
    teacher_view?: FiveETeacherView;
    message?: string;
}
