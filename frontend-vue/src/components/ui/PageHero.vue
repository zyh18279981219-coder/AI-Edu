<template>
  <section class="hero-panel app-hero" :class="toneClass">
    <div class="app-hero-copy">
      <p v-if="eyebrow" class="eyebrow">{{ eyebrow }}</p>
      <h1>{{ title }}</h1>
      <p v-if="description" class="hero-desc">{{ description }}</p>
    </div>

    <div v-if="$slots.actions || badges.length" class="app-hero-side">
      <div v-if="badges.length" class="app-hero-badges">
        <span v-for="badge in badges" :key="badge" class="info-pill">{{ badge }}</span>
      </div>
      <div v-if="$slots.actions" class="app-hero-actions">
        <slot name="actions" />
      </div>
    </div>
  </section>
</template>

<script setup lang="ts">
import { computed } from "vue";

const props = withDefaults(
  defineProps<{
    eyebrow?: string;
    title: string;
    description?: string;
    badges?: string[];
    tone?: "default" | "learning" | "teacher" | "admin" | "industry";
  }>(),
  {
    eyebrow: "",
    description: "",
    badges: () => [],
    tone: "default",
  },
);

const toneClass = computed(() => `app-hero--${props.tone}`);
</script>
