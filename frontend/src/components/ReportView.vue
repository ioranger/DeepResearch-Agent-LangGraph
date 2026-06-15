<template>
  <section class="panel report-view">
    <header class="panel-head">
      <h2>报告</h2>
    </header>
        <section class="report-block">
      <h3>报告</h3>
      <div v-html="renderedReport" />
    </section>
  </section>
</template>

<script lang="ts" setup>
import { defineProps } from "vue";
import { computed } from "vue";
import { useResearchStream } from "../composables/useResearchStream";
const { reportMarkdown } = useResearchStream();
const renderedReport = computed(() => reportMarkdown.value);
</script>
