<script setup lang="ts">
import type { Summary } from '../types'

const props = defineProps<{
  summary: Summary | null
  isLoading: boolean
  errorMessage: string
  periodLabel: string
}>()

function formatMoney(value: number | string | undefined) {
  return `¥${Number(value || 0).toFixed(2)}`
}
</script>

<template>
  <p v-if="errorMessage" class="summary-error">
    {{ errorMessage }}
  </p>

  <section class="overview">
    <article class="summary primary">
      <div class="summary-label">{{ props.periodLabel }}结余</div>

      <div class="summary-value">
        {{ isLoading ? '读取中…' : errorMessage || !props.summary ? '—' : formatMoney(props.summary.money_sum) }}
      </div>

      <div class="summary-note">收入减去支出</div>
    </article>

    <article class="summary">
      <div class="summary-label">{{ props.periodLabel }}收入</div>

      <div class="summary-value">
        {{ isLoading ? '读取中…' : errorMessage || !props.summary ? '—' : formatMoney(props.summary.money_in) }}
      </div>

      <div class="summary-note">持续积累，稳步向前</div>
    </article>

    <article class="summary">
      <div class="summary-label">{{ props.periodLabel }}支出</div>

      <div class="summary-value">
        {{ isLoading ? '读取中…' : errorMessage || !props.summary ? '—' : formatMoney(props.summary.money_out) }}
      </div>

      <div class="summary-note">{{ props.periodLabel }}消费支出</div>
    </article>
  </section>
</template>

<style scoped>
.overview {
  display: grid;
  grid-template-columns: 1.25fr 1fr 1fr;
  gap: 16px;
  margin-bottom: 28px;
}

.summary {
  min-height: 150px;
  padding: 23px 24px;
  border: 1px solid var(--line);
  border-radius: 18px;
  background: var(--card);
}

.summary.primary {
  border-color: var(--sage);
  background: var(--sage);
  color: #fff;
}

.summary-label {
  color: var(--muted);
  font-size: 13px;
}

.primary .summary-label {
  color: rgba(255, 255, 255, 0.68);
}

.summary-value {
  margin-top: 16px;
  font-family: Georgia, 'Times New Roman', serif;
  font-size: 33px;
  letter-spacing: -0.04em;
}

.summary-note {
  margin-top: 10px;
  color: var(--muted);
  font-size: 12px;
}

.primary .summary-note {
  color: rgba(255, 255, 255, 0.65);
}

.summary-error {
  color: var(--rose);
  font-size: 13px;
}

@media (max-width: 820px) {
  .overview {
    grid-template-columns: 1fr 1fr;
  }

  .summary.primary {
    grid-column: span 2;
  }
}

@media (max-width: 480px) {
  .overview {
    gap: 10px;
  }

  .summary {
    min-height: 126px;
    padding: 18px;
  }

  .summary-value {
    font-size: 27px;
  }
}
</style>
