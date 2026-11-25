<script setup>
import { computed, ref } from 'vue'
import { Bike, Play, MapPin, Navigation, CheckCircle2, ExternalLink } from 'lucide-vue-next'
import { useHubStore } from '../stores/hubStore'
import LiveDispatchMap from './LiveDispatchMap.vue'

const emit = defineEmits(['track-order'])

const hubStore = useHubStore()
const lastSimulatedOrder = ref(null)

const idleCount = computed(
  () => hubStore.riders.filter((r) => r.status === 'IDLE').length
)
const activeCount = computed(
  () => hubStore.riders.filter((r) => r.status !== 'IDLE').length
)

function assignedOrderForRider(riderId) {
  return hubStore.orders.find(
    (o) =>
      o.rider_id === riderId &&
      ['PACKED', 'OUT_FOR_DELIVERY'].includes(o.status)
  )
}

function statusBadgeClass(status) {
  if (status === 'DELIVERING') return 'bg-[#F5F3FF] text-[#6D28D9] border-[#DDD6FE]'
  if (status === 'ASSIGNED') return 'bg-amber-50 text-amber-800 border-amber-200'
  return 'bg-emerald-50 text-emerald-700 border-emerald-200'
}

async function handleRunSimulation() {
  const order = await hubStore.runDemoSimulation()
  if (order) {
    lastSimulatedOrder.value = order
  }
}

function openTracker(orderId) {
  hubStore.trackedOrderId = orderId
  emit('track-order', orderId)
}
</script>

<template>
  <div class="space-y-6">
    <!-- Top Header & Prominent Live Demo Trigger -->
    <div class="bg-white border border-[#E9E5F5] rounded-xl p-5 flex flex-col lg:flex-row lg:items-center lg:justify-between gap-4">
      <div class="flex items-start gap-3">
        <div class="w-10 h-10 rounded-lg bg-[#EDE9FE] text-[#5B21B6] flex items-center justify-center shrink-0">
          <Bike class="w-5 h-5" />
        </div>
        <div>
          <h1 class="text-lg font-semibold text-[#1E1B4B]">Rider Dispatch & Fleet Telemetry</h1>
          <p class="text-sm text-[#475569] mt-0.5">
            Nearest-rider auto-assignment on pack completion with live WebSocket GPS streaming.
          </p>
        </div>
      </div>

      <button
        type="button"
        :disabled="hubStore.simulationRunning"
        @click="handleRunSimulation"
        class="inline-flex items-center justify-center gap-2 px-5 py-2.5 rounded-lg bg-[#5B21B6] hover:bg-[#4C1D95] disabled:bg-slate-400 text-white text-sm font-semibold shadow-sm transition-colors shrink-0"
      >
        <Play class="w-4 h-4" />
        <span>
          {{ hubStore.simulationRunning ? 'Starting Live Demo...' : 'Run Live Demo Simulation' }}
        </span>
      </button>
    </div>

    <!-- Simulation Confirmation Banner -->
    <div
      v-if="lastSimulatedOrder"
      class="p-4 rounded-xl bg-[#F5F3FF] border border-[#DDD6FE] flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3"
    >
      <div class="flex items-center gap-2.5 text-sm text-[#5B21B6]">
        <CheckCircle2 class="w-5 h-5 shrink-0" />
        <span>
          Live demo order <strong>#ORD-{{ lastSimulatedOrder.id }}</strong> spawned. Watch the full ~35s picking, auto-dispatch, and GPS delivery animation in real time.
        </span>
      </div>
      <button
        type="button"
        @click="openTracker(lastSimulatedOrder.id)"
        class="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-white border border-[#DDD6FE] text-xs font-semibold text-[#5B21B6] hover:bg-[#EDE9FE] shrink-0"
      >
        <span>View in Ops Queue</span>
        <ExternalLink class="w-3.5 h-3.5" />
      </button>
    </div>

    <!-- Fleet KPI Cards -->
    <div class="grid grid-cols-1 sm:grid-cols-3 gap-4">
      <div class="bg-white border border-[#E9E5F5] rounded-xl p-4">
        <p class="text-xs font-medium text-[#475569]">Total Hub Riders</p>
        <p class="text-2xl font-bold text-[#0F172A] mt-1">{{ hubStore.riders.length }}</p>
      </div>
      <div class="bg-white border border-[#E9E5F5] rounded-xl p-4">
        <p class="text-xs font-medium text-[#475569]">Idle & Ready</p>
        <p class="text-2xl font-bold text-emerald-700 mt-1">{{ idleCount }}</p>
      </div>
      <div class="bg-white border border-[#E9E5F5] rounded-xl p-4">
        <p class="text-xs font-medium text-[#475569]">Assigned / Delivering</p>
        <p class="text-2xl font-bold text-[#6D28D9] mt-1">{{ activeCount }}</p>
      </div>
    </div>

    <!-- Fleet Map + Live Rider Table -->
    <div class="grid grid-cols-1 lg:grid-cols-5 gap-6">
      <div class="lg:col-span-3 bg-white border border-[#E9E5F5] rounded-xl p-4 space-y-3">
        <div class="flex items-center justify-between">
          <h2 class="text-sm font-semibold text-[#1E1B4B] flex items-center gap-2">
            <Navigation class="w-4 h-4 text-[#5B21B6]" />
            <span>Live Fleet Map ({{ hubStore.currentStore?.name }})</span>
          </h2>
          <span class="text-xs text-[#475569]">Real-time GPS markers</span>
        </div>

        <LiveDispatchMap
          :store="hubStore.currentStore"
          :riders="hubStore.riders"
          height-class="h-80"
        />
      </div>

      <div class="lg:col-span-2 bg-white border border-[#E9E5F5] rounded-xl overflow-hidden flex flex-col">
        <div class="px-4 py-3.5 border-b border-[#E9E5F5] flex items-center justify-between">
          <h2 class="text-sm font-semibold text-[#1E1B4B]">Hub Rider Roster</h2>
          <span class="text-xs text-[#475569]">Live status</span>
        </div>

        <div class="overflow-x-auto flex-1">
          <table class="w-full text-left border-collapse">
            <thead>
              <tr class="bg-[#FAF8FF] border-b border-[#E9E5F5] text-[11px] font-semibold uppercase tracking-wider text-[#475569]">
                <th class="px-4 py-2.5">Rider</th>
                <th class="px-4 py-2.5">Status</th>
                <th class="px-4 py-2.5">Assignment</th>
              </tr>
            </thead>
            <tbody class="divide-y divide-[#E9E5F5] text-xs">
              <tr v-for="rider in hubStore.riders" :key="rider.id" class="hover:bg-[#FAF8FF]">
                <td class="px-4 py-3">
                  <p class="font-semibold text-[#0F172A]">{{ rider.name }}</p>
                  <p class="text-[11px] text-[#475569] flex items-center gap-1 mt-0.5">
                    <MapPin class="w-3 h-3" />
                    <span>{{ rider.current_lat.toFixed(4) }}, {{ rider.current_lng.toFixed(4) }}</span>
                  </p>
                </td>
                <td class="px-4 py-3">
                  <span
                    class="inline-flex px-2 py-0.5 rounded-full text-[11px] font-semibold border"
                    :class="statusBadgeClass(rider.status)"
                  >
                    {{ rider.status }}
                  </span>
                </td>
                <td class="px-4 py-3 text-[#475569]">
                  <template v-if="assignedOrderForRider(rider.id)">
                    <button
                      type="button"
                      @click="openTracker(assignedOrderForRider(rider.id).id)"
                      class="font-semibold text-[#6D28D9] hover:underline"
                    >
                      #ORD-{{ assignedOrderForRider(rider.id).id }}
                    </button>
                    <p class="text-[11px] truncate max-w-[130px]">
                      {{ assignedOrderForRider(rider.id).customer_name }}
                    </p>
                  </template>
                  <span v-else class="text-slate-400">Standby at hub</span>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>
  </div>
</template>
