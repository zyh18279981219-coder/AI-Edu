import {KnowledgeGraphResponse} from "../types/knowledgeGraph";
import {apiClient} from "./client";

export async function fetchKnowledgeGraph() {
    const {data} = await apiClient.get<KnowledgeGraphResponse>("/api/knowledge-graph");
    return data;
}