<script setup lang="ts">
import { onMounted, onUnmounted, ref } from 'vue'
import {
  request,
  errorMessage,
  isUnauthorized,
  onUnauthorized,
  resetApiSession,
} from './api/client'
import LoginForm from './components/LoginForm.vue'
import RegisterForm from './components/RegisterForm.vue'
import DashboardView from './components/DashboardView.vue'
import type { User } from './types'

const authNotice = ref('')
const loginEmail = ref('')
const currentUser = ref<User | null>(null)
const isCheckingAuth = ref(true)
const authMode = ref<'login' | 'register'>('login')
const isLoggingOut = ref(false)

function handleLoginSuccess(user: User) {
  resetApiSession()
  authNotice.value = ''
  currentUser.value = user
}

async function checkCurrentUser() {
  try {
    currentUser.value = await request<User>('/api/auth/me', { requiresAuth: false })
  } catch (error) {
    console.error('检查登录状态失败：', error)
    if (!isUnauthorized(error)) authNotice.value = errorMessage(error, '检查登录状态失败。')
  } finally {
    isCheckingAuth.value = false
  }
}

async function logout() {
  isLoggingOut.value = true

  try {
    await request('/api/auth/logout', { method: 'POST', requiresAuth: false })
    resetApiSession()
    authNotice.value = ''
    authMode.value = 'login'
    currentUser.value = null
  } catch (error) {
    console.error('退出登录失败：', error)
    alert(errorMessage(error, '退出登录失败。'))
  } finally {
    isLoggingOut.value = false
  }
}

function handleRegisterSuccess(email: string) {
  loginEmail.value = email
  authMode.value = 'login'
}

const removeUnauthorizedHandler = onUnauthorized(() => {
  loginEmail.value = currentUser.value?.email ?? loginEmail.value
  currentUser.value = null
  authMode.value = 'login'
  authNotice.value = '登录已过期，请重新登录。'
})
onUnmounted(removeUnauthorizedHandler)

onMounted(() => {
  checkCurrentUser()
})
</script>

<template>
  <div v-if="isCheckingAuth">正在检查登录状态……</div>

  <LoginForm
    v-else-if="currentUser === null && authMode === 'login'"
    :initial-email="loginEmail"
    :notice="authNotice"
    @login-success="handleLoginSuccess"
    @show-register="authMode = 'register'"
  />

  <RegisterForm
    v-else-if="currentUser === null"
    @show-login="authMode = 'login'"
    @register-success="handleRegisterSuccess"
  />

  <DashboardView v-else :user="currentUser" :is-logging-out="isLoggingOut" @logout="logout" />
</template>
