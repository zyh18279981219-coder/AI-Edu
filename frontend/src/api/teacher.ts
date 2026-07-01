import {apiClient, HeatmapResponse} from './client';
import {
    ClassOverviewResponse,
    TeacherStudentDetail,
    TeacherStudentTrend,
    TeacherTwinAiSuggestionsResponse,
    TeacherTwinDrilldownResponse,
    TeacherTwinSummary,
    CourseAbilityMapping,
    CourseAbilityMappingCandidateResult,
    CourseCareerAbility,
    CourseCareerPosition,
    CourseDigitalTwinResource,
    CourseDigitalTwinSummary,
    CourseInitialGraphResponse,
    CourseResourceBindResponse,
    CourseStructureUpsertResponse,
    CourseRuntimeEvaluation,
    QuizDefinition,
    QuizDefinitionQuestion,
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

export async function upsertCourseDigitalTwinStructure(payload: {
    course_id: string;
    course_name: string;
    graph_data: Record<string, unknown>;
    lifecycle_status?: string;
}) {
    const {data} = await apiClient.post<CourseStructureUpsertResponse>('/api/course-digital-twin/structure', payload);
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

export async function fetchCourseDigitalTwinPositions(courseId: string) {
    const {data} = await apiClient.get<{ positions: CourseCareerPosition[] }>(
        `/api/course-digital-twin/${encodeURIComponent(courseId)}/positions`,
    );
    return data;
}

export async function saveCourseDigitalTwinPosition(payload: {
    course_id: string;
    position_name: string;
    position_type?: string;
    target_rank?: number;
    source_keyword?: string | null;
}) {
    const {data} = await apiClient.post<{
        success: boolean;
        position: CourseCareerPosition;
        positions: CourseCareerPosition[];
    }>('/api/course-digital-twin/positions', payload);
    return data;
}

export async function fetchCourseDigitalTwinAbilities(courseId: string) {
    const {data} = await apiClient.get<{ abilities: CourseCareerAbility[] }>(
        `/api/course-digital-twin/${encodeURIComponent(courseId)}/abilities`,
    );
    return data;
}

export async function importCourseDigitalTwinAbilities(payload: {
    course_id: string;
    position_id: number;
    abilities: Array<Record<string, unknown>>;
    industry_payload?: Record<string, unknown> | null;
    generate_mapping_candidates?: boolean;
    max_candidates_per_ability?: number;
    min_mapping_score?: number;
}) {
    const {data} = await apiClient.post<{
        success: boolean;
        import_result: { position_id: number; saved: number; ability_ids: number[] };
        abilities: CourseCareerAbility[];
        mapping_candidate_result?: CourseAbilityMappingCandidateResult | null;
        mappings?: CourseAbilityMapping[] | null;
    }>('/api/course-digital-twin/abilities/import', payload);
    return data;
}

export async function fetchCourseDigitalTwinAbilityMappings(courseId: string) {
    const {data} = await apiClient.get<{ mappings: CourseAbilityMapping[] }>(
        `/api/course-digital-twin/${encodeURIComponent(courseId)}/ability-mappings`,
    );
    return data;
}

export async function saveCourseDigitalTwinAbilityMappings(payload: {
    course_id: string;
    mappings: Array<Record<string, unknown>>;
}) {
    const {data} = await apiClient.post<{
        success: boolean;
        mapping_result: { saved: number; rejected?: Array<Record<string, unknown>> };
        mappings: CourseAbilityMapping[];
    }>('/api/course-digital-twin/ability-mappings', payload);
    return data;
}

export async function generateCourseDigitalTwinAbilityMappingCandidates(payload: {
    course_id: string;
    max_candidates_per_ability?: number;
    min_score?: number;
}) {
    const {data} = await apiClient.post<{
        success: boolean;
        candidate_result: CourseAbilityMappingCandidateResult;
        mappings: CourseAbilityMapping[];
    }>('/api/course-digital-twin/ability-mappings/candidates/generate', payload);
    return data;
}

export async function fetchCourseDigitalTwinRuntimeEvaluation(courseId: string, windowDays = 30, minQuizAttempts = 3) {
    const {data} = await apiClient.get<{ evaluation: CourseRuntimeEvaluation }>(
        `/api/course-digital-twin/${encodeURIComponent(courseId)}/runtime-evaluation`,
        {
            params: {
                window_days: windowDays,
                min_quiz_attempts: minQuizAttempts,
            },
        },
    );
    return data;
}

export async function fetchQuizDefinitions(payload: { course_id: string; node_id: string; status?: string }) {
    const {data} = await apiClient.get<{ definitions: QuizDefinition[] }>('/api/quiz/definitions', {
        params: {
            course_id: payload.course_id,
            node_id: payload.node_id,
            status: payload.status,
        },
    });
    return data;
}

export async function saveQuizDefinition(payload: {
    course_id: string;
    node_id: string;
    title?: string;
    status?: string;
    definition_id?: string;
    questions: QuizDefinitionQuestion[];
}) {
    const {data} = await apiClient.post<{ success: boolean; definition: QuizDefinition }>('/api/quiz/definitions', payload);
    return data;
}

export async function publishQuizDefinition(payload: { definition_id: string; course_id: string; node_id: string }) {
    const {data} = await apiClient.post<{ success: boolean; definition: QuizDefinition }>(
        `/api/quiz/definitions/${encodeURIComponent(payload.definition_id)}/publish`,
        {
            course_id: payload.course_id,
            node_id: payload.node_id,
        },
    );
    return data;
}

export async function reviewCourseDigitalTwinAbilityMappings(payload: {
    course_id: string;
    mappings: Array<{
        mapping_id: number;
        review_status: string;
        support_level?: string | null;
    }>;
}) {
    const {data} = await apiClient.post<{ success: boolean; updated: number; mappings: CourseAbilityMapping[] }>(
        '/api/course-digital-twin/ability-mappings/review',
        payload,
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
