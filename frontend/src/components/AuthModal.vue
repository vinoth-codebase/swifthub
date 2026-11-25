<script setup>
import { ref, watch } from 'vue'
import { X, Lock, Mail, User, AlertCircle } from 'lucide-vue-next'
import { useAuthStore } from '../stores/authStore'

const emit = defineEmits(['authenticated'])

const authStore = useAuthStore()

// All form fields strictly initialized as empty strings
const fullName = ref('')
const email = ref('')
const password = ref('')

function resetFields() {
  fullName.value = ''
  email.value = ''
  password.value = ''
}

watch(
  () => authStore.authModalOpen,
  (isOpen) => {
    if (isOpen) {
      resetFields()
    }
  }
)

watch(
  () => authStore.authModalMode,
  () => {
    authStore.error = ''
    resetFields()
  }
)

async function handleSubmit() {
  if (authStore.authModalMode === 'register') {
    const user = await authStore.register(fullName.value, email.value, password.value)
    if (user) {
      resetFields()
      emit('authenticated', user)
    }
  } else {
    const user = await authStore.login(email.value, password.value)
    if (user) {
      resetFields()
      emit('authenticated', user)
    }
  }
}
</script>

<template>
  <div
    v-if="authStore.authModalOpen"
    class="fixed inset-0 z-50 flex items-center justify-center p-4"
  >
    <!-- Backdrop -->
    <div
      class="fixed inset-0 bg-slate-900/45 backdrop-blur-[1px]"
      @click="authStore.closeAuthModal()"
    />

    <!-- Modal Panel -->
    <div
      role="dialog"
      aria-modal="true"
      aria-label="Account Authentication"
      class="relative z-10 w-full max-w-md bg-white rounded-2xl border border-[#E9E5F5] shadow-2xl overflow-hidden"
    >
      <!-- Header with Explicit Top-Right Close (X) Button -->
      <div class="px-6 py-4 border-b border-[#E9E5F5] flex items-center justify-between">
        <div>
          <h2 class="text-base font-semibold text-[#1E1B4B]">
            {{ authStore.authModalMode === 'register' ? 'Create Customer Account' : 'Sign In to SwiftHub' }}
          </h2>
          <p class="text-xs text-[#475569] mt-0.5">
            {{
              authStore.authModalMode === 'register'
                ? 'Register with your email to place orders and track deliveries live.'
                : 'Sign in with your Customer or Branch Admin credentials.'
            }}
          </p>
        </div>

        <button
          type="button"
          @click="authStore.closeAuthModal()"
          aria-label="Close authentication modal"
          class="p-2 rounded-lg text-[#475569] hover:text-[#1E1B4B] hover:bg-[#F5F3FF] border border-transparent hover:border-[#E9E5F5] transition-colors"
        >
          <X class="w-5 h-5" />
        </button>
      </div>

      <!-- Mode Switcher -->
      <div class="px-6 pt-5">
        <div class="grid grid-cols-2 p-1 rounded-lg bg-[#FAF8FF] border border-[#E9E5F5]">
          <button
            type="button"
            @click="authStore.authModalMode = 'login'"
            class="py-1.5 text-xs font-semibold rounded-md transition-colors"
            :class="
              authStore.authModalMode === 'login'
                ? 'bg-[#5B21B6] text-white'
                : 'text-[#475569] hover:text-[#1E1B4B]'
            "
          >
            Sign In
          </button>
          <button
            type="button"
            @click="authStore.authModalMode = 'register'"
            class="py-1.5 text-xs font-semibold rounded-md transition-colors"
            :class="
              authStore.authModalMode === 'register'
                ? 'bg-[#5B21B6] text-white'
                : 'text-[#475569] hover:text-[#1E1B4B]'
            "
          >
            Register
          </button>
        </div>
      </div>

      <!-- Form -->
      <form @submit.prevent="handleSubmit" class="p-6 space-y-4">
        <div
          v-if="authStore.error"
          class="p-3 rounded-lg bg-rose-50 border border-rose-200 text-rose-700 text-xs flex items-start gap-2"
        >
          <AlertCircle class="w-4 h-4 shrink-0 mt-0.5" />
          <span>{{ authStore.error }}</span>
        </div>

        <div v-if="authStore.authModalMode === 'register'">
          <label for="auth-fullname" class="block text-xs font-semibold text-[#0F172A] mb-1">
            Full Name
          </label>
          <div class="relative">
            <User class="w-4 h-4 text-[#475569] absolute left-3 top-1/2 -translate-y-1/2" />
            <input
              id="auth-fullname"
              v-model="fullName"
              type="text"
              required
              autocomplete="name"
              placeholder="Enter your full name"
              class="w-full pl-9 pr-3 py-2 rounded-lg border border-[#E9E5F5] bg-white text-sm text-[#0F172A] placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-[#7C3AED]"
            />
          </div>
        </div>

        <div>
          <label for="auth-email" class="block text-xs font-semibold text-[#0F172A] mb-1">
            Email Address
          </label>
          <div class="relative">
            <Mail class="w-4 h-4 text-[#475569] absolute left-3 top-1/2 -translate-y-1/2" />
            <input
              id="auth-email"
              v-model="email"
              type="email"
              required
              autocomplete="email"
              placeholder="name@example.com"
              class="w-full pl-9 pr-3 py-2 rounded-lg border border-[#E9E5F5] bg-white text-sm text-[#0F172A] placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-[#7C3AED]"
            />
          </div>
        </div>

        <div>
          <label for="auth-password" class="block text-xs font-semibold text-[#0F172A] mb-1">
            Password
          </label>
          <div class="relative">
            <Lock class="w-4 h-4 text-[#475569] absolute left-3 top-1/2 -translate-y-1/2" />
            <input
              id="auth-password"
              v-model="password"
              type="password"
              required
              :minlength="authStore.authModalMode === 'register' ? 6 : 1"
              :autocomplete="authStore.authModalMode === 'register' ? 'new-password' : 'current-password'"
              placeholder="Enter password"
              class="w-full pl-9 pr-3 py-2 rounded-lg border border-[#E9E5F5] bg-white text-sm text-[#0F172A] placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-[#7C3AED]"
            />
          </div>
        </div>

        <button
          type="submit"
          :disabled="authStore.loading"
          class="w-full py-2.5 px-4 rounded-lg bg-[#5B21B6] hover:bg-[#4C1D95] disabled:bg-slate-400 text-white text-sm font-semibold transition-colors"
        >
          {{
            authStore.loading
              ? 'Please wait...'
              : authStore.authModalMode === 'register'
                ? 'Create Account'
                : 'Sign In'
          }}
        </button>
      </form>
    </div>
  </div>
</template>
