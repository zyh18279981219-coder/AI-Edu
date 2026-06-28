<template>
  <div class="login-shell">
    <div class="login-locale">
      <LocaleSelection />
    </div>

    <section class="login-product" aria-label="AI-Education 平台入口">
      <div class="login-brand-block">
        <span class="login-mark">AE</span>
        <div>
          <strong>AI-Education</strong>
          <span>智能教学决策平台</span>
        </div>
      </div>

      <div class="login-product-copy">
        <p class="eyebrow">Digital Twin & Agent Platform</p>
        <h1>
          <span>以学生数字孪生</span>
          <span>驱动智能教学协同</span>
        </h1>
        <p>
          不只是管理课程和作业，而是持续刻画学生学习状态，并由智能体辅助完成诊断、推荐、干预与教研决策。
        </p>
      </div>

      <div class="login-academic-panel" aria-hidden="true">
        <div class="academic-steps">
          <article>
            <strong>学生数字孪生</strong>
            <span>融合课程学习、测验作业、互动记录与资源使用行为，形成可追踪的学习画像</span>
            <i style="--bar-width: 88%"></i>
            <i style="--bar-width: 62%"></i>
          </article>
          <article>
            <strong>智能体诊断推荐</strong>
            <span>基于知识点掌握度与学习偏好，自动生成学习路径并匹配视频、讲义和资料</span>
            <i style="--bar-width: 72%"></i>
            <i style="--bar-width: 54%"></i>
          </article>
          <article>
            <strong>教师干预与教研</strong>
            <span>智能体汇总风险学生、干预建议、行业情报和教研材料，辅助教师决策</span>
            <i style="--bar-width: 80%"></i>
            <i style="--bar-width: 68%"></i>
          </article>
        </div>

        <div class="academic-overview">
          <strong>相比传统教学平台新增能力</strong>
          <div>
            <span>学生画像建模</span>
            <span>知识点诊断</span>
            <span>个性化路径</span>
            <span>智能资源推荐</span>
            <span>干预建议生成</span>
            <span>多智能体协同</span>
          </div>
        </div>
      </div>
    </section>

    <section class="login-card">
      <p class="eyebrow">统一身份认证</p>
      <h2>进入系统</h2>
      <p class="login-desc">请使用平台账号登录对应工作台。</p>

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
            <el-option :label="$t('login.admin')" value="admin"/>
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
import {useRoute, useRouter} from "vue-router";
import type {LoginForm} from "../types/login";
import {loginUser} from "../api/login";
import i18n from '../locale/index';

const {t}=i18n.global
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
    error.value = t('login.emptyUsernameAndPassword');
    return;
  }

  submitting.value = true;
  error.value = "";

  try {
    await loginUser(form);
    const redirect = typeof route.query.redirect === "string" ? route.query.redirect : "";
    if (redirect && isRedirectAllowedForRole(redirect, form.user_type)) {
      await router.replace(redirect);
    } else if (form.user_type === "teacher") {
      await router.replace("/teacher/dashboard");
    } else if (form.user_type === "admin") {
      await router.replace("/admin/dashboard");
    } else {
      await router.replace("/student/home");
    }
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

function isRedirectAllowedForRole(redirect: string, userType: LoginForm["user_type"]) {
  const rolePrefix: Record<LoginForm["user_type"], string> = {
    student: "/student",
    teacher: "/teacher",
    admin: "/admin",
  };
  return redirect.startsWith(rolePrefix[userType]);
}

</script>

<style scoped>

</style>
