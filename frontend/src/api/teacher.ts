import {apiClient, HeatmapResponse} from './client';
import {
    ClassOverviewResponse,
    TeacherStudentDetail,
    TeacherStudentTrend,
    TeacherTwinAiSuggestionsResponse,
    TeacherTwinDrilldownResponse,
    TeacherTwinSummary,
    CourseDigitalTwinResource,
    CourseDigitalTwinSummary,
    CourseInitialGraphResponse,
    CourseResourceBindResponse,
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

export async function fetchTeacherTwinDrilldown(dimension: string, windowDays = 30) {
    const {data} = await apiClient.get<TeacherTwinDrilldownResponse>('/api/dashboard/teacher-twin/drilldown', {
        params: {
            dimension,
            window_days: windowDays,
        },
    });
    return data;
}

export async function fetchCourseDigitalTwinCourses() {
    const {data} = await apiClient.get<{ courses: CourseDigitalTwinSummary[] }>('/api/course-digital-twin/courses');
    return data;
}

export async function fetchCourseDigitalTwin(courseId: string) {
    const {data} = await apiClient.get<{
        summary: CourseDigitalTwinSummary;
        graph_data: Record<string, unknown>;
    }>(`/api/course-digital-twin/${encodeURIComponent(courseId)}`);
    return data;
}

export async function generateCourseInitialGraph(payload: {
    course_id: string;
    course_name: string;
    outline_text: string;
    lifecycle_status?: string;
    bind_resource_candidates?: boolean;
    max_resources_per_leaf?: number;
}) {
    const {data} = await apiClient.post<CourseInitialGraphResponse>('/api/course-digital-twin/initial-graph', payload);
    return data;
}

export async function bindCourseResourceCandidates(payload: {
    course_id: string;
    max_resources_per_leaf?: number;
    overwrite?: boolean;
    review_status?: string;
}) {
    const {data} = await apiClient.post<CourseResourceBindResponse>('/api/course-digital-twin/resource-candidates/bind', payload);
    return data;
}

export async function fetchCourseDigitalTwinResources(courseId: string) {
    const {data} = await apiClient.get<{ resources: CourseDigitalTwinResource[] }>(
        `/api/course-digital-twin/${encodeURIComponent(courseId)}/resources`,
    );
    return data;
}

export async function reviewCourseDigitalTwinResource(payload: {
    course_id: string;
    node_id: string;
    resource_path: string;
    is_enabled: boolean;
    review_status?: string;
    quality_status?: string;
}) {
    const {data} = await apiClient.post<{ success: boolean; summary: CourseDigitalTwinSummary }>(
        '/api/course-digital-twin/resource-review',
        payload,
    );
    return data;
}

export async function publishCourseDigitalTwin(courseId: string) {
    const {data} = await apiClient.post<{ success: boolean; summary: CourseDigitalTwinSummary }>(
        '/api/course-digital-twin/publish',
        {course_id: courseId},
    );
    return data;
}
