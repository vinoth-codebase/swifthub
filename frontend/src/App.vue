<script setup>
import { computed, onMounted, onUnmounted, ref, watch } from 'vue'
import {
  Store,
  ClipboardList,
  Bike,
  BarChart3,
  Zap,
  Wifi,
  WifiOff,
  Lock,
  LogIn,
  UserPlus,
  LogOut,
  PackageCheck,
} from 'lucide-vue-next'
import { useAuthStore } from './stores/authStore'
import { useHubStore } from './stores/hubStore'
import { useCartStore } from './stores/cartStore'
import { useWebSocket } from './composables/useWebSocket'
import CustomerStorefront from './components/CustomerStorefront.vue'
import LiveOrderTracker from './components/LiveOrderTracker.vue'
import CartDrawer from './components/CartDrawer.vue'
import AuthModal from './components/AuthModal.vue'
import OpsConsole from './components/OpsConsole.vue'
import RiderDispatchPanel from './components/RiderDispatchPanel.vue'
import AnalyticsDashboard from './components/AnalyticsDashboard.vue'

const authStore = useAuthStore()
const hubStore = useHubStore()
const cartStore = useCartStore()

const activeTab = ref('storefront')

const adminTabs = [
  { id: 'ops', label: 'Dark-Store Ops', icon: ClipboardList },
  { id: 'riders', label: 'Rider Dispatch', icon: Bike },
  { id: 'analytics', label: 'Ops Analytics', icon: BarChart3 },
]

const managedHubName = computed(() => {
  if (!authStore.isBranchAdmin) return ''
  return authStore.user?.store_name || hubStore.currentStore?.name || `Hub #${authStore.user?.store_id}`
})

const ws = useWebSocket((event) => {
  hubStore.handleWsEvent(event)
})

function syncTabForRole() {
  if (authStore.isBranchAdmin) {
    if (!['ops', 'riders', 'analytics'].includes(activeTab.value)) {
      activeTab.value = 'ops'
    }
  } else if (authStore.isCustomer) {
    if (!['storefront', 'orders'].includes(activeTab.value)) {
      activeTab.value = 'storefront'
    }
  } else {
    activeTab.value = 'storefront'
  }
}

async function onAuthenticated(user) {
  if (user.role === 'BRANCH_ADMIN') {
    cartStore.clearCart()
    cartStore.closeDrawer()
    activeTab.value = 'ops'
  } else {
    activeTab.value = 'storefront'
  }
  await hubStore.initialize()
}

async function handleLogout() {
  authStore.logout()
  cartStore.clearCart()
  cartStore.closeDrawer()
  activeTab.value = 'storefront'
  await hubStore.initialize()
}

function onOrderPlaced() {
  activeTab.value = 'orders'
}

watch(
  () => authStore.user?.role,
  () => {
    syncTabForRole()
  }
)

onMounted(async () => {
  await authStore.hydrate()
  syncTabForRole()
  await hubStore.initialize()
  ws.connect()
})

onUnmounted(() => {
  ws.disconnect()
})
</script>

<template>
  <div class="min-h-screen flex flex-col bg-[#FAF8FF] text-[#0F172A]">
    <header class="sticky top-0 z-30 bg-white border-b border-[#E9E5F5]">
      <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between gap-4">
        <!-- Brand -->
        <div class="flex items-center gap-2.5 shrink-0">
          <div class="w-9 h-9 rounded-lg bg-gradient-to-br from-[#4C1D95] via-[#6D28D9] to-[#A21CAF] text-white flex items-center justify-center shadow-sm">
            <Zap class="w-5 h-5" />
          </div>
          <div>
            <span class="font-bold text-lg tracking-tight text-[#1E1B4B]">SwiftHub</span>
            <span class="hidden lg:inline-block ml-2 text-xs font-medium text-[#475569] border-l border-[#E9E5F5] pl-2">
              {{ authStore.isBranchAdmin ? '10-Min Dark-Store Dispatch' : 'Groceries in Minutes' }}
            </span>
          </div>
        </div>

        <!-- Role-Based Navigation -->
        <nav v-if="authStore.isBranchAdmin" class="flex items-center gap-1 overflow-x-auto">
          <button
            v-for="tab in adminTabs"
            :key="tab.id"
            type="button"
            @click="activeTab = tab.id"
            class="flex items-center gap-2 px-3 py-2 rounded-lg text-sm font-medium transition-colors whitespace-nowrap"
            :class="
              activeTab === tab.id
                ? 'bg-[#5B21B6] text-white'
                : 'text-[#475569] hover:bg-[#F5F3FF] hover:text-[#1E1B4B]'
            "
          >
            <component :is="tab.icon" class="w-4 h-4" />
            <span>{{ tab.label }}</span>
          </button>
        </nav>

        <nav v-else-if="authStore.isCustomer" class="flex items-center gap-1 overflow-x-auto">
          <button
            type="button"
            @click="activeTab = 'storefront'"
            class="flex items-center gap-2 px-3 py-2 rounded-lg text-sm font-medium transition-colors whitespace-nowrap"
            :class="
              activeTab === 'storefront'
                ? 'bg-[#5B21B6] text-white'
                : 'text-[#475569] hover:bg-[#F5F3FF] hover:text-[#1E1B4B]'
            "
          >
            <Store class="w-4 h-4" />
            <span>Storefront</span>
          </button>
          <button
            type="button"
            @click="activeTab = 'orders'"
            class="flex items-center gap-2 px-3 py-2 rounded-lg text-sm font-medium transition-colors whitespace-nowrap"
            :class="
              activeTab === 'orders'
                ? 'bg-[#5B21B6] text-white'
                : 'text-[#475569] hover:bg-[#F5F3FF] hover:text-[#1E1B4B]'
            "
          >
            <PackageCheck class="w-4 h-4" />
            <span>My Orders</span>
            <span
              v-if="hubStore.orders.length > 0"
              class="px-1.5 py-0.5 text-[11px] font-semibold rounded-full"
              :class="activeTab === 'orders' ? 'bg-white text-[#5B21B6]' : 'bg-[#EDE9FE] text-[#5B21B6]'"
            >
              {{ hubStore.orders.length }}
            </span>
          </button>
        </nav>

        <!-- Right Controls: Locked Hub Badge / Live Sync / Auth Buttons -->
        <div class="flex items-center gap-2 shrink-0">
          <!-- Locked Hub Badge for Branch Admin -->
          <span
            v-if="authStore.isBranchAdmin"
            class="hidden md:inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold bg-[#F5F3FF] text-[#5B21B6] border border-[#DDD6FE]"
          >
            <Lock class="w-3.5 h-3.5" />
            <span>Managed Hub: {{ managedHubName }}</span>
          </span>

          <!-- WebSocket Status -->
          <span
            class="hidden xl:inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium border"
            :class="
              ws.status.value === 'connected'
                ? 'bg-emerald-50 text-emerald-700 border-emerald-200'
                : 'bg-amber-50 text-amber-800 border-amber-200'
            "
          >
            <Wifi v-if="ws.status.value === 'connected'" class="w-3.5 h-3.5" />
            <WifiOff v-else class="w-3.5 h-3.5" />
            <span>{{ ws.status.value === 'connected' ? 'Live Sync' : 'Reconnecting' }}</span>
          </span>

          <!-- Unauthenticated Actions -->
          <template v-if="!authStore.isAuthenticated">
            <button
              type="button"
              @click="authStore.openAuthModal('login')"
              class="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-[#E9E5F5] bg-white hover:bg-[#F5F3FF] text-xs font-semibold text-[#1E1B4B] transition-colors"
            >
              <LogIn class="w-3.5 h-3.5 text-[#7C3AED]" />
              <span>Sign In</span>
            </button>
            <button
              type="button"
              @click="authStore.openAuthModal('register')"
              class="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-[#5B21B6] hover:bg-[#4C1D95] text-white text-xs font-semibold transition-colors"
            >
              <UserPlus class="w-3.5 h-3.5" />
              <span>Register</span>
            </button>
          </template>

          <!-- Authenticated User & Logout -->
          <template v-else>
            <span
              v-if="authStore.isCustomer"
              class="hidden sm:inline-block text-xs font-medium text-[#475569] max-w-[140px] truncate"
            >
              {{ authStore.user?.full_name }}
            </span>
            <button
              type="button"
              @click="handleLogout"
              class="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-[#E9E5F5] bg-white hover:bg-[#F5F3FF] text-xs font-semibold text-[#475569] hover:text-[#1E1B4B] transition-colors"
            >
              <LogOut class="w-3.5 h-3.5" />
              <span>Logout</span>
            </button>
          </template>
        </div>
      </div>
    </header>

    <main class="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-6">
      <div
        v-if="hubStore.error"
        class="mb-4 p-4 rounded-xl bg-rose-50 border border-rose-200 text-rose-700 text-sm"
      >
        {{ hubStore.error }}
      </div>

      <!-- Branch Admin Views -->
      <template v-if="authStore.isBranchAdmin">
        <OpsConsole v-if="activeTab === 'ops'" />
        <RiderDispatchPanel
          v-else-if="activeTab === 'riders'"
          @track-order="activeTab = 'ops'"
        />
        <AnalyticsDashboard v-else-if="activeTab === 'analytics'" />
      </template>

      <!-- Customer & Unauthenticated Views -->
      <template v-else>
        <div v-if="authStore.isCustomer && activeTab === 'orders'" class="space-y-6">
          <div class="bg-white border border-[#E9E5F5] rounded-xl p-5 flex items-center justify-between gap-4">
            <div>
              <h1 class="text-lg font-semibold text-[#1E1B4B]">My Live Orders</h1>
              <p class="text-sm text-[#475569] mt-0.5">
                Track your active deliveries and order history in real time.
              </p>
            </div>
            <button
              type="button"
              @click="activeTab = 'storefront'"
              class="px-3.5 py-2 rounded-lg bg-[#5B21B6] hover:bg-[#4C1D95] text-white text-xs font-semibold transition-colors"
            >
              Continue Shopping
            </button>
          </div>

          <LiveOrderTracker v-if="hubStore.orders.length > 0" />
          <div
            v-else
            class="bg-white border border-[#E9E5F5] rounded-xl p-12 text-center space-y-2"
          >
            <PackageCheck class="w-8 h-8 text-slate-300 mx-auto" />
            <p class="text-sm font-semibold text-[#1E1B4B]">No orders yet</p>
            <p class="text-xs text-[#475569]">
              Browse the storefront and place an order to see live tracking here.
            </p>
          </div>
        </div>

        <CustomerStorefront v-else />
      </template>
    </main>

    <CartDrawer v-if="!authStore.isBranchAdmin" @order-placed="onOrderPlaced" />
    <AuthModal @authenticated="onAuthenticated" />

    <footer class="bg-white border-t border-[#E9E5F5] py-4 mt-8">
      <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 flex flex-col sm:flex-row items-center justify-between gap-2 text-xs text-[#475569]">
        <p>
          Disclaimer: SwiftHub is a non-commercial technical portfolio project using simulated operational data and synthetic telemetry.
        </p>
        <p class="font-medium text-[#1E1B4B]">SwiftHub Groceries &amp; Dispatch Engine</p>
      </div>
    </footer>
  </div>
</template>
