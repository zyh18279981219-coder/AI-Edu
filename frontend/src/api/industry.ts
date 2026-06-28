import {apiClient} from './client';
import {IndustryAnalyzePayload, IndustryJob, IndustryStatusResponse, IndustryTask} from '../types/industry';

export async function fetchIndustryStatus() {
    const {data} = await apiClient.get<IndustryStatusResponse>('/api/industry-intelligence/status');
    return data;
}

export async function fetchCurrentIndustryTask() {
    const {data} = await apiClient.get<{ task: IndustryTask | null }>('/api/industry-intelligence/current');
    return data.task;
}

export async function fetchIndustryTask(taskId: string) {
    const {data} = await apiClient.get<IndustryTask>(`/api/industry-intelligence/tasks/${encodeURIComponent(taskId)}`);
    return data;
}

export async function startIndustryAnalysis(payload: IndustryAnalyzePayload) {
    const {data} = await apiClient.post<{
        success: boolean;
        task_id: string
    }>('/api/industry-intelligence/analyze', payload);
    return data;
}

export async function reanalyzeIndustryJobs(jobs: IndustryJob[]) {
    const {data} = await apiClient.post<{ success: boolean; task_id: string }>('/api/industry-intelligence/reanalyze', {
        jobs,
    });
    return data;
}

export async function cancelIndustryTask(taskId: string) {
    const {data} = await apiClient.post<{ success: boolean; task: IndustryTask }>(
        `/api/industry-intelligence/tasks/${encodeURIComponent(taskId)}/cancel`,
    );
    return data;
}
