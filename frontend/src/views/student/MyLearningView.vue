<template>
  <main class="path-page-shell">
    <section class="path-page-heading">
      <div>
        <p class="path-page-eyebrow">Personalized Learning Path</p>
        <h1>个性化学习路径</h1>
        <p>
          根据学生画像、课程学习进度、测验作业与资源学习证据，生成后续学习顺序和配套资源推荐。
        </p>
      </div>
    </section>

    <PersonalizedPathPanel />
  </main>
</template>

<script setup lang="ts">
import PersonalizedPathPanel from "./components/PersonalizedPathPanel.vue";
</script>

<style scoped>
.path-page-shell {
  min-height: 100%;
  padding: 28px;
  background: #f6f8fb;
}

.path-page-heading {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: 20px;
  max-width: 1280px;
  margin: 0 auto 18px;
}

.path-page-eyebrow {
  margin: 0 0 8px;
  color: #2563eb;
  font-size: 12px;
  font-weight: 800;
  letter-spacing: 0;
  text-transform: uppercase;
}

.path-page-heading h1 {
  margin: 0;
  color: #0f172a;
  font-size: 28px;
  font-weight: 800;
  letter-spacing: 0;
}

.path-page-heading p:last-child {
  max-width: 760px;
  margin: 8px 0 0;
  color: #475569;
  font-size: 15px;
  line-height: 1.7;
}

@media (max-width: 720px) {
  .path-page-shell {
    padding: 18px;
  }

  .path-page-heading {
    align-items: flex-start;
    flex-direction: column;
  }

  .path-page-heading h1 {
    font-size: 24px;
  }
}
</style>
