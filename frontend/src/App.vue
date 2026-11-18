<script setup>
import { onMounted, onUnmounted, ref } from 'vue'
import {
  Store,
  ClipboardList,
  Bike,
  BarChart3,
  Zap,
  Wifi,
  WifiOff,
} from 'lucide-vue-next'
import { useHubStore } from './stores/hubStore'
import { useWebSocket } from './composables/useWebSocket'
import CustomerStorefront from './components/CustomerStorefront.vue'
import CartDrawer from './components/CartDrawer.vue'
import OpsConsole from './components/OpsConsole.vue'

const hubStore = useHubStore()
const activeTab = ref('storefront')

const tabs = [
  { id: 'storefront', label: 'Customer Storefront', icon: Store },
  { id: 'ops', label: 'Dark-Store Ops', icon: ClipboardList },
  { id: 'riders', label: 'Rider Dispatch', icon: Bike },
  { id: 'analytics', label: 'Ops Analytics', icon: BarChart3 },
]

const ws = useWebSocket((event) => {
  hubStore.handleWsEvent(event)
})

onMounted(async () => {
  await hubStore.initialize()
  ws.connect()
})

onUnmounted(() => {
  ws.disconnect()
})
</script>

<template>
  <div class="min-h-screen flex flex-col bg-[#F8FAFC] text-[#0F172A]">
    <header class="sticky top-0 z-30 bg-white border-b border-[#E2E8F0]">
      <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between gap-4">
        <div class="flex items-center gap-2.5 shrink-0">
          <div class="w-9 h-9 rounded-lg bg-[#1E3A8A] text-white flex items-center justify-center">
            <Zap class="w-5 h-5" />
          </div>
          <div>
            <span class="font-bold text-lg tracking-tight text-[#0F172A]">SwiftHub</span>
            <span class="hidden lg:inline-block ml-2 text-xs font-medium text-[#475569] border-l border-[#E2E8F0] pl-2">
              10-Min Dark-Store Dispatch
            </span>
          </div>
        </div>

        <nav class="flex items-center gap-1 overflow-x-auto">
          <button
            v-for="tab in tabs"
            :key="tab.id"
            type="button"
            @click="activeTab = tab.id"
            class="flex items-center gap-2 px-3 py-2 rounded-lg text-sm font-medium transition-colors whitespace-nowrap"
            :class="
              activeTab === tab.id
                ? 'bg-[#1E3A8A] text-white'
                : 'text-[#475569] hover:bg-slate-100 hover:text-[#0F172A]'
            "
          >
            <component :is="tab.icon" class="w-4 h-4" />
            <span>{{ tab.label }}</span>
          </button>
        </nav>

        <div class="hidden sm:flex items-center gap-2 shrink-0">
          <span
            class="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium border"
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

      <CustomerStorefront v-if="activeTab === 'storefront'" />
      <OpsConsole v-else-if="activeTab === 'ops'" />
      <div
        v-else
        class="bg-white border border-[#E2E8F0] rounded-xl p-8 text-center text-sm text-[#475569]"
      >
        View module initializing...
      </div>
    </main>

    <CartDrawer />

    <footer class="bg-white border-t border-[#E2E8F0] py-4 mt-8">
      <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 flex flex-col sm:flex-row items-center justify-between gap-2 text-xs text-[#475569]">
        <p>
          SwiftHub is a non-commercial technical portfolio project using simulated operational data.
        </p>
        <p>Bangalore Dark-Store Dispatch Engine</p>
      </div>
    </footer>
  </div>
</template>
