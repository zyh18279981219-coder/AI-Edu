<template>
  <div class="layout-shell">
    <header class="topbar">
      <div class="brand">AI-Education</div>
      <nav class="nav-links">
        <RouterLink to="/admin/dashboard">管理端</RouterLink>
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
import { fetchCurrentUser, logoutUser } from "../api/studentTwin";

const router = useRouter();
const currentUser = ref<{
  username: string;
  user_type: string;
  user_data: Record<string, unknown>;
} | null>(null);

const displayName = computed(() => {
  const userData = currentUser.value?.user_data ?? {};
  return String(userData["name"] ?? currentUser.value?.username ?? "管理员");
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
