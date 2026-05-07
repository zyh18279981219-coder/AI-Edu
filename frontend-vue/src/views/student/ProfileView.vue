<template>
  <div class="profile-shell-vue">
    <!-- 页面头部 -->
    <div class="student-profile-v2-header">
      <div>
        <h1>⚙️ 个人中心设置</h1>
        <p class="student-profile-v2-desc">管理个人资料和账户安全</p>
      </div>
    </div>

    <section v-if="error" class="state-card error-state">
      <h2>{{ $t('student.profile.errorLoadingPersonalCenter') }}</h2>
      <p>{{ error }}</p>
    </section>

    <section v-else class="student-profile-v2-layout">
      <!-- 账户概览 -->
      <div class="student-profile-v2-overview">
        <div class="student-profile-v2-overview-header">
          <div class="student-profile-v2-avatar">
            <span>{{ profile.name ? profile.name.charAt(0).toUpperCase() : profile.username.charAt(0).toUpperCase() }}</span>
          </div>
          <div class="student-profile-v2-user-info">
            <h2>{{ profile.name || profile.username }}</h2>
            <p class="muted">@{{ profile.username }}</p>
          </div>
        </div>
        
        <div class="student-profile-v2-stats">
          <div class="student-profile-v2-stat-item">
            <div class="student-profile-v2-stat-label">身份</div>
            <div class="student-profile-v2-stat-value">{{ profile.userType || 'student' }}</div>
          </div>
          <div class="student-profile-v2-stat-item">
            <div class="student-profile-v2-stat-label">学习目标</div>
            <div class="student-profile-v2-stat-value">{{ learningGoals.length }}</div>
          </div>
        </div>
      </div>

      <!-- 表单区域 -->
      <div class="student-profile-v2-forms">
        <!-- 个人资料 -->
        <article class="student-profile-v2-card">
          <div class="student-profile-v2-card-header">
            <h2>{{ $t('student.profile.profile') }}</h2>
            <span class="muted">更新个人信息</span>
          </div>

          <form class="student-profile-v2-form" @submit.prevent="saveProfile">
            <label>
              <span>{{ $t('student.profile.username') }}</span>
              <input :value="profile.username" type="text" disabled/>
            </label>
            <label>
              <span>{{ $t('student.profile.name') }}</span>
              <input :value="profile.name" type="text" disabled/>
            </label>
            <label class="wide">
              <span>{{ $t('student.profile.email') }}</span>
              <input v-model.trim="profile.email" type="email" :placeholder="$t('student.profile.emailPlaceholder')"/>
            </label>
            <label class="wide">
              <span>{{ $t('student.profile.instructor') }}</span>
              <input v-model.trim="profile.teacher" type="text" :placeholder="$t('student.profile.instructorPlaceholder')"/>
            </label>
            <label class="wide">
              <span>{{ $t('student.profile.learningGoals') }}</span>
              <textarea
                  v-model.trim="goalText"
                  rows="5"
                  :placeholder="$t('student.profile.learningGoalsPlaceholder')"
              />
            </label>

            <p v-if="profileMessage" :class="profileSuccess ? 'student-profile-v2-success' : 'student-profile-v2-error'">
              {{ profileMessage }}
            </p>

            <button type="submit" class="primary-link button-like full-width" :disabled="savingProfile">
              {{ savingProfile ? $t('student.profile.saving') : $t('student.profile.save') }}
            </button>
          </form>
        </article>

        <!-- 账户安全 -->
        <article class="student-profile-v2-card">
          <div class="student-profile-v2-card-header">
            <h2>{{ $t('student.profile.accountSecurity') }}</h2>
            <span class="muted">修改登录密码</span>
          </div>

          <form class="student-profile-v2-form" @submit.prevent="savePassword">
            <label class="wide">
              <span>{{ $t('student.profile.currentPassword') }}</span>
              <input v-model="passwordForm.current_password" type="password" :placeholder="$t('student.profile.currentPasswordPlaceHolder')"/>
            </label>
            <label class="wide">
              <span>{{ $t('student.profile.newPassword') }}</span>
              <input v-model="passwordForm.new_password" type="password" :placeholder="$t('student.profile.newPasswordPlaceholder')"/>
            </label>

            <p v-if="passwordMessage" :class="passwordSuccess ? 'student-profile-v2-success' : 'student-profile-v2-error'">
              {{ passwordMessage }}
            </p>

            <button type="submit" class="ghost-btn full-width" :disabled="savingPassword">
              {{ savingPassword ? $t('student.profile.changingPassword') : $t('student.profile.changePassword') }}
            </button>
          </form>
        </article>
      </div>
    </section>
  </div>
</template>

<script setup lang="ts">
import axios from "axios";
import {computed, onMounted, reactive, ref} from "vue";
import {fetchCurrentUser} from "../../api/login";
import {changeStudentPassword, updateStudentProfile} from "../../api/student";
import type { UserProfile, PasswordForm, ProfileResponse, UserAccount } from "../../types/student";
import i18n from "../../locale";

const { t } = i18n.global;

const loading = ref(true);
const error = ref("");
const savingProfile = ref(false);
const savingPassword = ref(false);
const profileMessage = ref("");
const passwordMessage = ref("");
const profileSuccess = ref(false);
const passwordSuccess = ref(false);

const profile = reactive<UserProfile>({
  username: "",
  name: "",
  email: "",
  teacher: "",
  userType: "",
});

const goalText = ref("");
const passwordForm = reactive<PasswordForm>({
  current_password: "",
  new_password: "",
});

const learningGoals = computed(() =>
    goalText.value
        .split(/\r?\n/)
        .map((item) => item.trim())
        .filter(Boolean),
);

const heroBadges = computed(() => [
  `${t('student.profile.user')} ${profile.username || t('student.profile.noUser')}`,
  `${t('student.profile.goals')} ${learningGoals.value.length}`,
  `${t('student.profile.identify')} ${profile.userType || "student"}`,
]);

async function loadProfile() {
  loading.value = true;
  error.value = "";
  try {
    const user = (await fetchCurrentUser()) as UserAccount;
    profile.username = user.username;
    profile.userType = user.user_type;
    profile.name = String(user.user_data["stu_name"] ?? user.user_data["name"] ?? user.username ?? "");
    profile.email = String(user.user_data["email"] ?? "");
    profile.teacher = String(user.user_data["teacher"] ?? "");
    const goals = Array.isArray(user.user_data["learning_goals"]) ? (user.user_data["learning_goals"] as string[]) : [];
    goalText.value = goals.join("\n");
  } catch (err) {
    error.value = err instanceof Error ? err.message : t('student.profile.errorLoadingPersonalCenter');
  } finally {
    loading.value = false;
  }
}

async function saveProfile() {
  savingProfile.value = true;
  profileMessage.value = "";
  profileSuccess.value = false;
  try {
    const data: ProfileResponse = await updateStudentProfile({
      email: profile.email,
      teacher: profile.teacher,
      learning_goals: learningGoals.value,
    });
    profileMessage.value = data.message || t('student.profile.successfullySavingProfile');
    profileSuccess.value = !!data.success;
  } catch (err) {
    profileMessage.value = resolveError(err, t('student.profile.errorSavingProfile'));
    profileSuccess.value = false;
  } finally {
    savingProfile.value = false;
  }
}

async function savePassword() {
  if (!passwordForm.current_password || !passwordForm.new_password) {
    passwordMessage.value = t('student.profile.noPassword');
    passwordSuccess.value = false;
    return;
  }
  savingPassword.value = true;
  passwordMessage.value = "";
  passwordSuccess.value = false;
  try {
    const data: ProfileResponse = await changeStudentPassword(passwordForm);
    passwordMessage.value = data.message || t('student.profile.successfullyChangingPassword');
    passwordSuccess.value = !!data.success;
    passwordForm.current_password = "";
    passwordForm.new_password = "";
  } catch (err) {
    passwordMessage.value = resolveError(err, t('student.profile.errorChangingPassword'));
    passwordSuccess.value = false;
  } finally {
    savingPassword.value = false;
  }
}

function resolveError(err: unknown, fallback: string) {
  if (axios.isAxiosError(err)) {
    return err.response?.data?.detail || err.message || fallback;
  }
  return err instanceof Error ? err.message : fallback;
}

onMounted(() => {
  void loadProfile();
});
</script>
