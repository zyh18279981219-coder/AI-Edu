<template>
  <div class="layout-shell">
    <header class="topbar">
      <div class="brand">AI-Education</div>
      <nav class="nav-links">
        <RouterLink to="/teacher/dashboard" active-class="" exact-active-class="router-link-active">教师展板</RouterLink>
        <RouterLink to="/teacher/homework" active-class="" exact-active-class="router-link-active">作业中心</RouterLink>
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
</style>
