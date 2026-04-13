<template>
  <div class="layout-shell">
    <header class="topbar">
      <div class="brand">AI-Education</div>
      <nav class="nav-links">
        <RouterLink to="/teacher/dashboard">教师展板</RouterLink>
        <RouterLink to="/teacher/homework" class="homework-entry">作业中心</RouterLink>
      </nav>
      <div class="nav-user">
        <span class="nav-user-name">{{ displayName }}</span>
        <button class="ghost-btn" type="button" @click="handleLogout">退出登录</button>
      </div>
    </header>

    <main class="page-container">
      <RouterView />
    </main>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import { useRouter } from "vue-router";
import { fetchCurrentUser, logoutUser } from "../api/login";

const router = useRouter();
const currentUser = ref<{
  username: string;
  user_type: string;
  user_data: Record<string, unknown>;
} | null>(null);

const displayName = computed(() => {
  const userData = currentUser.value?.user_data ?? {};
  return String(userData["name"] ?? currentUser.value?.username ?? "教师用户");
});

async function loadCurrentUser() {
  try {
    currentUser.value = await fetchCurrentUser();
  } catch {
    currentUser.value = null;
  }
}

async function handleLogout() {
  await logoutUser();
  await router.push("/login");
}

onMounted(loadCurrentUser);
</script>

<style scoped>
.homework-entry {
  padding: 6px 12px;
  border-radius: 999px;
  border: 1px solid #0f766e;
  color: #0f766e;
  font-weight: 700;
  background: #f0fdfa;
  transition: all 0.2s ease;
}

.homework-entry:hover {
  background: #ccfbf1;
  transform: translateY(-1px);
}

.homework-entry.router-link-active {
  background: #0f766e;
  color: #ffffff;
  box-shadow: 0 6px 16px rgba(15, 118, 110, 0.28);
}
</style>
