<template>
  <section class="panel task-list">
    <header class="panel-head">
      <h2>任务列表</h2>
    </header>
        <aside class="tasks-list">
      <h3>研究任务</h3>
      <ul>
        <li v-for="task in todoTasks" :key="task.id">
          <header class="task-header">
            <span class="task-title">{{ task.title }}</span>
            <span class="task-status" :class="task.status">{{ formatTaskStatus(task.status) }}</span>
          </header>
          <p class="task-intent">{{ task.intent }}</p>
        </li>
      </ul>
    </aside>
  </section>
</template>

<script lang="ts" setup>
import { defineProps } from "vue";
import { useResearchStream } from "../composables/useResearchStream";
import { formatTaskStatus } from "../composables/useResearchStream";
const { todoTasks } = useResearchStream();
</script>
