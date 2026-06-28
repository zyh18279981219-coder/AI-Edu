import { apiClient } from "./client";

export interface LearningStreakData {
    current_streak: number;
    longest_streak: number;
    last_activity_date: string | null;
    total_days: number;
}

export async function fetchLearningStreak() {
    const { data } = await apiClient.get<LearningStreakData>("/api/learning-streak");
    return data;
}

export async function logLearningActivity(activityType: string, activityDetails?: string) {
    const { data } = await apiClient.post<{ success: boolean; streak?: LearningStreakData }>("/api/learning-activity", {
        activity_type: activityType,
        activity_details: activityDetails,
    });
    return data;
}
