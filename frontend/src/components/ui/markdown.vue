<script setup lang="ts">
import Markdown from 'markdown-it';

const props=defineProps({
  content:{
    type:String,
    required:true
  }
});

const md= new Markdown();
const mdHTML=computed(()=>md.render(props.content));
</script>

<template>
 <div v-html="mdHTML"/>
</template>

<style scoped>

</style>