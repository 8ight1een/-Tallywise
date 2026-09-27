<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { request, errorMessage } from '../api/client'
import SummaryCards from './SummaryCards.vue'
import TransactionList from './TransactionList.vue'
import type { User, Summary, Transaction, Category, MonthSelection } from '../types'

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
const selectedPeriod = ref<MonthSelection>('current')
const periodLabel = computed(() =>
  selectedPeriod.value === 'current' ? '本月' : `${selectedPeriod.value}月`,
)
const transactions = ref<Transaction[]>([])
const categories = ref<Category[]>([])
const isTransactionsLoading = ref(true)
const transactionsError = ref('')

function getQueryPeriod() {
  const now = new Date()
  return {
    year: now.getFullYear(),
    month: selectedPeriod.value === 'current' ? now.getMonth() + 1 : selectedPeriod.value,
  }
}

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

async function loadTransactions(year: number, month: number) {
  isTransactionsLoading.value = true
  transactionsError.value = ''

  try {
    const [records, incomeCategories, expenseCategories] = await Promise.all([
      request<Transaction[]>(`/api/transactions/${year}/${month}`),
      request<Category[]>(`/api/categories?money_type=${encodeURIComponent('收入')}`),
      request<Category[]>(`/api/categories?money_type=${encodeURIComponent('支出')}`),
    ])
    transactions.value = records
    categories.value = [...incomeCategories, ...expenseCategories]
  } catch (error) {
    console.error(error)
    transactionsError.value = errorMessage(error, '读取交易记录失败。')
  } finally {
    isTransactionsLoading.value = false
  }
}

async function refreshFinancialData() {
  const { year, month } = getQueryPeriod()
  await Promise.all([loadSummary(year, month), loadTransactions(year, month)])
}

async function changePeriod(value: MonthSelection) {
  if (isSummaryLoading.value || isTransactionsLoading.value) return
  if (value === selectedPeriod.value) return
  selectedPeriod.value = value
  await refreshFinancialData()
}

onMounted(refreshFinancialData)
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
      :period-label="periodLabel"
    />

    <TransactionList
      :transactions="transactions"
      :categories="categories"
      :is-loading="isTransactionsLoading"
      :error-message="transactionsError"
      :selected-period="selectedPeriod"
      :is-period-loading="isSummaryLoading || isTransactionsLoading"
      @month-change="changePeriod"
    />
  </main>
</template>
