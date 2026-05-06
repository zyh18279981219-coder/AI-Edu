export type UserType = "student" | "teacher" | "admin";

export interface LoginForm {
    username: string;
    password: string;
    user_type: UserType;
}

export interface User {
    username: string;
    user_type: string;
    user_data: Record<string, unknown>;
}

export interface LoginResponse {
    success: boolean;
    message: string;
    user: User;
}
