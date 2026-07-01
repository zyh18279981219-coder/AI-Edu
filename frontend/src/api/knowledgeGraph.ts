import {KnowledgeGraphResponse} from "../types/knowledgeGraph";
import {apiClient} from "./client";

export async function fetchKnowledgeGraph(courseId?: string | null) {
    const {data} = await apiClient.get<KnowledgeGraphResponse>("/api/knowledge-graph", {
        params: courseId ? {course_id: courseId} : undefined,
    });
    return data;
}
