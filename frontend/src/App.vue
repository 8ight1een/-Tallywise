<script setup lang="ts">
import { ref } from 'vue'
import LoginForm from './components/LoginForm.vue'
import type { User } from './types'

const currentUser = ref<User | null>(null)

function handleLoginSuccess(user: User) {
  currentUser.value = user
}
</script>

<template>
  <LoginForm v-if="currentUser === null" @login-success="handleLoginSuccess" />
  <div v-else class="auth-screen">
    <div class="auth-card">
      <h1>登录成功</h1>
      <p>{{ currentUser.nickname || currentUser.email }}，欢迎回来。</p>
    </div>
  </div>
</template>