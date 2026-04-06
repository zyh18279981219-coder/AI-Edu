import axios from "axios";

export const apiClient = axios.create({
    baseURL: '',
    withCredentials: true,
});

const backendOrigin = (import.meta.env.VITE_BACKEND_ORIGIN as string | undefined)?.replace(/\/$/, "")
    ?? (import.meta.env.DEV ? "http://127.0.0.1:8000" : "");

export function buildBackendUrl(path: string) {
    const normalizedPath = path.startsWith("/") ? path : `/${path}`;
    return `${backendOrigin}${normalizedPath}`;
}

export interface TechnicalLevel {
    label: string;
    code: string;
    description: string;
}

export interface RadarMetric {
    name: string;
    value: number;
}

export interface RiskAlert {
    code: string;
    level: string;
    title: string;
    detail: string;
}

export interface WeakNode {
    node_id: string;
    node_path: string[];
    mastery_score: number;
    progress: number;
    quiz_score: number;
}

export interface TrendPoint {
    date: string;
    overall_mastery: number;
}


export interface ChatResponse {
    response: string;
    used_fallback?: boolean;
    used_retriever?: boolean;
}

export interface SummaryResponse {
    summary?: string;
    used_retriever?: boolean;
}

export interface QuizQuestion {
    topic: string;
    question: string;
    correct: string;
}

export interface QuizState {
    subject: string;
    language: string;
    questions: QuizQuestion[];
    index: number;
    scores: Record<string, [number, number]>;
    correct_total: number;
}

export interface QuizStartResponse {
    question: QuizQuestion;
    state: QuizState;
    used_retriever?: boolean;
}

export interface QuizAnswerResponse {
    finished: boolean;
    is_correct?: boolean;
    correct_answer?: string;
    next_question?: QuizQuestion;
    results?: string;
    state: QuizState;
}

export interface QuizSummaryResponse {
    summary: string;
}

export interface DashboardStudentSummary {
    username: string;
    overall_mastery: number;
}



export interface HeatmapNodeRow {
    node_id: string;
    avg_mastery: number;
    student_count: number;
}

export interface HeatmapResponse {
    nodes: HeatmapNodeRow[];
}


export interface AdminTeacherRecord {
    username: string;
    name: string;
    email?: string;
    students: string[];
}

export interface AdminStudentPreference {
    course_type?: Array<{ name?: string }>;
}

export interface AdminStudentRecord {
    username: string;
    stu_name: string;
    email?: string;
    img?: string;
    teacher?: string;
    learning_goals?: string[];
    preference?: AdminStudentPreference;
}

export interface AdminLlmLog {
    timestamp: string;
    module?: string;
    metadata?: Record<string, unknown>;
    request?: {
        model?: string;
        messages?: Array<{ role: string; content: string }>;
    };
    response?: {
        usage?: {
            prompt_tokens?: number;
            completion_tokens?: number;
            total_tokens?: number;
        };
        choices?: Array<{
            message?: {
                content?: string;
            };
        }>;
    };
}





export async function fetchLanguages() {
    const {data} = await apiClient.get<string[]>("/languages");
    return data;
}


export async function fetchAdminTeachers() {
    const {data} = await apiClient.get<AdminTeacherRecord[]>("/teachers");
    return data;
}

export async function fetchAdminStudents() {
    const {data} = await apiClient.get<AdminStudentRecord[]>("/students");
    return data;
}

export async function fetchAdminLlmLogs() {
    const {data} = await apiClient.get<AdminLlmLog[]>("/llm-logs");
    return data;
}

export async function selectPdfForChat(pdfPath: string) {
    const {data} = await apiClient.post("/pdf/select", {pdf_path: pdfPath});
    return data as { success: boolean; pdf_path: string };
}

export async function sendCourseChat(payload: {
    message: string;
    history: Array<[string, string]>;
    lang_choice?: string;
}) {
    try {
        const {data} = await apiClient.post<ChatResponse>(
            "/chat",
            {
                message: payload.message,
                history: payload.history,
                lang_choice: payload.lang_choice ?? "auto",
            },
        );
        return data;
    } catch (error) {
        if (axios.isAxiosError(error)) {
            if (error.code === "ECONNABORTED") {
                throw new Error("AI 助教响应超时，请稍后重试，或换一个更短的问题。");
            }
            const detail =
                typeof error.response?.data === "string"
                    ? error.response.data
                    : (error.response?.data as { detail?: string } | undefined)?.detail;
            throw new Error(detail || "AI 助教暂时不可用，请稍后重试。");
        }
        throw error;
    }
}

export async function generateCourseSummary(topic: string) {
    const {data} = await apiClient.post<SummaryResponse>("/summary", {
        topic,
        lang_choice: "auto",
    });
    return data;
}

export async function startQuiz(payload: { subject: string; lang_choice?: string }) {
    const {data} = await apiClient.post<QuizStartResponse>(
        "/quiz/start",
        {
            subject: payload.subject,
            lang_choice: payload.lang_choice ?? "auto",
        },
    );
    return data;
}

export async function answerQuiz(payload: { choice: string; state: QuizState }) {
    const {data} = await apiClient.post<QuizAnswerResponse>("/quiz/answer", payload);
    return data;
}

export async function generateQuizSummary(payload: {
    topic: string;
    score: number;
    total: number;
    user_answers: Array<Record<string, unknown>>;
    questions: Array<Record<string, unknown>>;
}) {
    const {data} = await apiClient.post<QuizSummaryResponse>("/quiz/summary", payload);
    return data;
}



export async function completeQuiz(payload: { node_name: string; score: number; total: number }) {
    const {data} = await apiClient.post<{
        success: boolean;
        message?: string;
        passed?: boolean
    }>("/quiz/complete", payload);
    return data;
}


