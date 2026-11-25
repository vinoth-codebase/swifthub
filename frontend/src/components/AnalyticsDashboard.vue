<script setup>
import { onMounted, onUnmounted, ref, watch } from 'vue'
import { BarChart3, Clock, CheckCircle2, Timer, Truck } from 'lucide-vue-next'
import Chart from 'chart.js/auto'
import { useHubStore } from '../stores/hubStore'
import { formatDuration } from '../utils/sla'

const hubStore = useHubStore()

const slaCanvas = ref(null)
const latencyCanvas = ref(null)
const categoryCanvas = ref(null)

let slaChart = null
let latencyChart = null
let categoryChart = null

function destroyCharts() {
  if (slaChart) {
    slaChart.destroy()
    slaChart = null
  }
  if (latencyChart) {
    latencyChart.destroy()
    latencyChart = null
  }
  if (categoryChart) {
    categoryChart.destroy()
    categoryChart = null
  }
}

function renderCharts() {
  const data = hubStore.analytics
  if (!data) return
  destroyCharts()

  if (slaCanvas.value) {
    slaChart = new Chart(slaCanvas.value, {
      type: 'doughnut',
      data: {
        labels: ['Within 10-Min SLA', 'SLA Breached (>10m)'],
        datasets: [
          {
            data: [data.sla_met_count || 0, data.sla_breached_count || 0],
            backgroundColor: ['#059669', '#DC2626'],
            borderColor: '#FFFFFF',
            borderWidth: 2,
          },
        ],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        cutout: '66%',
        plugins: {
          legend: {
            position: 'bottom',
            labels: { color: '#475569', boxWidth: 12, font: { size: 12 } },
          },
        },
      },
    })
  }

  if (latencyCanvas.value) {
    latencyChart = new Chart(latencyCanvas.value, {
      type: 'bar',
      data: {
        labels: ['Picking Time', 'Dispatch Wait', 'Delivery Time'],
        datasets: [
          {
            label: 'Average Seconds',
            data: [
              data.avg_pick_time_sec || 0,
              data.avg_dispatch_wait_sec || 0,
              data.avg_delivery_time_sec || 0,
            ],
            backgroundColor: ['#5B21B6', '#64748B', '#7C3AED'],
            borderRadius: 6,
            barThickness: 38,
          },
        ],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: { display: false },
        },
        scales: {
          y: {
            beginAtZero: true,
            grid: { color: '#E2E8F0' },
            ticks: { color: '#475569', callback: (v) => `${v}s` },
          },
          x: {
            grid: { display: false },
            ticks: { color: '#0F172A', font: { size: 12 } },
          },
        },
      },
    })
  }

  if (categoryCanvas.value) {
    const categories = data.category_volume || []
    categoryChart = new Chart(categoryCanvas.value, {
      type: 'bar',
      data: {
        labels: categories.map((c) => c.category),
        datasets: [
          {
            label: 'Units Ordered',
            data: categories.map((c) => c.units),
            backgroundColor: '#5B21B6',
            borderRadius: 6,
            barThickness: 22,
          },
        ],
      },
      options: {
        indexAxis: 'y',
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: { display: false },
        },
        scales: {
          x: {
            beginAtZero: true,
            grid: { color: '#E2E8F0' },
            ticks: { color: '#475569', precision: 0 },
          },
          y: {
            grid: { display: false },
            ticks: { color: '#0F172A', font: { size: 12 } },
          },
        },
      },
    })
  }
}

onMounted(async () => {
  if (!hubStore.analytics) {
    await hubStore.refreshAnalytics()
  }
  renderCharts()
})

watch(
  () => hubStore.analytics,
  () => {
    renderCharts()
  },
  { deep: true }
)

onUnmounted(() => {
  destroyCharts()
})
</script>

<template>
  <div class="space-y-6">
    <!-- Header -->
    <div class="bg-white border border-[#E9E5F5] rounded-xl p-5 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
      <div class="flex items-start gap-3">
        <div class="w-10 h-10 rounded-lg bg-[#EDE9FE] text-[#5B21B6] flex items-center justify-center shrink-0">
          <BarChart3 class="w-5 h-5" />
        </div>
        <div>
          <h1 class="text-lg font-semibold text-[#1E1B4B]">Operations Analytics Dashboard</h1>
          <p class="text-sm text-[#475569] mt-0.5">
            Real-time SLA compliance, picking latency, and category throughput derived from append-only order events.
          </p>
        </div>
      </div>

      <span class="text-xs font-medium px-3 py-1.5 rounded-lg bg-[#FAF8FF] border border-[#E9E5F5] text-[#0F172A]">
        Hub: {{ hubStore.currentStore?.name || 'All Hubs' }}
      </span>
    </div>

    <!-- KPI Grid -->
    <div v-if="hubStore.analytics" class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
      <div class="bg-white border border-[#E9E5F5] rounded-xl p-4">
        <div class="flex items-center justify-between text-xs font-medium text-[#475569]">
          <span>10-Min SLA Compliance</span>
          <CheckCircle2 class="w-4 h-4 text-emerald-600" />
        </div>
        <p class="text-2xl font-bold text-[#0F172A] mt-2">
          {{ hubStore.analytics.sla_compliance_pct }}%
        </p>
        <p class="text-[11px] text-[#475569] mt-1">
          {{ hubStore.analytics.sla_met_count }} of {{ hubStore.analytics.delivered_orders }} delivered on time
        </p>
      </div>

      <div class="bg-white border border-[#E9E5F5] rounded-xl p-4">
        <div class="flex items-center justify-between text-xs font-medium text-[#475569]">
          <span>Avg Fulfillment Time</span>
          <Clock class="w-4 h-4 text-[#5B21B6]" />
        </div>
        <p class="text-2xl font-bold text-[#0F172A] mt-2">
          {{ formatDuration(hubStore.analytics.avg_total_fulfillment_sec) }}
        </p>
        <p class="text-[11px] text-[#475569] mt-1">
          Across {{ hubStore.analytics.total_orders }} total orders
        </p>
      </div>

      <div class="bg-white border border-[#E9E5F5] rounded-xl p-4">
        <div class="flex items-center justify-between text-xs font-medium text-[#475569]">
          <span>Avg Picking Duration</span>
          <Timer class="w-4 h-4 text-[#7C3AED]" />
        </div>
        <p class="text-2xl font-bold text-[#0F172A] mt-2">
          {{ formatDuration(hubStore.analytics.avg_pick_time_sec) }}
        </p>
        <p class="text-[11px] text-[#475569] mt-1">
          Aisle sweep from PICKING to PACKED
        </p>
      </div>

      <div class="bg-white border border-[#E9E5F5] rounded-xl p-4">
        <div class="flex items-center justify-between text-xs font-medium text-[#475569]">
          <span>Avg Last-Mile Delivery</span>
          <Truck class="w-4 h-4 text-amber-600" />
        </div>
        <p class="text-2xl font-bold text-[#0F172A] mt-2">
          {{ formatDuration(hubStore.analytics.avg_delivery_time_sec) }}
        </p>
        <p class="text-[11px] text-[#475569] mt-1">
          Hub departure to doorstep handover
        </p>
      </div>
    </div>

    <!-- Charts Grid -->
    <div class="grid grid-cols-1 lg:grid-cols-3 gap-6">
      <div class="bg-white border border-[#E9E5F5] rounded-xl p-5 flex flex-col">
        <h2 class="text-sm font-semibold text-[#1E1B4B]">SLA Compliance Breakdown</h2>
        <p class="text-xs text-[#475569] mb-4">Orders delivered within 600s target</p>
        <div class="h-60 relative">
          <canvas ref="slaCanvas" />
        </div>
      </div>

      <div class="bg-white border border-[#E9E5F5] rounded-xl p-5 flex flex-col">
        <h2 class="text-sm font-semibold text-[#1E1B4B]">Picking vs. Delivery Latency</h2>
        <p class="text-xs text-[#475569] mb-4">Average stage duration in seconds</p>
        <div class="h-60 relative">
          <canvas ref="latencyCanvas" />
        </div>
      </div>

      <div class="bg-white border border-[#E9E5F5] rounded-xl p-5 flex flex-col">
        <h2 class="text-sm font-semibold text-[#1E1B4B]">Order Volume by Category</h2>
        <p class="text-xs text-[#475569] mb-4">Total units picked across hub aisles</p>
        <div class="h-60 relative">
          <canvas ref="categoryCanvas" />
        </div>
      </div>
    </div>
  </div>
</template>
