import {createRouter, createWebHistory} from "vue-router";
import axios from "axios";
import {fetchCurrentUser} from "../api/login";

const AdminLayout = () => import("../layouts/AdminLayout.vue");
const StudentLayout = () => import("../layouts/StudentLayout.vue");
const TeacherLayout = () => import("../layouts/TeacherLayout.vue");
const AdminDashboardView = () => import("../views/admin/AdminDashboardView.vue");
const HomeView = () => import("../views/student/HomeView.vue");
const LoginView = () => import("../views/LoginView.vue");
const CourseContentView = () => import("../views/student/CourseContentView.vue");
const IndustryIntelligenceView = () => import("../views/student/IndustryIntelligenceView.vue");
const MyLearningView = () => import("../views/student/MyLearningView.vue");
const ProfileView = () => import("../views/student/ProfileView.vue");
const QuizView = () => import("../views/student/QuizView.vue");
const StudentTwinView = () => import("../views/student/StudentTwinView.vue");
const TeacherDashboardView = () => import("../views/teacher/TeacherDashboardView.vue");

const router = createRouter({
    history: createWebHistory(),
    routes: [
        {
            path: "/login",
            name: "login",
            component: LoginView,
            meta: {guestOnly: true},
        },
        {
            path: "/student",
            component: StudentLayout,
            meta: {requiresAuth: true, requiredRole: 'student'},
            children: [
                {
                    path: "home",
                    name: "student-home",
                    component: HomeView,
                },
                {
                    path: "learning",
                    name: "student-learning",
                    component: MyLearningView,
                },
                {
                    path: "profile",
                    name: "student-profile",
                    component: ProfileView,
                },
                {
                    path: "course-content",
                    name: "course-content",
                    component: CourseContentView,
                },
                {
                    path: "student-twin",
                    name: "student-twin",
                    component: StudentTwinView,
                },
                {
                    path: "quiz",
                    name: "quiz",
                    component: QuizView,
                },
                {
                    path: "industry-intelligence",
                    name: "industry-intelligence",
                    component: IndustryIntelligenceView,
                },
            ],
        },
        {
            path: "/teacher",
            component: TeacherLayout,
            meta: {requiresAuth: true, requiredRole: "teacher"},
            children: [
                {
                    path: "dashboard",
                    name: "teacher-dashboard",
                    component: TeacherDashboardView,
                },
            ],
        },
        {
            path: "/admin",
            component: AdminLayout,
            meta: {requiresAuth: true, requiredRole: "admin"},
            children: [
                {
                    path: "dashboard",
                    name: "admin-dashboard",
                    component: AdminDashboardView,
                },
            ],
        },
        {
            path: "/:pathMatch(.*)*",
            redirect: (to) => {
                return "/login";
            }
        }
    ],
});

router.beforeEach(async (to, from) => {
    try {
        const currentUser = await fetchCurrentUser();
        const userType = currentUser.user_type;

        if (to.meta.guestOnly) {
            return getFallbackRoute(userType)
        }

        if (to.matched.length === 0 || to.path === '/') {
            return getFallbackRoute(userType);
        }

        return true;
    } catch (error) {
        if (axios.isAxiosError(error) && error.response?.status === 401) {
            if (to.meta.requiresAuth) {
                return {name: "login", query: {redirect: to.fullPath}};
            }
        }

        if (to.name === 'login') return true;
        return {name: "login"};
    }
});

function getFallbackRoute(userType: string) {
    switch (userType) {
        case 'teacher':
            return {name: 'teacher-dashboard'};
        case 'admin':
            return {name: 'admin-dashboard'};
        case 'student':
            return {name: 'student-home'};
        default:
            return {name: 'login'};
    }
}

export default router;
