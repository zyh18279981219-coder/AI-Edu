export type UserType = "student" | "teacher" | "admin";

export interface LoginForm {
    username: string;
    password: string;
    user_type: UserType;
}

export interface User {
    username: string;
    user_type: UserType;
    login_id: string;
    user_id: string;
}

export interface LoginResponse {
    success: boolean;
    message: string;
    user: User;
}
