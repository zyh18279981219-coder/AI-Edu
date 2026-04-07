import {
    apiClient,
    QuizState,
} from "./client";
import {
    GraphVisualizationResponse,
    LearningPathResponse,
    LearningPlanEntry, LearningPlanFile,
    LearningProgressResponse,
    ProfileUpdatePayload, StudentTwinSummary
} from "../types/student";
import axios from "axios";



export async function fetchGraphVisualization() {
    const {data} = await apiClient.get<GraphVisualizationResponse>("/api/graph-visualization");
    return data;
}

export async function fetchLearningProgress() {
    const {data} = await apiClient.get<LearningProgressResponse>("/api/learning-progress");
    return data;
}

export async function updateStudentProfile(payload: ProfileUpdatePayload) {
    const {data} = await apiClient.post("/api/update-profile", payload);
    return data as { success: boolean; message: string };
}

export async function changeStudentPassword(payload: {
    current_password: string;
    new_password: string;
}) {
    const {data} = await apiClient.post("/api/change-password", payload);
    return data as { success: boolean; message: string };
}

export async function createLearningPlan(payload: {
    name: string;
    goals: string;
    lang_choice: string;
    priority: string;
    deadline_days: number;
}) {
    const {data} = await apiClient.post("/api/learning-plan", payload);
    return data as {
        message: string;
        plan: LearningPlanEntry[];
    };
}

export async function fetchCurrentLearningPath(username: string) {
    try {
        const {data} = await apiClient.get<LearningPathResponse>(
            `/api/digital-twin/path/${encodeURIComponent(username)}/current`,
        );
        return data;
    } catch (error) {
        if (axios.isAxiosError(error)) {
            const detail =
                typeof error.response?.data === "string"
                    ? error.response.data
                    : (error.response?.data as { detail?: string } | undefined)?.detail;
            throw new Error(detail || "学习路径加载失败，请稍后重试。");
        }
        throw error;
    }
}

export async function generateLearningPath(username: string) {
    try {
        const {data} = await apiClient.post<LearningPathResponse>(
            `/api/digital-twin/path/generate/${encodeURIComponent(username)}`,
            undefined,
        );
        return data;
    } catch (error) {
        if (axios.isAxiosError(error)) {
            if (error.code === "ECONNABORTED") {
                throw new Error("个性化学习路径重新规划超时，请稍后重试。若持续较慢，我可以继续帮你优化后端生成速度。");
            }
            const detail =
                typeof error.response?.data === "string"
                    ? error.response.data
                    : (error.response?.data as { detail?: string } | undefined)?.detail;
            throw new Error(detail || "个性化学习路径生成失败，请稍后重试。");
        }
        throw error;
    }
}

export async function fetchLearningPlans() {
    const {data} = await apiClient.get<LearningPlanFile[]>("/api/learning-plans");
    return data;
}

export async function generateLearningPlanFromQuiz(payload: {
    name: string;
    state: QuizState;
    lang_choice?: string;
}) {
    const {data} = await apiClient.post<{
        message: string;
        plan: LearningPlanEntry[]
    }>("/api/learning-plan/from-quiz", {
        name: payload.name,
        state: payload.state,
        lang_choice: payload.lang_choice ?? "auto",
    });
    return data;
}

export async function fetchStudentTwin(username: string) {
    const {data} = await apiClient.get<StudentTwinSummary>(`/api/digital-twin/student-profile/${encodeURIComponent(username)}`);
    return data;
}

export async function refreshStudentTwin(username: string) {
    const {data} = await apiClient.post('/api/digital-twin/collect/${encodeURIComponent(username)}');
    return data;
}


