<template>
  <main class="app-shell" :class="{ expanded: isExpanded }">
    <div class="aurora" aria-hidden="true">
      <span></span>
      <span></span>
      <span></span>
    </div>

    <div v-if="!isExpanded" class="layout layout-centered">
      <TopicInput />
    </div>

    <div v-else class="layout layout-fullscreen">
      <aside class="sidebar">
        <TaskList />
      </aside>
      <section class="panel panel-result">
        <header class="status-bar">
          <div class="status-main">
            <span class="status-chip" :class="{ active: loading }">{{ loading ? "研究中" : "就绪" }}</span>
            <span class="status-meta">共 {{ totalTasks }} 个任务，已完成 {{ completedTasks }}</span>
          </div>
          <div class="status-controls">
            <button type="button" @click="startNewResearch">新建研究</button>
            <button type="button" @click="cancelResearch" :disabled="!loading">取消</button>
            <button type="button" @click="goBack">返回</button>
          </div>
        </header>

        <SourcePanel />
        <ReportView />
      </section>
    </div>

    <section v-if="error" class="error-banner">{{ error }}</section>
  </main>
</template>

<script lang="ts" setup>
import { onBeforeUnmount } from "vue";
import { useResearchStream } from "./composables/useResearchStream";
import TopicInput from "./components/TopicInput.vue";
import TaskList from "./components/TaskList.vue";
import SourcePanel from "./components/SourcePanel.vue";
import ReportView from "./components/ReportView.vue";

const {
  loading,
  error,
  isExpanded,
  totalTasks,
  completedTasks,
  cancelResearch,
  goBack,
  startNewResearch
} = useResearchStream();

onBeforeUnmount(() => {
  cancelResearch();
});
</script>
