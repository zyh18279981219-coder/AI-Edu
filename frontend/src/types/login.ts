export type UserType = "student" | "teacher" | "admin";

export interface LoginForm {
  username: string;
  password: string;
  user_type: UserType;
}

export interface LoginResponse {
  success: boolean;
  message: string;
  user: {
    username: string;
    user_type: string;
    user_data: Record<string, unknown>;
  };
}
