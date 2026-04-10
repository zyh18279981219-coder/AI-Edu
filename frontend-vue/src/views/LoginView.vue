<template>
  <div class="login-shell">
    <section class="login-card">
      <p class="eyebrow">Vue 登录</p>
      <h1>登录 AI-Education</h1>
      <p class="login-desc">这是前后端分离版的登录页，当前已接入学生、教师和管理端统一登录。</p>

      <form class="login-form" @submit.prevent="handleSubmit">
        <label>
          <span>{{ $t('login.username') }}</span>
          <el-input v-model="form.username" :placeholder="$t('login.usernamePlaceholder')" clearable/>
        </label>

        <label>
          <span>{{ $t('login.password') }}</span>
          <el-input v-model="form.password" type="password" show-password :placeholder="$t('login.passwordPlaceholder')"/>
        </label>

        <label>
          <span>{{ $t('login.userType') }}</span>
          <el-select v-model="form.user_type" :placeholder="$t('login.userTypePlaceholder')">
            <el-option :label="$t('login.student')" value="student"/>
            <el-option :label="$t('login.teacher')" value="teacher"/>
            <el-option :label="$t('login.teacher')" value="admin"/>
          </el-select>
        </label>

        <p v-if="error" class="form-error">{{ error }}</p>

        <el-button class="full-width" type="primary" size="large" :loading="submitting" native-type="submit">
          {{ submitting ? $t('login.doLogin') : $t('login.login') }}
        </el-button>
      </form>
    </section>
  </div>
</template>

<script setup lang="ts">
import axios from "axios";
import {reactive, ref} from "vue";
import type {LoginForm} from "../types/login";
import {loginUser} from "../api/login";
import i18n from '../locale/index';

const {t}=i18n.global

const submitting = ref(false);
const error = ref("");
const form = reactive<LoginForm>({
  username: "",
  password: "",
  user_type: "student",
});

async function handleSubmit() {
  if (!form.username || !form.password) {
    error.value = t('login.emptyUsernameAndPassword');
    return;
  }

  submitting.value = true;
  error.value = "";

  try {
    await loginUser(form);

    window.location.reload();
  } catch (err) {
    if (axios.isAxiosError(err)) {
      error.value = err.response?.data?.detail || err.message || t('login.loginFailed');
    } else {
      error.value = err instanceof Error ? err.message : t('login.loginFailed');
    }
  } finally {
    submitting.value = false;
  }
}

</script>
