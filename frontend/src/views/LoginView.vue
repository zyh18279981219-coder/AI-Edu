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
          <span>以课程图谱为底座</span>
          <span>闭环刻画学生成长</span>
        </h1>
        <p>
          将课程知识图谱、学习资源、测验作业和互动证据接入同一条教学链路，持续生成学生画像、个性化学习路径与教师干预建议。
        </p>
      </div>

      <div class="login-academic-panel" aria-label="平台能力闭环">
        <div class="login-loop-panel">
          <div class="login-loop-head">
            <span>平台创新闭环</span>
            <strong>从课程结构到教学决策，数据不再停在记录层</strong>
          </div>
          <ol class="login-loop-list">
            <li>
              <span class="login-loop-code">课程底座</span>
              <strong>课程图谱底座</strong>
              <p>发布课程知识图谱，统一知识点、作业、资源和职业能力映射。</p>
            </li>
            <li>
              <span class="login-loop-code">学习证据</span>
              <strong>学生画像</strong>
              <p>汇聚测验、作业、5E 互动和资源学习行为，形成可追踪画像。</p>
            </li>
            <li>
              <span class="login-loop-code">智能推荐</span>
              <strong>个性化路径</strong>
              <p>按整体学习情况推荐知识点顺序，并匹配 B站、YouTube、CSDN 与教师资源。</p>
            </li>
            <li>
              <span class="login-loop-code">教师决策</span>
              <strong>干预与课程优化</strong>
              <p>面向风险学生、薄弱知识点和课程运行效果生成教师可确认的建议。</p>
            </li>
          </ol>
        </div>

        <div class="academic-overview">
          <strong>核心能力</strong>
          <div>
            <span>课程图谱发布</span>
            <span>资源证据回流</span>
            <span>学生画像诊断</span>
            <span>学习路径推荐</span>
            <span>教师干预闭环</span>
            <span>职业能力映射</span>
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
