<script setup lang="ts">
import {logoutUser} from "../api/login";
import router from "../router";
import i18n from "../locale";

defineProps({
  displayName: String
})

const language = ref('zh')

async function handleLogout() {
  await logoutUser();
  await router.push("/login");
}

function onSelectedLanguageChange(value: 'zh' | 'en') {
  language.value = value
  i18n.global.locale = value
  localStorage.setItem('locale', language.value)
}

onMounted(() => {
  const locale = localStorage.getItem('locale') == 'en' ? 'en' : 'zh'

  language.value = locale
  i18n.global.locale = locale
  localStorage.setItem('locale', locale)
})

</script>

<template>
  <el-select v-model="language" @change="onSelectedLanguageChange" style="width:100px;">
    <el-option key="0" value="zh" label="简体中文"/>
    <el-option key="1" value="en" label="English"/>
  </el-select>
  <RouterLink class="nav-user-name nav-profile-link" to="/student/profile">{{ displayName }}</RouterLink>
  <button class="ghost-btn" type="button" @click="handleLogout">{{ $t('layout.logout') }}</button>
</template>

<style scoped>

</style>