export interface IndustryStatusResponse {
    ok: boolean;
    messages: string[];
    countries: string[];
    cities: string[];
    city_map: Record<string, string[]>;
    sources: string[];
}

export interface IndustryTaskMeta {
    step?: number;
    current?: number;
    total?: number;
    raw_count?: number;
    title?: string;
    countries?: string[];
    parallel?: boolean;
}

export interface IndustryJob {
    title: string;
    company: string;
    salary: string;
    experience: string;
    education: string;
    location: string;
    source: string;
    description: string;
    requirements: string;
    relevance_score: number;
    relevance_reasons: string[];
    skills: string[];
    skill_evidence: Array<{ name?: string; evidence?: string }>;
    market_country?: string;
}

export interface IndustryChartRow {
    name: string;
    value: number;
}

export interface IndustryResult {
    jobs: IndustryJob[];
    metrics: {
        jobs_total: number;
        jobs_analyzed: number;
        skills_total: number;
        sources_total: number;
    };
    summary: Record<string, unknown>;
    raw_count: number;
    source_counts: Record<string, number>;
    relevance_summary: {
        input_count?: number;
        requested_count?: number;
        threshold?: number;
        threshold_kept_count?: number;
        selected_count?: number;
        dropped_count?: number;
        backfilled_count?: number;
        strict_threshold?: boolean;
        fetch_rounds?: number;
        final_fetch_limit?: number;
        max_fetch_limit?: number;
        completed_target?: boolean;
        country?: string;
        city?: string;
        search_terms?: string[];
        parallel?: boolean;
        included_countries?: string[];
    };
    relevance_message: string;
    warnings: string[];
    charts: {
        skill_ranking: IndustryChartRow[];
        job_distribution: IndustryChartRow[];
        experience_distribution: IndustryChartRow[];
        education_distribution: IndustryChartRow[];
        skill_heatmap: unknown;
    };
}

export interface IndustryTask {
    task_id: string;
    task_type: "analyze" | "reanalyze";
    status: string;
    message: string;
    meta?: IndustryTaskMeta;
    result?: IndustryResult | null;
    error?: string | null;
    cancel_requested?: boolean;
}

export interface IndustryAnalyzePayload {
    keyword: string;
    country: string;
    city: string;
    include_global: boolean;
    job_limit: number;
    relevance_threshold: number;
    sources: string[];
    fetch_desc: boolean;
}