<template>
  <div id="authScreen" class="auth-screen">
    <div class="auth-card">
      <div class="auth-brand">
        <span class="brand-mark"></span>
        Tallywise
      </div>

      <div id="loginPanel">
        <h1>欢迎回来</h1>

        <p class="auth-subtitle">登录后继续管理你的每一笔账。</p>

        <p v-if="notice" class="auth-error" role="status">{{ notice }}</p>

        <form @submit.prevent="handleLogin" class="auth-form">
          <label>
            邮箱
            <input
              v-model.trim="email"
              type="email"
              autocomplete="email"
              placeholder="请输入邮箱"
              required
            />
          </label>

          <label>
            密码
            <input
              v-model="password"
              type="password"
              autocomplete="current-password"
              placeholder="请输入密码"
              required
            />
          </label>

          <div v-if="errorMessage" class="auth-error">
            {{ errorMessage }}
          </div>
          <button class="auth-submit" type="submit" :disabled="isLoading">
            {{ isLoading ? '登录中…' : '登录' }}
          </button>
        </form>

      </div>
    </div>
  </div>
</template>

<script lang="ts" setup>
import { ref } from 'vue'
import { request, errorMessage as getErrorMessage,resetApiSession } from '../api/client'
import type { User, LoginResponse } from '../types/index'

const props = defineProps<{
  initialEmail?: string
  notice?: string
}>()

const emit = defineEmits<{
  loginSuccess: [user: User]
}>()

const email = ref(props.initialEmail ?? '')
const password = ref('')
const isLoading = ref(false)
const errorMessage = ref('')

async function handleLogin() {
  errorMessage.value = ''
  isLoading.value = true

  try {
    const loginData = await request<LoginResponse>('/api/auth/login', {
      method: 'POST',
      requireAuth: false,
      fallbackMessage: '登录失败，请检查邮箱和密码。',
      json: { email: email.value, password: password.value },
    })

    password.value = ''

    emit('loginSuccess', loginData.user)
  } catch (error) {
    console.error(error)
    errorMessage.value = getErrorMessage(error, '登录失败。')
  } finally {
    isLoading.value = false
  }
}
</script>

