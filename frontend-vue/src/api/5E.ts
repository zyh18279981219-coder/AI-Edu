import {apiClient} from "./client";
import {ChatResponse} from "../types/5E";

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