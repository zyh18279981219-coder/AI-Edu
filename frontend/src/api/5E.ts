import {apiClient} from "./client";
import {ChatResponse, FiveEEffectivenessSummary} from "../types/5E";

export async function fetchCourseIdByName(courseName: string) {
    const {data} = await apiClient.post<{ course_id: string }>("/api/5e/course/id-by-name", {course_name: courseName});
    return data;
}

export async function fetchChatHistory(studentId: string, courseId: string): Promise<ChatResponse[]> {
    const {data} = await apiClient.post("/api/5e/chat/history", {
        student_id: studentId,
        course_id: courseId,
    });
    return data;
}

export async function fetchFiveEEffectivenessSummary(params?: {
    course_id?: string | null;
    student_username?: string | null;
    limit?: number;
    low_score_threshold?: number;
}) {
    const {data} = await apiClient.get<FiveEEffectivenessSummary>("/api/5e/effectiveness/summary", {
        params: {
            course_id: params?.course_id || undefined,
            student_username: params?.student_username || undefined,
            limit: params?.limit,
            low_score_threshold: params?.low_score_threshold,
        },
    });
    return data;
}

export async function sendFiveEChatMessage(payload: {
    content: string;
    courseId: string;
    studentId: string;
    nodeId?: string | null;
    onChunk?: (chunk: string) => void;
}): Promise<ChatResponse> {
    const response = await fetch("/api/5e/chat/message", {
        method: "POST",
        headers: {
            "Content-Type": "application/json",
        },
        credentials: "include",
        body: JSON.stringify({
            content: payload.content,
            course_id: payload.courseId,
            user_id: payload.studentId,
            node_id: payload.nodeId || null,
        }),
    });

    if (!response.ok) {
        throw new Error(`5E assistant request failed: ${response.status}`);
    }

    if (!response.body) {
        throw new Error("ReadableStream is not supported in this browser");
    }

    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let raw = "";

    while (true) {
        const {value, done} = await reader.read();
        if (done) break;
        const chunk = decoder.decode(value, {stream: true});
        raw += chunk;
        payload.onChunk?.(raw);
    }

    raw += decoder.decode();

    try {
        return JSON.parse(raw) as ChatResponse;
    } catch {
        return {
            role: "assistant",
            content: raw || "5E 助教暂时没有返回内容。",
            buttons: [],
            resources: [],
            tests: [],
            timestamp: Date.now() / 1000,
        };
    }
}
