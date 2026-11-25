<script setup>
import { computed, ref } from 'vue'
import { AlertTriangle, PackagePlus, CheckCircle2 } from 'lucide-vue-next'
import { useHubStore } from '../stores/hubStore'

const hubStore = useHubStore()
const restockingId = ref(null)

const sortedLowStock = computed(() =>
  [...hubStore.lowStockItems].sort((a, b) => a.stock_available - b.stock_available)
)

async function handleRestock(item) {
  restockingId.value = item.product_id
  try {
    await hubStore.restockSku(item.product_id, 10)
  } finally {
    restockingId.value = null
  }
}
</script>

<template>
  <aside class="bg-white border border-[#E9E5F5] rounded-xl p-5 space-y-4">
    <div class="flex items-center justify-between gap-2">
      <div class="flex items-center gap-2">
        <AlertTriangle class="w-4 h-4 text-amber-600" />
        <h2 class="text-sm font-semibold text-[#1E1B4B]">Low-Stock Reorder Alerts</h2>
      </div>
      <span
        class="text-xs font-semibold px-2 py-0.5 rounded-full border"
        :class="
          sortedLowStock.length > 0
            ? 'bg-amber-50 text-amber-800 border-amber-200'
            : 'bg-emerald-50 text-emerald-700 border-emerald-200'
        "
      >
        {{ sortedLowStock.length }} SKUs
      </span>
    </div>

    <p class="text-xs text-[#475569]">
      SKUs at or below reorder threshold in {{ hubStore.currentStore?.name || 'current hub' }}.
    </p>

    <div
      v-if="sortedLowStock.length === 0"
      class="p-6 rounded-lg bg-emerald-50/60 border border-emerald-200 text-center space-y-1.5"
    >
      <CheckCircle2 class="w-6 h-6 text-emerald-600 mx-auto" />
      <p class="text-xs font-semibold text-emerald-800">All SKUs Above Threshold</p>
      <p class="text-[11px] text-emerald-700">No immediate replenishment required.</p>
    </div>

    <div v-else class="space-y-2.5 max-h-[540px] overflow-y-auto pr-1">
      <div
        v-for="item in sortedLowStock"
        :key="item.id"
        class="p-3 rounded-lg border bg-[#FAF8FF] space-y-2.5"
        :class="item.stock_available === 0 ? 'border-rose-200 bg-rose-50/40' : 'border-[#E9E5F5]'"
      >
        <div class="flex items-start justify-between gap-2">
          <div class="min-w-0">
            <p class="text-xs font-semibold text-[#0F172A] leading-snug">{{ item.name }}</p>
            <p class="text-[11px] text-[#475569] mt-0.5">
              {{ item.aisle_code }} &middot; {{ item.sku }}
            </p>
          </div>
          <span
            class="text-[11px] font-bold px-2 py-0.5 rounded border shrink-0"
            :class="
              item.stock_available === 0
                ? 'bg-rose-50 text-rose-700 border-rose-200'
                : 'bg-amber-50 text-amber-800 border-amber-200'
            "
          >
            {{ item.stock_available }} / {{ item.reorder_threshold }}
          </span>
        </div>

        <button
          type="button"
          :disabled="restockingId === item.product_id"
          @click="handleRestock(item)"
          class="w-full inline-flex items-center justify-center gap-1.5 px-3 py-1.5 rounded-lg bg-[#F5F3FF]/50 hover:bg-[#6D28D9] hover:text-white text-[#6D28D9] border border-[#7C3AED] disabled:opacity-50 text-xs font-semibold transition-colors"
        >
          <PackagePlus class="w-3.5 h-3.5" />
          <span>{{ restockingId === item.product_id ? 'Restocking...' : 'Restock (+10)' }}</span>
        </button>
      </div>
    </div>
  </aside>
</template>
