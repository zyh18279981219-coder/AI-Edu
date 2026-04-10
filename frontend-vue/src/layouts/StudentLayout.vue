<template>
  <div class="layout-shell">
    <header class="topbar">
      <div class="brand">AI-Education</div>
      <nav class="nav-links">
        <RouterLink to="/student/home" exact-active-class="router-link-active">{{$t('layout.student.home')}}</RouterLink>
        <RouterLink to="/student/learning">{{$t('layout.student.myLearning')}}</RouterLink>
        <RouterLink to="/student/course-content">{{$t('layout.student.courseContent')}}</RouterLink>
        <RouterLink to="/student/student-twin">{{$t('layout.student.studentTwin')}}</RouterLink>
        <RouterLink to="/student/industry-intelligence">{{$t('layout.student.industryInformation')}}</RouterLink>
        <RouterLink to="/student/profile">{{$t('layout.student.profile')}}</RouterLink>
      </nav>
      <div class="nav-user">
        <user-layout :display-name="displayName"/>
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
import {logoutUser } from "../api/login";
import {fetchCurrentUser} from "../api/login";
import UserLayout from "./UserLayout.vue";

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

onMounted(loadCurrentUser);
</script>
