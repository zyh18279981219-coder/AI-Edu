import {LoginForm, LoginResponse} from "../types/login";
import {apiClient} from "./client";

export async function fetchCurrentUser() {
    const {data} = await apiClient.get("/api/current-user");
    return data as {
        username: string;
        user_type: string;
        user_data: Record<string, unknown>;
    };
}

export async function loginUser(payload: LoginForm): Promise<LoginResponse> {
    const {data} = await apiClient.post("/api/auth/login", payload);
    return data;
}

export async function logoutUser() {
    const {data} = await apiClient.post("/api/logout");
    return data as { success: boolean; message: string };
}