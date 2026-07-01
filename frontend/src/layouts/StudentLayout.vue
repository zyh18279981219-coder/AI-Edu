<template>
  <div class="layout-shell">
    <header class="topbar">
      <div class="brand">AI-Education</div>
      <nav class="nav-links">
        <RouterLink to="/student/home" active-class="" exact-active-class="router-link-active">
          今日学习
        </RouterLink>
        <RouterLink to="/student/course-content" active-class="" exact-active-class="router-link-active">
          学习中心
        </RouterLink>
        <RouterLink to="/student/learning" active-class="" exact-active-class="router-link-active">
          个性化路径
        </RouterLink>
        <RouterLink to="/student/student-twin" active-class="" exact-active-class="router-link-active">
          学习诊断
        </RouterLink>
        <RouterLink to="/student/homework" active-class="" exact-active-class="router-link-active">
          作业测验
        </RouterLink>
        <RouterLink to="/student/intervention" active-class="" exact-active-class="router-link-active">
          老师任务
        </RouterLink>
        <RouterLink to="/student/interaction" active-class="" exact-active-class="router-link-active">
          互动答疑
        </RouterLink>
        <RouterLink to="/student/profile" active-class="" exact-active-class="router-link-active">
          设置
        </RouterLink>
      </nav>
      <div class="nav-user">
        <locale-selection/>
        <RouterLink class="nav-user-name nav-profile-link" to="/student/profile">{{ displayName }}</RouterLink>
        <button class="ghost-btn" type="button" @click="handleLogout">{{ $t('layout.logout') }}</button>
      </div>
    </header>

    <main class="page-container">
      <RouterView />
    </main>
  </div>
</template>

<script setup lang="ts">
import {computed, onMounted, ref} from "vue";
import {useRouter} from "vue-router";
import {fetchCurrentUser, logoutUser} from "../api/login";

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

<style scoped>
</style>
