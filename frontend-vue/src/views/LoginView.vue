<template>
  <div class="login-shell">
    <section class="login-card">
      <p class="eyebrow">Vue 登录</p>
      <h1>登录 AI-Education</h1>
      <p class="login-desc">这是前后端分离版的登录页，当前已接入学生、教师和管理端统一登录。</p>

      <form class="login-form" @submit.prevent="handleSubmit">
        <label>
          <span>用户名</span>
          <el-input v-model="form.username" placeholder="请输入用户名" clearable/>
        </label>

        <label>
          <span>密码</span>
          <el-input v-model="form.password" type="password" show-password placeholder="请输入密码"/>
        </label>

        <label>
          <span>用户类型</span>
          <el-select v-model="form.user_type" placeholder="请选择用户类型">
            <el-option label="学生" value="student"/>
            <el-option label="教师" value="teacher"/>
            <el-option label="管理员" value="admin"/>
          </el-select>
        </label>

        <p v-if="error" class="form-error">{{ error }}</p>

        <el-button class="full-width" type="primary" size="large" :loading="submitting" native-type="submit">
          {{ submitting ? "登录中..." : "登录" }}
        </el-button>
      </form>
    </section>
  </div>
</template>

<script setup lang="ts">
import axios from "axios";
import {reactive, ref} from "vue";
import {useRoute, useRouter} from "vue-router";
import {apiClient} from "../api/client";
import type {LoginForm, LoginResponse} from "../types/login";
import {loginUser} from "../api/login";

const router = useRouter();
const route = useRoute();
const submitting = ref(false);
const error = ref("");
const form = reactive<LoginForm>({
  username: "",
  password: "",
  user_type: "student",
});

async function handleSubmit() {
  if (!form.username || !form.password) {
    error.value = "请输入用户名和密码";
    return;
  }

  submitting.value = true;
  error.value = "";

  try {
    await loginUser(form);

    window.location.reload();
  } catch (err) {
    if (axios.isAxiosError(err)) {
      error.value = err.response?.data?.detail || err.message || "登录失败";
    } else {
      error.value = err instanceof Error ? err.message : "登录失败";
    }
  } finally {
    submitting.value = false;
  }
}

</script>
