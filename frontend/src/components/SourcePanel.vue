<template>
  <section class="panel source-panel">
    <header class="panel-head">
      <h2>来源</h2>
    </header>
        <section v-if="currentTaskSources.length" class="sources-block">
      <h3>来源</h3>
      <ul class="sources-list">
        <li v-for="item in currentTaskSources" :key="item.url" class="source-item">
          <a :href="item.url" target="_blank" rel="noopener" class="source-link">
            {{ item.title || item.url }}
          </a>
          <div v-if="item.snippet || item.raw" class="source-tooltip">
            {{ item.snippet || item.raw }}
          </div>
        </li>
      </ul>
    </section>
  </section>
</template>

<script lang="ts" setup>
import { defineProps } from "vue";
import { useResearchStream } from "../composables/useResearchStream";
const { currentTaskSources } = useResearchStream();
</script>
