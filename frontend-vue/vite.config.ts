import { defineConfig } from "vite";
import vue from "@vitejs/plugin-vue";
import AutoImport from "unplugin-auto-import/vite";
import Components from "unplugin-vue-components/vite";
import { ElementPlusResolver } from "unplugin-vue-components/resolvers";

export default defineConfig({
  plugins: [
    vue(),
    AutoImport({
      imports: ["vue", "vue-router"],
      resolvers: [ElementPlusResolver()],
      dts: "src/auto-imports.d.ts",
    }),
    Components({
      resolvers: [ElementPlusResolver({ importStyle: "css" })],
      dts: "src/components.d.ts",
    }),
  ],
  build: {
    rollupOptions: {
      output: {
        manualChunks(id) {
          if (id.includes("node_modules")) {
            if (id.includes("echarts")) return "charts";
            if (id.includes("vue-router")) return "vue-router";
            if (id.includes("axios")) return "network";
            if (id.includes("element-plus") || id.includes("@element-plus")) return undefined;
            return "vendor";
          }
          if (id.includes("/src/views/student/IndustryIntelligenceView.vue")) return "page-industry-intelligence";
          if (id.includes("/src/views/student/StudentTwinView.vue")) return "page-student-twin";
          if (id.includes("/src/views/student/CourseContentView.vue")) return "page-course-content";
          if (id.includes("/src/views/student/MyLearningView.vue")) return "page-my-learning";
          if (id.includes("/src/views/student/QuizView.vue")) return "page-quiz";
          if (id.includes("/src/views/student/ProfileView.vue")) return "page-profile";
          if (id.includes("/src/views/teacher/TeacherDashboardView.vue")) return "page-teacher-dashboard";
          if (id.includes("/src/views/admin/panels/AdminUsersPanel.vue")) return "panel-admin-users";
          if (id.includes("/src/views/admin/panels/AdminTokensPanel.vue")) return "panel-admin-tokens";
          if (id.includes("/src/views/admin/panels/AdminConversationsPanel.vue")) return "panel-admin-conversations";
          if (id.includes("/src/views/student/components/IndustryResultsBoard.vue")) return "panel-industry-results";
          if (id.includes("/src/views/HomeView.vue")) return "page-home";
          if (id.includes("/src/views/LoginView.vue")) return "page-login";
          return undefined;
        },
      },
    },
  },
  server: {
    port: 5173,
    proxy: {
      "/api": {
        target: "http://127.0.0.1:8000",
        changeOrigin: true,
      },
      "/static": {
        target: "http://127.0.0.1:8000",
        changeOrigin: true,
      },
    },
  },
});
