<template>
  <section class="admin-users">
    <div class="migration-grid teacher-metrics-grid">
      <article class="metric-card">
        <span class="metric-label">教师数量</span>
        <strong>{{ teachers.length }}</strong>
        <small>当前系统内可管理的教师账号。</small>
      </article>
      <article class="metric-card">
        <span class="metric-label">学生数量</span>
        <strong>{{ students.length }}</strong>
        <small>当前系统内可管理的学生账号。</small>
      </article>
      <article class="metric-card">
        <span class="metric-label">平均带教学生数</span>
        <strong>{{ averageStudentsPerTeacher }}</strong>
        <small>按教师账号下绑定的学生数计算。</small>
      </article>
      <article class="metric-card">
        <span class="metric-label">带学习目标学生</span>
        <strong>{{ studentsWithGoals }}</strong>
        <small>已经在学生档案中配置学习目标的人数。</small>
      </article>
    </div>

    <div class="card-panel admin-filter-bar">
      <div class="field">
        <span>搜索用户</span>
        <el-input v-model="searchValue" placeholder="搜索教师、学生或用户名" clearable />
      </div>
    </div>

    <div class="detail-grid">
      <section class="card-panel">
        <div class="section-head">
          <h2>教师管理</h2>
          <span class="muted">{{ filteredTeachers.length }} 位教师</span>
        </div>
        <div class="admin-user-grid">
          <article v-for="teacher in filteredTeachers" :key="teacher.username" class="admin-user-card">
            <div class="admin-user-head">
              <div class="admin-avatar">{{ teacher.name?.slice(0, 1) || teacher.username.slice(0, 1) }}</div>
              <div>
                <strong>{{ teacher.name || teacher.username }}</strong>
                <p>{{ teacher.email || "未提供邮箱" }}</p>
              </div>
            </div>
            <div class="admin-user-meta">
              <span class="meta-chip">用户名：{{ teacher.username }}</span>
              <span class="meta-chip">学生数：{{ teacher.students.length }}</span>
            </div>
            <div class="admin-tag-list">
              <span v-for="student in teacher.students" :key="student" class="skill-chip">{{ student }}</span>
            </div>
          </article>
        </div>
      </section>

      <section class="card-panel">
        <div class="section-head">
          <h2>学生管理</h2>
          <span class="muted">{{ filteredStudents.length }} 位学生</span>
        </div>
        <div class="admin-user-grid">
          <article v-for="student in filteredStudents" :key="student.username" class="admin-user-card">
            <div class="admin-user-head">
              <div class="admin-avatar">{{ student.stu_name?.slice(0, 1) || student.username.slice(0, 1) }}</div>
              <div>
                <strong>{{ student.stu_name || student.username }}</strong>
                <p>{{ student.email || "未提供邮箱" }}</p>
              </div>
            </div>
            <div class="admin-user-meta">
              <span class="meta-chip">用户名：{{ student.username }}</span>
              <span class="meta-chip">指导教师：{{ student.teacher || "未绑定" }}</span>
            </div>
            <div class="admin-tag-list">
              <span v-for="goal in student.learning_goals || []" :key="goal" class="skill-chip">{{ goal }}</span>
            </div>
          </article>
        </div>
      </section>
    </div>
  </section>
</template>

<script setup lang="ts">
import { computed } from "vue";
import type { AdminStudentRecord, AdminTeacherRecord } from "../../../api/studentTwin";

const searchValue = defineModel<string>("search", { default: "" });

const props = defineProps<{
  teachers: AdminTeacherRecord[];
  students: AdminStudentRecord[];
}>();

const averageStudentsPerTeacher = computed(() => {
  if (!props.teachers.length) return "0";
  const total = props.teachers.reduce((sum, teacher) => sum + (teacher.students?.length ?? 0), 0);
  return (total / props.teachers.length).toFixed(1);
});

const studentsWithGoals = computed(() => props.students.filter((student) => (student.learning_goals ?? []).length > 0).length);

const filteredTeachers = computed(() => {
  const keyword = searchValue.value.trim().toLowerCase();
  if (!keyword) return props.teachers;
  return props.teachers.filter((teacher) => {
    const text = [teacher.name, teacher.username, teacher.email, ...(teacher.students ?? [])].filter(Boolean).join(" ").toLowerCase();
    return text.includes(keyword);
  });
});

const filteredStudents = computed(() => {
  const keyword = searchValue.value.trim().toLowerCase();
  if (!keyword) return props.students;
  return props.students.filter((student) => {
    const courseTypes = student.preference?.course_type?.map((item) => item?.name ?? "").join(" ") ?? "";
    const text = [
      student.stu_name,
      student.username,
      student.email,
      student.teacher,
      ...(student.learning_goals ?? []),
      courseTypes,
    ]
      .filter(Boolean)
      .join(" ")
      .toLowerCase();
    return text.includes(keyword);
  });
});
</script>
