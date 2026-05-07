import { apiClient } from "./client";

export interface Notification {
    icon: string;
    title: string;
    time: string;
    timestamp: string;
    type: string;
    link: string;
}

export interface NotificationResponse {
    success: boolean;
    notifications: Notification[];
    count: number;
}

export async function fetchRecentNotifications(limit: number = 10) {
    const { data } = await apiClient.get<NotificationResponse>("/api/notifications/recent", {
        params: { limit }
    });
    return data;
}
