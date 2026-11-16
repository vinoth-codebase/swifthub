<script setup>
import { computed, onMounted, onUnmounted, ref } from 'vue'
import {
  Clock,
  CheckCircle2,
  Circle,
  Bike,
  AlertTriangle,
  XCircle,
  Activity,
} from 'lucide-vue-next'
import { useHubStore } from '../stores/hubStore'
import {
  ORDER_STEPS,
  formatCountdown,
  formatDuration,
  formatCurrencyInr,
  getRemainingSlaSeconds,
  getSlaRiskMeta,
  getStepIndex,
} from '../utils/sla'

const hubStore = useHubStore()

const nowMs = ref(Date.now())
let timerId = null

onMounted(() => {
  timerId = setInterval(() => {
    nowMs.value = Date.now()
  }, 1000)
})

onUnmounted(() => {
  if (timerId) clearInterval(timerId)
})

const trackableOrders = computed(() => hubStore.orders.slice(0, 8))

const activeOrder = computed(() => {
  if (hubStore.trackedOrder) return hubStore.trackedOrder
  const inFlight = hubStore.orders.find(
    (o) => !['DELIVERED', 'CANCELLED'].includes(o.status)
  )
  return inFlight || hubStore.orders[0] || null
})

const remainingSec = computed(() => {
  if (!activeOrder.value) return 600
  if (activeOrder.value.status === 'DELIVERED') {
    const placed = activeOrder.value.events?.find((e) => e.to_status === 'PLACED')
    const delivered = activeOrder.value.events?.find((e) => e.to_status === 'DELIVERED')
    if (placed && delivered) {
      const elapsed = Math.floor(
        (new Date(delivered.timestamp).getTime() - new Date(placed.timestamp).getTime()) / 1000
      )
      return 600 - elapsed
    }
  }
  return getRemainingSlaSeconds(activeOrder.value.created_at, nowMs.value)
})

const riskMeta = computed(() => getSlaRiskMeta(activeOrder.value?.sla_risk_score || 0))
const currentStepIdx = computed(() => getStepIndex(activeOrder.value?.status || 'PLACED'))

const canCancel = computed(() => {
  if (!activeOrder.value) return false
  return ['PLACED', 'PICKING', 'PACKED'].includes(activeOrder.value.status)
})

async function handleCancel() {
  if (!activeOrder.value) return
  await hubStore.advanceOrderStatus(
    activeOrder.value.id,
    'CANCELLED',
    'Cancelled by customer prior to dispatch'
  )
}
</script>

<template>
  <section
    v-if="activeOrder"
    class="bg-white border border-[#E2E8F0] rounded-xl p-5 space-y-5"
  >
    <!-- Header Row -->
    <div class="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-4">
      <div class="space-y-1">
        <div class="flex items-center gap-2.5 flex-wrap">
          <span class="text-xs font-semibold uppercase tracking-wider text-[#1E3A8A]">
            Live Order Tracker
          </span>
          <span class="text-xs font-mono text-[#475569]">#ORD-{{ activeOrder.id }}</span>
          <span
            class="text-xs font-medium px-2 py-0.5 rounded-full border"
            :class="riskMeta.badgeClass"
          >
            {{ riskMeta.label }} ({{ riskMeta.pct }}%)
          </span>
          <span
            v-if="activeOrder.status === 'CANCELLED'"
            class="text-xs font-medium px-2 py-0.5 rounded-full border bg-rose-50 text-rose-700 border-rose-200"
          >
            CANCELLED
          </span>
        </div>
        <h2 class="text-base font-semibold text-[#0F172A]">
          {{ activeOrder.customer_name }} &middot; {{ activeOrder.store_name }}
        </h2>
      </div>

      <div class="flex items-center gap-3 flex-wrap">
        <select
          :value="activeOrder.id"
          @change="hubStore.trackedOrderId = Number($event.target.value)"
          class="bg-[#F8FAFC] border border-[#E2E8F0] rounded-lg px-3 py-1.5 text-xs font-medium text-[#0F172A] focus:outline-none focus:ring-2 focus:ring-[#1D4ED8]"
        >
          <option v-for="o in trackableOrders" :key="o.id" :value="o.id">
            #ORD-{{ o.id }} - {{ o.customer_name }} ({{ o.status }})
          </option>
        </select>

        <!-- 10-Min SLA Countdown Pill -->
        <div
          class="flex items-center gap-2 px-3 py-1.5 rounded-lg border text-xs font-semibold"
          :class="
            remainingSec < 0
              ? 'bg-rose-50 text-rose-700 border-rose-200'
              : remainingSec < 180
                ? 'bg-amber-50 text-amber-800 border-amber-200'
                : 'bg-[#EFF6FF] text-[#1E3A8A] border-blue-200'
          "
        >
          <Clock class="w-4 h-4" />
          <span>SLA Window: {{ formatCountdown(remainingSec) }}</span>
        </div>

        <button
          v-if="canCancel"
          type="button"
          @click="handleCancel"
          class="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-rose-200 bg-rose-50 hover:bg-rose-100 text-rose-700 text-xs font-medium transition-colors"
        >
          <XCircle class="w-3.5 h-3.5" />
          <span>Cancel</span>
        </button>
      </div>
    </div>

    <!-- 5-Step Progress Timeline -->
    <div v-if="activeOrder.status !== 'CANCELLED'" class="grid grid-cols-5 gap-2">
      <div
        v-for="(step, idx) in ORDER_STEPS"
        :key="step.key"
        class="flex flex-col items-center text-center"
      >
        <div class="flex items-center w-full">
          <div
            class="h-1 flex-1 rounded-full"
            :class="idx === 0 ? 'bg-transparent' : idx <= currentStepIdx ? 'bg-[#1D4ED8]' : 'bg-[#E2E8F0]'"
          />
          <div
            class="w-7 h-7 rounded-full flex items-center justify-center shrink-0 border"
            :class="
              idx <= currentStepIdx
                ? 'bg-[#1E3A8A] text-white border-[#1E3A8A]'
                : 'bg-white text-slate-400 border-[#E2E8F0]'
            "
          >
            <CheckCircle2 v-if="idx <= currentStepIdx" class="w-4 h-4" />
            <Circle v-else class="w-3.5 h-3.5" />
          </div>
          <div
            class="h-1 flex-1 rounded-full"
            :class="idx === ORDER_STEPS.length - 1 ? 'bg-transparent' : idx < currentStepIdx ? 'bg-[#1D4ED8]' : 'bg-[#E2E8F0]'"
          />
        </div>
        <span
          class="mt-1.5 text-[11px] font-medium leading-tight"
          :class="idx <= currentStepIdx ? 'text-[#0F172A]' : 'text-[#475569]'"
        >
          {{ step.label }}
        </span>
      </div>
    </div>

    <!-- Telemetry & Details Grid -->
    <div class="grid grid-cols-1 lg:grid-cols-3 gap-4 pt-2">
      <!-- Left: ML Prediction & Audit Log -->
      <div class="space-y-3">
        <div class="grid grid-cols-2 gap-2.5">
          <div class="p-3 rounded-lg bg-[#F8FAFC] border border-[#E2E8F0]">
            <p class="text-[11px] font-medium text-[#475569]">ML Predicted ETA</p>
            <p class="text-base font-bold text-[#0F172A] mt-0.5">
              {{ formatDuration(activeOrder.predicted_eta_sec) }}
            </p>
          </div>
          <div class="p-3 rounded-lg bg-[#F8FAFC] border border-[#E2E8F0]">
            <p class="text-[11px] font-medium text-[#475569]">Order Total</p>
            <p class="text-base font-bold text-[#0F172A] mt-0.5">
              {{ formatCurrencyInr(activeOrder.total_inr) }}
            </p>
          </div>
        </div>

        <div class="p-3 rounded-lg bg-[#F8FAFC] border border-[#E2E8F0] flex items-center justify-between">
          <div class="flex items-center gap-2">
            <Bike class="w-4 h-4 text-[#1E3A8A]" />
            <span class="text-xs font-medium text-[#475569]">Assigned Rider</span>
          </div>
          <span class="text-xs font-semibold text-[#0F172A]">
            {{ activeOrder.rider_name || 'Pending Pack' }}
          </span>
        </div>

        <div class="p-3 rounded-lg bg-[#F8FAFC] border border-[#E2E8F0]">
          <div class="flex items-center gap-1.5 text-xs font-semibold text-[#0F172A] mb-2">
            <Activity class="w-3.5 h-3.5 text-[#1E3A8A]" />
            <span>Status Audit Log</span>
          </div>
          <ul class="space-y-1.5 max-h-36 overflow-y-auto">
            <li
              v-for="ev in activeOrder.events"
              :key="ev.id"
              class="text-[11px] text-[#475569] flex items-start justify-between gap-2"
            >
              <span class="font-medium text-[#0F172A]">{{ ev.to_status }}</span>
              <span class="truncate flex-1">{{ ev.note }}</span>
            </li>
          </ul>
        </div>
      </div>

      <!-- Right: Map Slot -->
      <div class="lg:col-span-2">
        <slot name="map" :order="activeOrder">
          <div class="h-full min-h-[240px] rounded-xl border border-dashed border-[#E2E8F0] bg-[#F8FAFC] flex items-center justify-center text-xs text-[#475569]">
            <AlertTriangle class="w-4 h-4 mr-1.5 text-slate-400" />
            <span>Live dispatch map loading...</span>
          </div>
        </slot>
      </div>
    </div>
  </section>
</template>
