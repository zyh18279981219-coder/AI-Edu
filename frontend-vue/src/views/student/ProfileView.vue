<template>
  <div class="profile-shell-vue">
    <PageHero
        eyebrow="Profile"
        title="个人中心"
        description="在这里维护学生基本信息、学习目标和账户密码。"
        :badges="heroBadges"
        tone="learning"
    />

    <section v-if="error" class="state-card error-state">
      <h2>个人中心加载失败</h2>
      <p>{{ error }}</p>
    </section>

    <section v-else class="detail-grid profile-grid-vue">
      <article class="card-panel">
        <div class="section-head">
          <h2>基本信息</h2>
        </div>

        <form class="plan-form" @submit.prevent="saveProfile">
          <label>
            用户名
            <input :value="profile.username" type="text" disabled/>
          </label>
          <label>
            姓名
            <input :value="profile.name" type="text" disabled/>
          </label>
          <label class="wide">
            邮箱
            <input v-model.trim="profile.email" type="email" placeholder="请输入邮箱"/>
          </label>
          <label class="wide">
            指导教师
            <input v-model.trim="profile.teacher" type="text" placeholder="请输入教师用户名或姓名"/>
          </label>
          <label class="wide">
            学习目标
            <textarea
                v-model.trim="goalText"
                rows="5"
                placeholder="每行一个学习目标，例如：掌握 Python 数据分析"
            />
          </label>

          <p v-if="profileMessage" :class="profileSuccess ? 'muted' : 'form-error'">{{ profileMessage }}</p>

          <button type="submit" class="primary-link button-like full-width" :disabled="savingProfile">
            {{ savingProfile ? "保存中..." : "保存资料" }}
          </button>
        </form>
      </article>

      <article class="card-panel">
        <div class="section-head">
          <h2>账户安全</h2>
        </div>

        <form class="plan-form" @submit.prevent="savePassword">
          <label class="wide">
            当前密码
            <input v-model="passwordForm.current_password" type="password" placeholder="请输入当前密码"/>
          </label>
          <label class="wide">
            新密码
            <input v-model="passwordForm.new_password" type="password" placeholder="请输入新密码"/>
          </label>

          <p v-if="passwordMessage" :class="passwordSuccess ? 'muted' : 'form-error'">{{ passwordMessage }}</p>

          <button type="submit" class="ghost-btn full-width" :disabled="savingPassword">
            {{ savingPassword ? "修改中..." : "修改密码" }}
          </button>
        </form>

        <div class="stack-list profile-info-stack">
          <div class="list-card">
            <div class="list-title">当前身份</div>
            <div class="list-meta">{{ profile.userType }}</div>
          </div>
          <div class="list-card">
            <div class="list-title">学习目标数</div>
            <div class="list-meta">{{ learningGoals.length }} 项</div>
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
import {fetchCurrentUser,} from "../../api/client";
import {changeStudentPassword, updateStudentProfile} from "../../api/student";
import type { UserProfile, PasswordForm, ProfileResponse, UserAccount } from "../../types/student";

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
  `用户 ${profile.username || "未加载"}`,
  `目标 ${learningGoals.value.length}`,
  `身份 ${profile.userType || "student"}`,
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
    error.value = err instanceof Error ? err.message : "个人中心加载失败";
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
    profileMessage.value = data.message || "资料已更新";
    profileSuccess.value = !!data.success;
  } catch (err) {
    profileMessage.value = resolveError(err, "资料保存失败");
    profileSuccess.value = false;
  } finally {
    savingProfile.value = false;
  }
}

async function savePassword() {
  if (!passwordForm.current_password || !passwordForm.new_password) {
    passwordMessage.value = "请填写当前密码和新密码";
    passwordSuccess.value = false;
    return;
  }
  savingPassword.value = true;
  passwordMessage.value = "";
  passwordSuccess.value = false;
  try {
    const data: ProfileResponse = await changeStudentPassword(passwordForm);
    passwordMessage.value = data.message || "密码修改成功";
    passwordSuccess.value = !!data.success;
    passwordForm.current_password = "";
    passwordForm.new_password = "";
  } catch (err) {
    passwordMessage.value = resolveError(err, "密码修改失败");
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
