<script setup lang="ts">
import i18n from "../../locale";

defineProps({
  displayName: String
})

const language = ref('zh')

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
</template>

<style scoped>

</style>