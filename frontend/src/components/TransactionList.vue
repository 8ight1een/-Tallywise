<script setup lang="ts">
import { computed, ref } from 'vue'
import MonthPicker from './MonthPicker.vue'
import type { Category, MonthSelection, Transaction } from '../types'

const props = defineProps<{
  transactions: Transaction[]
  categories: Category[]
  isLoading: boolean
  errorMessage: string
  isPeriodLoading: boolean
  selectedPeriod: MonthSelection
}>()

const emit = defineEmits<{
  'month-change': [value: MonthSelection]
}>()

type RecordFilter = 'all' | 'expense' | 'income'

const currentFilter = ref<RecordFilter>('all')
const filteredTransactions = computed(() => {
  if (currentFilter.value === 'all') {
    return props.transactions
  }

  const moneyType = currentFilter.value === 'income' ? '收入' : '支出'

  return props.transactions.filter((transaction) => {
    return transaction.money_type === moneyType
  })
})

function getCategoryName(categoryId: number) {
  return props.categories.find((item) => item.id === categoryId)?.name_categories ?? '未知分类'
}

function formatMoney(value: number | string) {
  return Number(value).toFixed(2)
}
</script>

<template>
  <section class="panel records-panel">
    <div class="records-head">
      <h2 class="panel-title records-title">
        <MonthPicker
          :model-value="props.selectedPeriod"
          :disabled="props.isPeriodLoading"
          @update:model-value="emit('month-change', $event)"
        />
        <span>记录</span>
      </h2>

      <div class="filters">
        <button
          class="filter"
          :class="{ active: currentFilter === 'all' }"
          type="button"
          @click="currentFilter = 'all'"
        >
          全部
        </button>

        <button
          class="filter"
          :class="{ active: currentFilter === 'expense' }"
          type="button"
          @click="currentFilter = 'expense'"
        >
          支出
        </button>

        <button
          class="filter"
          :class="{ active: currentFilter === 'income' }"
          type="button"
          @click="currentFilter = 'income'"
        >
          收入
        </button>
      </div>
    </div>

    <p v-if="isLoading" class="empty">正在读取记录……</p>

    <p v-else-if="errorMessage" class="empty error">
      {{ errorMessage }}
    </p>

    <div v-else-if="filteredTransactions.length === 0" class="empty">
      <span>🧾</span>
      {{ transactions.length === 0 ? '该月份暂无记录' : '当前筛选下暂无记录' }}
    </div>

    <div v-else>
      <div v-for="transaction in filteredTransactions" :key="transaction.id" class="record">
        <div class="icon">
          {{ transaction.money_type === '收入' ? '↗' : '↘' }}
        </div>

        <div>
          <div class="record-name">
            {{ getCategoryName(transaction.category_id) }}
            <span class="tip">{{
              transaction.description ? '：' + transaction.description : ''
            }}</span>
          </div>

          <div class="record-meta">
            {{ transaction.transaction_date }}
          </div>
        </div>

        <div class="amount" :class="transaction.money_type === '收入' ? 'income' : 'expense'">
          {{ transaction.money_type === '收入' ? '+' : '-' }}
          ¥{{ formatMoney(transaction.money) }}
        </div>
      </div>
    </div>
  </section>
</template>

<style scoped>
.panel {
  border: 1px solid var(--line);
  border-radius: 18px;
  background: var(--card);
}

.records-panel {
  overflow: hidden;
}

.records-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 24px 25px 17px;
}

.panel-title {
  margin: 0;
  font-size: 17px;
  font-weight: 600;
}

.record {
  display: grid;
  grid-template-columns: 40px minmax(0, 1fr) auto;
  align-items: center;
  gap: 14px;
  padding: 17px 25px;
  border-top: 1px solid var(--line);
}

.icon {
  display: grid;
  place-items: center;
  width: 40px;
  height: 40px;
  border-radius: 12px;
  background: #f3f2ee;
  font-size: 18px;
}

.record-name {
  overflow: hidden;
  font-size: 14px;
  font-weight: 600;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.record-meta {
  margin-top: 5px;
  color: var(--muted);
  font-size: 12px;
}

.amount {
  font-family: Georgia, serif;
  font-size: 17px;
  text-align: right;
}

.amount.income {
  color: var(--sage);
}

.amount.expense {
  color: var(--rose);
}

.empty {
  padding: 58px 20px;
  color: var(--muted);
  font-size: 14px;
  text-align: center;
}

.empty span {
  display: block;
  margin-bottom: 12px;
  font-size: 28px;
}

.empty.error {
  color: var(--rose);
}

.filters {
  display: flex;
  gap: 8px;
}

.filter {
  padding: 7px 10px;
  border: 0;
  border-radius: 7px;
  background: transparent;
  color: var(--muted);
  font-size: 12px;
}

.filter:hover,
.filter.active {
  background: #f1f3ef;
  color: var(--sage);
}

.tip {
  font-size: 10px;
  color: #999;
}

.records-title {
  display: flex;
  align-items: center;
  gap: 4px;
}
</style>
