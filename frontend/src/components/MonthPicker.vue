<script setup lang="ts">
import { computed } from 'vue'
import type { MonthSelection } from '../types'

const props = defineProps<{
  disabled?: boolean
  modelValue: MonthSelection
}>()

const emit = defineEmits<{
  'update:modelValue': [value: MonthSelection]
}>()

const options: { label: string; value: MonthSelection }[] = [
  { label: '本月', value: 'current' },
  { label: '1月', value: 1 },
  { label: '2月', value: 2 },
  { label: '3月', value: 3 },
  { label: '4月', value: 4 },
  { label: '5月', value: 5 },
  { label: '6月', value: 6 },
  { label: '7月', value: 7 },
  { label: '8月', value: 8 },
  { label: '9月', value: 9 },
  { label: '10月', value: 10 },
  { label: '11月', value: 11 },
  { label: '12月', value: 12 },
]

const selectedIndex = computed(() => {
  return options.findIndex((option) => option.value === props.modelValue)
})

const selectedLabel = computed(() => {
  return options[selectedIndex.value]?.label ?? '本月'
})

function moveSelection(direction: -1 | 1) {
  if (props.disabled) return

  const nextOption = options[selectedIndex.value + direction]


  if (!nextOption) return

  emit('update:modelValue', nextOption.value)
}
</script>

<template>
  <span class="month-picker">
    <button
      type="button"
      class="month-arrow"
      aria-label="上一个月份选项"
      :disabled="props.disabled || selectedIndex <= 0"
      @click="moveSelection(-1)"
    >
      ▴
    </button>

    <span class="month-label" aria-live="polite">
      {{ selectedLabel }}
    </span>

    <button
      type="button"
      class="month-arrow"
      aria-label="下一个月份选项"
      :disabled="props.disabled || selectedIndex >= options.length - 1"
      @click="moveSelection(1)"
    >
      ▾
    </button>
  </span>
</template>

<style scoped>
.month-picker {
  display: inline-flex;
  flex-direction: column;
  align-items: center;
  vertical-align: middle;
  width: 3.5em;
}

.month-label {
  line-height: 1.5;
  white-space: nowrap;
}

.month-arrow {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 100%;
  height: 18px;
  padding: 0;
  border: 0;
  background: transparent;
  color: var(--sage);
  cursor: pointer;
}

.month-arrow:disabled {
  opacity: 0.3;
  cursor: default;
}

.month-arrow:focus-visible {
  outline: 2px solid var(--sage);
  border-radius: 4px;
}
</style>
