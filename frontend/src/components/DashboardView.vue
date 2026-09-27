<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { request, errorMessage } from '../api/client'
import SummaryCards from './SummaryCards.vue'
import type { User, Summary } from '../types'

defineProps<{
  user: User
  isLoggingOut: boolean
}>()

const emit = defineEmits<{
  logout: []
}>()

const summary = ref<Summary | null>(null)
const isSummaryLoading = ref(true)
const summaryError = ref('')

async function loadSummary(year: number, month: number) {
  isSummaryLoading.value = true
  summaryError.value = ''

  try {
    summary.value = await request<Summary>(`/api/summary?year=${year}&month=${month}`)
  } catch (error) {
    console.error(error)
    summaryError.value = errorMessage(error, '读取月度汇总失败。')
  } finally {
    isSummaryLoading.value = false
  }
}

onMounted(() => {
  const now = new Date()
  loadSummary(now.getFullYear(), now.getMonth() + 1)
})
</script>

<template>
  <main class="app">
    <header>
      <div class="brand">
        <span class="brand-mark"></span>
        Tallywise
      </div>

      <div class="header-right">
        <div class="user-info">
          <span class="user-nickname">
            {{ user.nickname }}
          </span>

          <span class="user-email">
            {{ user.email }}
          </span>
        </div>

        <button
          class="logout-button"
          type="button"
          :disabled="isLoggingOut"
          @click="emit('logout')"
        >
          {{ isLoggingOut ? '退出中…' : '退出登录' }}
        </button>
      </div>
    </header>

    <section class="greeting">
      <h1>你的财务，一目了然。</h1>
      <p>记录每一笔微小的流动，让生活保持从容。</p>
    </section>

    <SummaryCards
      :summary="summary"
      :is-loading="isSummaryLoading"
      :error-message="summaryError"
      period-label="本月"
    />
  </main>
</template>
