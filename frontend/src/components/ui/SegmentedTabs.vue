<template>
  <div class="app-segmented-tabs">
    <el-segmented
      :model-value="modelValue"
      :options="tabs"
      @update:model-value="handleChange"
    />
  </div>
</template>

<script setup lang="ts">
defineProps<{
  modelValue: string;
  tabs: Array<{ label: string; value: string }>;
}>();

const emit = defineEmits<{
  (event: "update:modelValue", value: string): void;
}>();

function handleChange(value: string | number | boolean) {
  emit("update:modelValue", String(value));
}
</script>
