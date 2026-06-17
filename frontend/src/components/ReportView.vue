<template>
  <section class="panel report-view">
    <header class="panel-head">
      <h2>报告</h2>
    </header>
        <section class="report-block">
      <h3>报告</h3>
      <div v-if="reportMarkdown" class="report-content" v-html="renderedReport" />
      <p v-else class="report-placeholder">研究进行中，报告完成后将在此显示…</p>
    </section>
  </section>
</template>

<script lang="ts" setup>
import { computed } from "vue";
import { marked } from "marked";
import { useResearchStream } from "../composables/useResearchStream";
const { reportMarkdown } = useResearchStream();
const renderedReport = computed(() => marked.parse(reportMarkdown.value, { async: false }) as string);
</script>
