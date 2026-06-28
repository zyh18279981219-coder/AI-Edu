<template>
  <article class="metric-card app-metric-card" :class="toneClass">
    <span class="metric-label">{{ label }}</span>
    <strong>{{ value }}</strong>
    <small v-if="description">{{ description }}</small>
  </article>
</template>

<script setup lang="ts">
import { computed } from "vue";

const props = withDefaults(
  defineProps<{
    label: string;
    value: string | number;
    description?: string;
    tone?: "default" | "success" | "warning" | "danger" | "brand";
  }>(),
  {
    description: "",
    tone: "default",
  },
);

const toneClass = computed(() => `app-metric-card--${props.tone}`);
</script>
