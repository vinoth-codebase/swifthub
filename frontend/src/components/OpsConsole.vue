<script setup>
import { computed, onMounted, onUnmounted, reactive, ref } from 'vue'
import {
  ClipboardList,
  Clock,
  CheckSquare,
  Square,
  ArrowRight,
  Bike,
  AlertTriangle,
} from 'lucide-vue-next'
import { useHubStore } from '../stores/hubStore'
import LowStockPanel from './LowStockPanel.vue'
import {
  formatCountdown,
  formatDuration,
  getRemainingSlaSeconds,
  getSlaRiskMeta,
} from '../utils/sla'

const hubStore = useHubStore()
const nowMs = ref(Date.now())
const checkedItems = reactive({})
const busyOrderId = ref(null)
const actionError = ref('')

let timerId = null
onMounted(() => {
  timerId = setInterval(() => {
    nowMs.value = Date.now()
  }, 1000)
})
onUnmounted(() => {
  if (timerId) clearInterval(timerId)
})

const prioritizedQueue = computed(() => {
  const active = hubStore.orders.filter(
    (o) => !['DELIVERED', 'CANCELLED'].includes(o.status)
  )
  return [...active].sort((a, b) => {
    const riskDiff = (b.sla_risk_score || 0) - (a.sla_risk_score || 0)
    if (Math.abs(riskDiff) > 0.05) return riskDiff
    const remA = getRemainingSlaSeconds(a.created_at, nowMs.value)
    const remB = getRemainingSlaSeconds(b.created_at, nowMs.value)
    return remA - remB
  })
})

function togglePickItem(orderId, itemId) {
  const key = `${orderId}:${itemId}`
  checkedItems[key] = !checkedItems[key]
}

function isPicked(orderId, itemId) {
  return Boolean(checkedItems[`${orderId}:${itemId}`])
}

function sortedItems(order) {
  return [...(order.items || [])].sort((a, b) =>
    a.aisle_code.localeCompare(b.aisle_code)
  )
}

function nextActionFor(status) {
  if (status === 'PLACED') return { status: 'PICKING', label: 'Start Picking' }
  if (status === 'PICKING') return { status: 'PACKED', label: 'Mark Packed' }
  if (status === 'PACKED') return { status: 'OUT_FOR_DELIVERY', label: 'Dispatch Rider' }
  if (status === 'OUT_FOR_DELIVERY') return { status: 'DELIVERED', label: 'Mark Delivered' }
  return null
}

async function advanceOrder(order) {
  const next = nextActionFor(order.status)
  if (!next) return
  busyOrderId.value = order.id
  actionError.value = ''
  try {
    await hubStore.advanceOrderStatus(order.id, next.status)
  } catch (err) {
    actionError.value = err.message || 'Could not update order status'
  } finally {
    busyOrderId.value = null
  }
}
</script>

<template>
  <div class="space-y-6">
    <!-- Header Banner -->
    <div class="bg-white border border-[#E9E5F5] rounded-xl p-5 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
      <div class="flex items-start gap-3">
        <div class="w-10 h-10 rounded-lg bg-[#EDE9FE] text-[#5B21B6] flex items-center justify-center shrink-0">
          <ClipboardList class="w-5 h-5" />
        </div>
        <div>
          <h1 class="text-lg font-semibold text-[#1E1B4B]">Dark-Store Picker & Hub Ops Console</h1>
          <p class="text-sm text-[#475569] mt-0.5">
            Queue automatically prioritized by highest ML SLA breach risk and lowest remaining window.
          </p>
        </div>
      </div>

      <div class="flex items-center gap-3 text-xs font-medium">
        <span class="px-3 py-1.5 rounded-lg bg-[#FAF8FF] border border-[#E9E5F5] text-[#0F172A]">
          Active Queue: {{ prioritizedQueue.length }}
        </span>
        <span class="px-3 py-1.5 rounded-lg bg-[#FAF8FF] border border-[#E9E5F5] text-[#0F172A]">
          Hub: {{ hubStore.currentStore?.name || 'All' }}
        </span>
      </div>
    </div>

    <div
      v-if="actionError"
      class="p-3.5 rounded-xl bg-rose-50 border border-rose-200 text-rose-700 text-sm flex items-center gap-2"
    >
      <AlertTriangle class="w-4 h-4 shrink-0" />
      <span>{{ actionError }}</span>
    </div>

    <!-- Main Ops Layout (Queue + Sidebar Slot) -->
    <div class="grid grid-cols-1 lg:grid-cols-3 gap-6">
      <!-- Left 2 Cols: SLA-Prioritized Order Queue -->
      <div class="lg:col-span-2 space-y-4">
        <div
          v-if="prioritizedQueue.length === 0"
          class="bg-white border border-[#E9E5F5] rounded-xl p-10 text-center text-sm text-[#475569]"
        >
          No active orders in the queue for {{ hubStore.currentStore?.name }}. Place an order in the Storefront or trigger a Live Demo Simulation.
        </div>

        <article
          v-for="order in prioritizedQueue"
          :key="order.id"
          class="bg-white border border-[#E9E5F5] rounded-xl p-5 space-y-4"
        >
          <div class="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
            <div>
              <div class="flex items-center gap-2 flex-wrap">
                <span class="text-sm font-bold text-[#1E1B4B]">#ORD-{{ order.id }}</span>
                <span class="text-xs font-semibold px-2 py-0.5 rounded bg-[#F5F3FF] text-[#5B21B6]">
                  {{ order.status }}
                </span>
                <span
                  class="text-xs font-medium px-2 py-0.5 rounded-full border"
                  :class="getSlaRiskMeta(order.sla_risk_score).badgeClass"
                >
                  {{ getSlaRiskMeta(order.sla_risk_score).label }} ({{ getSlaRiskMeta(order.sla_risk_score).pct }}%)
                </span>
              </div>
              <p class="text-xs text-[#475569] mt-1">
                Customer: <strong class="text-[#0F172A]">{{ order.customer_name }}</strong>
                &middot; Predicted ETA: {{ formatDuration(order.predicted_eta_sec) }}
              </p>
            </div>

            <div class="flex items-center gap-2.5 flex-wrap">
              <div
                class="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg border text-xs font-semibold"
                :class="
                  getRemainingSlaSeconds(order.created_at, nowMs) < 0
                    ? 'bg-rose-50 text-rose-700 border-rose-200'
                    : getRemainingSlaSeconds(order.created_at, nowMs) < 180
                      ? 'bg-amber-50 text-amber-800 border-amber-200'
                      : 'bg-[#F5F3FF] text-[#5B21B6] border-[#DDD6FE]'
                "
              >
                <Clock class="w-3.5 h-3.5" />
                <span>{{ formatCountdown(getRemainingSlaSeconds(order.created_at, nowMs)) }}</span>
              </div>

              <button
                v-if="nextActionFor(order.status)"
                type="button"
                :disabled="busyOrderId === order.id"
                @click="advanceOrder(order)"
                class="inline-flex items-center gap-1.5 px-3.5 py-1.5 rounded-lg bg-[#5B21B6] hover:bg-[#4C1D95] disabled:bg-slate-300 text-white text-xs font-semibold transition-colors"
              >
                <span>{{ nextActionFor(order.status).label }}</span>
                <ArrowRight class="w-3.5 h-3.5" />
              </button>
            </div>
          </div>

          <!-- Aisle-Sorted Pick List -->
          <div class="border-t border-[#E9E5F5] pt-3">
            <div class="flex items-center justify-between mb-2">
              <span class="text-xs font-semibold uppercase tracking-wider text-[#475569]">
                Aisle-Sorted Pick List ({{ order.items.length }} SKUs)
              </span>
              <span v-if="order.rider_name" class="inline-flex items-center gap-1 text-xs font-medium text-[#5B21B6]">
                <Bike class="w-3.5 h-3.5" />
                <span>Rider: {{ order.rider_name }}</span>
              </span>
            </div>

            <div class="grid grid-cols-1 sm:grid-cols-2 gap-2">
              <button
                v-for="item in sortedItems(order)"
                :key="item.id"
                type="button"
                @click="togglePickItem(order.id, item.id)"
                class="flex items-center justify-between gap-2 p-2.5 rounded-lg border text-left transition-colors"
                :class="
                  isPicked(order.id, item.id)
                    ? 'bg-emerald-50/70 border-emerald-200 text-emerald-900'
                    : 'bg-[#FAF8FF] border-[#E9E5F5] hover:border-[#C4B5FD] text-[#0F172A]'
                "
              >
                <div class="flex items-center gap-2 min-w-0">
                  <CheckSquare
                    v-if="isPicked(order.id, item.id)"
                    class="w-4 h-4 text-emerald-600 shrink-0"
                  />
                  <Square v-else class="w-4 h-4 text-slate-400 shrink-0" />
                  <div class="min-w-0">
                    <p
                      class="text-xs font-medium truncate"
                      :class="{ 'line-through opacity-75': isPicked(order.id, item.id) }"
                    >
                      {{ item.name }}
                    </p>
                    <p class="text-[11px] text-[#475569]">
                      {{ item.aisle_code }} &middot; {{ item.sku }}
                    </p>
                  </div>
                </div>
                <span class="px-2 py-0.5 rounded bg-white border border-[#E2E8F0] text-xs font-bold shrink-0">
                  x{{ item.quantity }}
                </span>
              </button>
            </div>
          </div>
        </article>
      </div>

      <!-- Right Sidebar: Low-Stock Reorder Alerts -->
      <div class="space-y-4">
        <LowStockPanel />
      </div>
    </div>
  </div>
</template>
