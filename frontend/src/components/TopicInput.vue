<template>
  <section class="panel topic-input">
    <header class="panel-head">
      <h2>输入研究主题</h2>
    </header>
        <form class="form" @submit.prevent="submit">
      <label class="field">
        <span>研究主题</span>
        <textarea
          v-model="form.topic"
          placeholder="例如：探索多模态模型在 2025 年的关键突破"
          rows="4"
          required
        ></textarea>
      </label>
      <section class="options">
        <label class="field option">
          <span>搜索引擎</span>
          <select v-model="form.searchApi">
            <option value="">沿用后端配置</option>
            <option v-for="option in searchOptions" :key="option" :value="option">
              {{ option }}
            </option>
          </select>
        </label>
      </section>
      <div class="form-actions">
        <button type="submit" :disabled="loading">
          {{ loading ? "正在研究…" : "开始研究" }}
        </button>
      </div>
    </form>
  </section>
</template>

<script lang="ts" setup>
import { defineProps } from "vue";
import { useResearchStream } from "../composables/useResearchStream";
const { form, loading, submit, searchOptions } = useResearchStream();
</script>
