<template>
  <div class="profile-shell-vue">
    <PageHero
        eyebrow="Profile"
        :title="$t('student.profile.personalCenter')"
        :description="$t('student.profile.personalCenterDescription')"
        :badges="heroBadges"
        tone="learning"
    />

    <section v-if="error" class="state-card error-state">
      <h2>{{ $t('student.profile.errorLoadingPersonalCenter') }}</h2>
      <p>{{ error }}</p>
    </section>

    <section v-else class="detail-grid profile-grid-vue">
      <article class="card-panel">
        <div class="section-head">
          <h2>{{ $t('student.profile.profile') }}</h2>
        </div>

        <form class="plan-form" @submit.prevent="saveProfile">
          <label>
            {{ $t('student.profile.username') }}
            <input :value="profile.username" type="text" disabled/>
          </label>
          <label>
            {{ $t('student.profile.name') }}
            <input :value="profile.name" type="text" disabled/>
          </label>
          <label class="wide">
            {{ $t('student.profile.email') }}
            <input v-model.trim="profile.email" type="email" :placeholder="$t('student.profile.emailPlaceholder')"/>
          </label>
          <label class="wide">
            {{ $t('student.profile.instructor') }}
            <input v-model.trim="profile.teacher" type="text" :placeholder="$t('student.profile.instructorPlaceholder')"/>
          </label>
          <label class="wide">
            {{ $t('student.profile.learningGoals') }}
            <textarea
                v-model.trim="goalText"
                rows="5"
                :placeholder="$t('student.profile.learningGoalsPlaceholder')"
            />
          </label>

          <p v-if="profileMessage" :class="profileSuccess ? 'muted' : 'form-error'">{{ profileMessage }}</p>

          <button type="submit" class="primary-link button-like full-width" :disabled="savingProfile">
            {{ savingProfile ? $t('student.profile.saving') : $t('student.profile.save') }}
          </button>
        </form>
      </article>

      <article class="card-panel">
        <div class="section-head">
          <h2>{{ $t('student.profile.accountSecurity') }}</h2>
        </div>

        <form class="plan-form" @submit.prevent="savePassword">
          <label class="wide">
            {{ $t('student.profile.currentPassword') }}
            <input v-model="passwordForm.current_password" type="password" :placeholder="$t('student.profile.currentPasswordPlaceHolder')"/>
          </label>
          <label class="wide">
            {{ $t('student.profile.newPassword') }}
            <input v-model="passwordForm.new_password" type="password" :placeholder="$t('student.profile.newPasswordPlaceholder')"/>
          </label>

          <p v-if="passwordMessage" :class="passwordSuccess ? 'muted' : 'form-error'">{{ passwordMessage }}</p>

          <button type="submit" class="ghost-btn full-width" :disabled="savingPassword">
            {{ savingPassword ? $t('student.profile.changingPassword') : $t('student.profile.changePassword') }}
          </button>
        </form>

        <div class="stack-list profile-info-stack">
          <div class="list-card">
            <div class="list-title">{{ $t('student.profile.currentIdentify') }}</div>
            <div class="list-meta">{{ profile.userType }}</div>
          </div>
          <div class="list-card">
            <div class="list-title">{{ $t('student.profile.numberOfGoals') }}</div>
            <div class="list-meta">{{ learningGoals.length }}</div>
          </div>
        </div>
      </article>
    </section>
  </div>
</template>

<script setup lang="ts">
import axios from "axios";
import {computed, onMounted, reactive, ref} from "vue";
import PageHero from "../../components/ui/PageHero.vue";
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
