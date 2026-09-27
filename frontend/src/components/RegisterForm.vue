<template>
  <div class="auth-screen">
    <div class="auth-card">
      <div class="auth-brand">
        <span class="brand-mark"></span>
        Tallywise
      </div>

      <h1>创建账号</h1>

      <p class="auth-subtitle">注册后即可开始使用 Tallywise。</p>

      <form class="auth-form" @submit.prevent="handleRegister">
        <label>
          昵称
          <input
            :disabled="isLoading"
            v-model.trim="nickname"
            type="text"
            maxlength="20"
            autocomplete="nickname"
            placeholder="请输入昵称"
            required
          />
        </label>

        <label>
          邮箱
          <input
            :disabled="isLoading"
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
            :disabled="isLoading"
            v-model="password"
            type="password"
            minlength="8"
            maxlength="32"
            autocomplete="new-password"
            placeholder="至少 8 位"
            required
          />
        </label>

        <label>
          确认密码
          <input
            :disabled="isLoading"
            v-model="confirmPassword"
            type="password"
            minlength="8"
            maxlength="32"
            autocomplete="new-password"
            placeholder="再次输入密码"
            required
          />
        </label>

        <div v-if="errorMessage" class="auth-error">
          {{ errorMessage }}
        </div>

        <button class="auth-submit" type="submit" :disabled="isLoading">
          {{ isLoading ? '注册中…' : '注册' }}
        </button>
      </form>

      <p class="auth-switch">
        已有账号？

        <button type="button" :disabled="isLoading" @click="emit('showLogin')">返回登录</button>
      </p>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { request, errorMessage as getErrorMessage } from '../api/client'

const emit = defineEmits<{
  showLogin: []
  registerSuccess: [email: string]
}>()

const nickname = ref('')
const email = ref('')
const password = ref('')
const confirmPassword = ref('')
const errorMessage = ref('')
const isLoading = ref(false)

async function handleRegister() {
  if (isLoading.value) return

  errorMessage.value = ''

  if (password.value !== confirmPassword.value) {
    errorMessage.value = '两次输入的密码不一致。'
    return
  }

  isLoading.value = true

  try {
    await request('/api/auth/register', {
      method: 'POST',
      requiresAuth: false,
      fallbackMessage: '注册失败，请检查输入。',
      json: { nickname: nickname.value, email: email.value, password: password.value },
    })

    password.value = ''
    confirmPassword.value = ''

    alert('注册成功，请登录。')
    emit('registerSuccess', email.value)
  } catch (error) {
    console.error('注册失败：', error)
    errorMessage.value = getErrorMessage(error, '注册失败。')
  } finally {
    isLoading.value = false
  }
}
</script>
