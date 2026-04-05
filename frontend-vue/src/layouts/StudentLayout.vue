<template>
  <div class="layout-shell">
    <header class="topbar">
      <div class="brand">AI-Education</div>
      <nav class="nav-links">
        <RouterLink to="/" exact-active-class="router-link-active">首页</RouterLink>
        <RouterLink to="/learning">我的学习</RouterLink>
        <RouterLink to="/course-content">课程内容</RouterLink>
        <RouterLink to="/student-twin">学生孪生</RouterLink>
        <RouterLink to="/industry-intelligence">行业情报</RouterLink>
        <RouterLink to="/profile">个人中心</RouterLink>
      </nav>
      <div class="nav-user">
        <RouterLink class="nav-user-name nav-profile-link" to="/profile">{{ displayName }}</RouterLink>
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
  return String(userData.stu_name ?? userData.name ?? currentUser.value?.username ?? "当前用户");
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
