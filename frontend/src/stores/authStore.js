import { defineStore } from 'pinia'
import { computed, ref } from 'vue'
import { api, getStoredToken, setStoredToken } from '../api/client'

const USER_STORAGE_KEY = 'swifthub_auth_user'

function loadStoredUser() {
  try {
    const raw = localStorage.getItem(USER_STORAGE_KEY)
    return raw ? JSON.parse(raw) : null
  } catch {
    return null
  }
}

function saveStoredUser(user) {
  try {
    if (user) {
      localStorage.setItem(USER_STORAGE_KEY, JSON.stringify(user))
    } else {
      localStorage.removeItem(USER_STORAGE_KEY)
    }
  } catch {
    // ignore storage errors
  }
}

export const useAuthStore = defineStore('auth', () => {
  const token = ref(getStoredToken())
  const user = ref(loadStoredUser())
  const authModalOpen = ref(false)
  const authModalMode = ref('login') // 'login' | 'register'
  const loading = ref(false)
  const error = ref('')

  const isAuthenticated = computed(() => Boolean(token.value && user.value))
  const isBranchAdmin = computed(() => user.value?.role === 'BRANCH_ADMIN')
  const isCustomer = computed(() => user.value?.role === 'CUSTOMER')

  function openAuthModal(mode = 'login') {
    authModalMode.value = mode
    error.value = ''
    authModalOpen.value = true
  }

  function closeAuthModal() {
    authModalOpen.value = false
    error.value = ''
  }

  function setSession(accessToken, userData) {
    token.value = accessToken
    user.value = userData
    setStoredToken(accessToken)
    saveStoredUser(userData)
  }

  function clearSession() {
    token.value = ''
    user.value = null
    setStoredToken('')
    saveStoredUser(null)
  }

  async function hydrate() {
    if (!token.value) {
      clearSession()
      return null
    }
    try {
      const me = await api.fetchMe()
      user.value = me
      saveStoredUser(me)
      return me
    } catch {
      clearSession()
      return null
    }
  }

  async function login(email, password) {
    loading.value = true
    error.value = ''
    try {
      const data = await api.login({ email, password })
      setSession(data.access_token, data.user)
      authModalOpen.value = false
      return data.user
    } catch (err) {
      error.value = err.message || 'Sign in failed. Please check your credentials.'
      return null
    } finally {
      loading.value = false
    }
  }

  async function register(fullName, email, password) {
    loading.value = true
    error.value = ''
    try {
      const data = await api.register({
        full_name: fullName,
        email,
        password,
      })
      setSession(data.access_token, data.user)
      authModalOpen.value = false
      return data.user
    } catch (err) {
      error.value = err.message || 'Registration failed. Please try again.'
      return null
    } finally {
      loading.value = false
    }
  }

  function logout() {
    clearSession()
  }

  return {
    token,
    user,
    authModalOpen,
    authModalMode,
    loading,
    error,
    isAuthenticated,
    isBranchAdmin,
    isCustomer,
    openAuthModal,
    closeAuthModal,
    hydrate,
    login,
    register,
    logout,
  }
})
