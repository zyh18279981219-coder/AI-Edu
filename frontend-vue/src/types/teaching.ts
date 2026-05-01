export interface TeachingAnnouncement {
  id: string;
  teacher_username: string;
  title: string;
  content: string;
  class_name?: string;
  course_id?: string;
  status: string;
  published_at: string;
  created_at: string;
  updated_at: string;
}

export interface TeachingDiscussionPost {
  id: string;
  topic_id: string;
  author_username: string;
  author_role: string;
  content: string;
  replied_to_post_id?: string | null;
  response_minutes?: number | null;
  created_at: string;
}

export interface TeachingDiscussionTopic {
  id: string;
  teacher_username: string;
  title: string;
  content: string;
  class_name?: string;
  course_id?: string;
  status: string;
  student_question_count: number;
  teacher_reply_count: number;
  created_at: string;
  updated_at: string;
  posts?: TeachingDiscussionPost[];
}

export interface TeachingResearchRecord {
  id: string;
  teacher_username: string;
  activity_type: string;
  title: string;
  description: string;
  resource_link: string;
  class_name: string;
  course_id: string;
  happened_at: string;
  created_at: string;
  updated_at: string;
}

export interface TeachingContextOption {
  label: string;
  value: string;
}
