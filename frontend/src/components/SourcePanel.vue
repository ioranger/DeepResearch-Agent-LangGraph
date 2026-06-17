<template>
  <section class="panel source-panel">
    <header class="panel-head">
      <h2>来源</h2>
    </header>
    <section v-if="currentTaskSources.length" class="sources-block">
      <h3>来源</h3>
      <ul class="sources-list">
        <li v-for="item in currentTaskSources" :key="item.url || item.title" class="source-item">
          <a v-if="item.url" :href="item.url" target="_blank" rel="noopener" class="source-link">
            {{ item.title || item.url }}
          </a>
          <span v-else class="source-link">{{ item.title }}</span>
          <p v-if="item.snippet || item.raw" class="source-snippet">
            {{ item.snippet || item.raw }}
          </p>
        </li>
      </ul>
    </section>
    <p v-else class="source-placeholder">当前任务暂无来源，研究完成后会在这里展示。</p>
  </section>
</template>

<script lang="ts" setup>
import { useResearchStream } from "../composables/useResearchStream";
const { currentTaskSources } = useResearchStream();
</script>
