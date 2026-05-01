import { apiClient } from "./client";
import type {
  TeachingAnnouncement,
  TeachingContextOption,
  TeachingDiscussionTopic,
  TeachingResearchRecord,
} from "../types/teaching";

export async function teachingListAnnouncements() {
  const { data } = await apiClient.get<{ success: boolean; announcements: TeachingAnnouncement[] }>(
    "/api/teaching-interaction/announcements",
  );
  return data;
}

export async function teachingListPublicAnnouncements() {
  const { data } = await apiClient.get<{ success: boolean; announcements: TeachingAnnouncement[] }>(
    "/api/teaching-interaction/announcements/public",
  );
  return data;
}

export async function teachingCreateAnnouncement(payload: {
  title: string;
  content: string;
  class_name?: string;
  course_id?: string;
}) {
  const { data } = await apiClient.post<{ success: boolean; announcement: TeachingAnnouncement }>(
    "/api/teaching-interaction/announcements",
    payload,
  );
  return data;
}

export async function teachingListTopics() {
  const { data } = await apiClient.get<{ success: boolean; topics: TeachingDiscussionTopic[] }>(
    "/api/teaching-interaction/topics",
  );
  return data;
}

export async function teachingListPublicTopics() {
  const { data } = await apiClient.get<{ success: boolean; topics: TeachingDiscussionTopic[] }>(
    "/api/teaching-interaction/topics/public",
  );
  return data;
}

export async function teachingCreateTopic(payload: {
  title: string;
  content: string;
  class_name?: string;
  course_id?: string;
}) {
  const { data } = await apiClient.post<{ success: boolean; topic: TeachingDiscussionTopic }>(
    "/api/teaching-interaction/topics",
    payload,
  );
  return data;
}

export async function teachingCreatePost(payload: {
  topic_id: string;
  author_username: string;
  author_role: string;
  content: string;
  replied_to_post_id?: string;
  replied_to_created_at?: string;
}) {
  const { data } = await apiClient.post("/api/teaching-interaction/posts", payload);
  return data;
}

export async function teachingCreateStudentQuestion(topicId: string, content: string) {
  const { data } = await apiClient.post(`/api/teaching-interaction/topics/${encodeURIComponent(topicId)}/student-question`, null, {
    params: { content },
  });
  return data;
}

export async function teachingGetInteractionContextOptions() {
  const { data } = await apiClient.get<{
    success: boolean;
    class_options: TeachingContextOption[];
    course_options: TeachingContextOption[];
  }>("/api/teaching-interaction/context-options");
  return data;
}

export async function teachingListResearchRecords() {
  const { data } = await apiClient.get<{ success: boolean; records: TeachingResearchRecord[] }>(
    "/api/teaching-research/records",
  );
  return data;
}

export async function teachingCreateResearchRecord(payload: {
  activity_type: string;
  title: string;
  description?: string;
  resource_link?: string;
  class_name?: string;
  course_id?: string;
  happened_at?: string;
}) {
  const { data } = await apiClient.post<{ success: boolean; record: TeachingResearchRecord }>(
    "/api/teaching-research/records",
    payload,
  );
  return data;
}

export async function teachingGetResearchContextOptions() {
  const { data } = await apiClient.get<{
    success: boolean;
    class_options: TeachingContextOption[];
    course_options: TeachingContextOption[];
  }>("/api/teaching-research/context-options");
  return data;
}
