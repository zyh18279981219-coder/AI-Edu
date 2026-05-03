<template>
  <div class="student-intervention-shell">
    <section class="hero-panel app-hero app-hero--learning">
      <div class="app-hero-copy">
        <p class="eyebrow">Personalized Pack</p>
        <h1>教师推送任务包</h1>
        <p class="hero-desc">仅你可见。点击“进入作答”后可逐题完成，系统会自动计算进度。</p>
      </div>
      <div class="app-hero-actions">
        <button class="ghost-btn" type="button" :disabled="loading" @click="loadAll">刷新</button>
      </div>
    </section>

    <section v-if="error" class="card-panel state-card error-state">{{ error }}</section>

    <section class="card-panel">
      <div class="section-head">
        <h3>我的任务包</h3>
        <span class="muted">共 {{ packages.length }} 个</span>
      </div>

      <div class="industry-table-wrap">
        <table class="industry-table">
          <thead>
            <tr>
              <th>任务包</th>
              <th>教师</th>
              <th>状态</th>
              <th>进度</th>
              <th>题目数</th>
              <th>更新时间</th>
              <th>操作</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="pkg in packages" :key="pkg.id">
              <td>{{ pkg.id.slice(0, 8) }}</td>
              <td>{{ pkg.teacher_username }}</td>
              <td>{{ statusLabel(pkg.student_status) }}</td>
              <td>
                {{ progressText(pkg) }}
              </td>
              <td>{{ pkg.questions?.length ?? 0 }}</td>
              <td>{{ formatTime(pkg.updated_at) }}</td>
              <td>
                <button class="ghost-btn" type="button" @click="goToDetail(pkg.id)">进入作答</button>
              </td>
            </tr>
            <tr v-if="!packages.length">
              <td colspan="7">暂无教师推送任务包</td>
            </tr>
          </tbody>
        </table>
      </div>
    </section>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from "vue";
import { useRouter } from "vue-router";
import { interventionStudentPackages } from "../../api/intervention";
import type { InterventionPackage } from "../../types/intervention";

const router = useRouter();
const loading = ref(false);
const error = ref("");
const packages = ref<InterventionPackage[]>([]);

function statusLabel(status: string) {
  if (status === "accepted") return "已接受";
  if (status === "declined") return "暂不做";
  if (status === "in_progress") return "进行中";
  if (status === "completed") return "已完成";
  return "待处理";
}

function formatTime(value?: string) {
  if (!value) return "-";
  return new Date(value).toLocaleString();
}

function progressText(pkg: InterventionPackage) {
  const rate = Math.round((pkg.progress?.completion_rate || 0) * 100);
  const answered = pkg.progress?.answered_questions ?? 0;
  const total = pkg.progress?.total_questions ?? (pkg.questions?.length || 0);
  return `${rate}% (${answered}/${total})`;
}

function goToDetail(packageId: string) {
  router.push({ name: "student-intervention-detail", params: { packageId } });
}

async function loadAll() {
  loading.value = true;
  error.value = "";
  try {
    const res = await interventionStudentPackages();
    packages.value = res.packages || [];
  } catch (e) {
    error.value = e instanceof Error ? e.message : "加载任务包失败";
  } finally {
    loading.value = false;
  }
}

onMounted(loadAll);
</script>

<style scoped>
.student-intervention-shell {
  display: grid;
  gap: 16px;
}
</style>

