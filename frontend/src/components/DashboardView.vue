<script setup lang="ts">
import type { User } from '../types'

defineProps<{
  user: User
  isLoggingOut: boolean
}>()

const emit = defineEmits<{
  logout: []
}>()
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
      <h1>登录成功，{{ user.nickname || user.email }}。</h1>
      <p>欢迎回来。</p>
    </section>
  </main>
</template>
