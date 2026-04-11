import {apiClient, HeatmapResponse} from './client';
import {
    ClassOverviewResponse,
    TeacherStudentDetail,
    TeacherStudentTrend,
    TeacherTwinAiSuggestionsResponse,
    TeacherTwinSummary,
    UploadResponse,
} from '../types/teacher';

export async function uploadTeacherResources(nodeName: string, files: File[]) {
    const formData = new FormData();
    files.forEach((file) => formData.append('files', file));
    formData.append('node_name', nodeName);
    const {data} = await apiClient.post<UploadResponse>('/api/upload', formData, {
        headers: {'Content-Type': 'multipart/form-data'},
    });
    return data;
}

export async function deleteTeacherResource(nodeName: string, resourceIndex: number) {
    const {data} = await apiClient.post<{ success: boolean; message: string }>('/api/delete-resource', {
        node_name: nodeName,
        resource_index: resourceIndex,
    });
    return data;
}

export async function fetchClassOverview() {
    const {data} = await apiClient.get<ClassOverviewResponse>('/api/dashboard/class-overview');
    return data;
}

export async function fetchTeacherStudentDetail(username: string) {
    const {data} = await apiClient.get<TeacherStudentDetail>(`/api/dashboard/student/${encodeURIComponent(username)}`);
    return data;
}

export async function fetchTeacherStudentTrend(username: string) {
    const {data} = await apiClient.get<TeacherStudentTrend>(`/api/dashboard/student/${encodeURIComponent(username)}/trend`);
    return data;
}

export async function fetchTeacherStudents() {
    const {data} = await apiClient.get<Array<Record<string, unknown>>>('/api/students');
    return data;
}

export async function fetchTeacherHeatmap() {
    const {data} = await apiClient.get<HeatmapResponse>('/api/heatmap');
    return data;
}

export async function fetchTeacherTwin() {
    const {data} = await apiClient.get<TeacherTwinSummary>('/api/dashboard/teacher-twin');
    return data;
}

export async function generateTeacherTwinAiSuggestions() {
    const {data} = await apiClient.post<TeacherTwinAiSuggestionsResponse>('/api/dashboard/teacher-twin/ai-suggestions');
    return data;
}