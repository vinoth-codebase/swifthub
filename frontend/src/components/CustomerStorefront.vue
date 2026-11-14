<script setup>
import { computed, ref } from 'vue'
import {
  Search,
  MapPin,
  Plus,
  Minus,
  ShoppingBag,
  AlertTriangle,
  Package,
  Milk,
  Croissant,
  Leaf,
  Cookie,
  Coffee,
  Boxes,
} from 'lucide-vue-next'
import { useHubStore } from '../stores/hubStore'
import { useCartStore } from '../stores/cartStore'
import { formatCurrencyInr } from '../utils/sla'

const hubStore = useHubStore()
const cartStore = useCartStore()

const searchQuery = ref('')
const selectedCategory = ref('All')

const categories = ['All', 'Dairy', 'Bakery', 'Produce', 'Snacks', 'Beverages', 'Pantry']

const categoryIconMap = {
  Dairy: Milk,
  Bakery: Croissant,
  Produce: Leaf,
  Snacks: Cookie,
  Beverages: Coffee,
  Pantry: Boxes,
}

const filteredInventory = computed(() => {
  return hubStore.inventory.filter((item) => {
    const matchCategory =
      selectedCategory.value === 'All' || item.category === selectedCategory.value
    const term = searchQuery.value.trim().toLowerCase()
    const matchSearch =
      !term ||
      item.name.toLowerCase().includes(term) ||
      item.sku.toLowerCase().includes(term) ||
      item.aisle_code.toLowerCase().includes(term)
    return matchCategory && matchSearch
  })
})

function getCartQty(productId) {
  const found = cartStore.items.find((i) => i.product_id === productId)
  return found ? found.quantity : 0
}

function getCategoryIcon(category) {
  return categoryIconMap[category] || Package
}

async function onHubChange(event) {
  cartStore.clearCart()
  await hubStore.selectStore(Number(event.target.value))
}
</script>

<template>
  <div class="space-y-6">
    <!-- Hub Selector & Summary Banner -->
    <div class="bg-white border border-[#E2E8F0] rounded-xl p-5 flex flex-col md:flex-row md:items-center md:justify-between gap-4">
      <div class="flex items-start gap-3">
        <div class="w-10 h-10 rounded-lg bg-[#EFF6FF] text-[#1E3A8A] flex items-center justify-center shrink-0">
          <MapPin class="w-5 h-5" />
        </div>
        <div>
          <div class="flex items-center gap-2 flex-wrap">
            <h1 class="text-lg font-semibold text-[#0F172A]">Hyperlocal Dark-Store Storefront</h1>
            <span class="text-xs font-medium px-2 py-0.5 rounded-full bg-emerald-50 text-emerald-700 border border-emerald-200">
              10-Min SLA Target
            </span>
          </div>
          <p class="text-sm text-[#475569] mt-0.5">
            Live inventory synced over WebSockets with atomic checkout reservation.
          </p>
        </div>
      </div>

      <div class="flex items-center gap-3 flex-wrap">
        <label class="flex items-center gap-2 text-sm text-[#475569]">
          <span class="font-medium text-[#0F172A]">Active Hub:</span>
          <select
            :value="hubStore.selectedStoreId"
            @change="onHubChange"
            class="bg-[#F8FAFC] border border-[#E2E8F0] rounded-lg px-3 py-2 text-sm font-medium text-[#0F172A] focus:outline-none focus:ring-2 focus:ring-[#1D4ED8]"
          >
            <option v-for="store in hubStore.stores" :key="store.id" :value="store.id">
              {{ store.name }} ({{ store.active_pickers }} pickers)
            </option>
          </select>
        </label>

        <button
          type="button"
          @click="cartStore.openDrawer()"
          class="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-[#1E3A8A] hover:bg-[#1D4ED8] text-white text-sm font-medium transition-colors"
        >
          <ShoppingBag class="w-4 h-4" />
          <span>Cart</span>
          <span
            v-if="cartStore.itemCount > 0"
            class="ml-0.5 px-1.5 py-0.5 text-xs font-semibold rounded-full bg-white text-[#1E3A8A]"
          >
            {{ cartStore.itemCount }}
          </span>
        </button>
      </div>
    </div>

    <!-- Search & Category Filters -->
    <div class="flex flex-col md:flex-row gap-3 md:items-center md:justify-between">
      <div class="flex items-center gap-1.5 overflow-x-auto pb-1">
        <button
          v-for="cat in categories"
          :key="cat"
          type="button"
          @click="selectedCategory = cat"
          class="px-3 py-1.5 rounded-lg text-sm font-medium border transition-colors whitespace-nowrap"
          :class="
            selectedCategory === cat
              ? 'bg-[#1E3A8A] text-white border-[#1E3A8A]'
              : 'bg-white text-[#475569] border-[#E2E8F0] hover:bg-slate-50 hover:text-[#0F172A]'
          "
        >
          {{ cat }}
        </button>
      </div>

      <div class="relative w-full md:w-72">
        <Search class="w-4 h-4 text-[#475569] absolute left-3 top-1/2 -translate-y-1/2" />
        <input
          v-model="searchQuery"
          type="text"
          placeholder="Search SKU, item, or aisle..."
          class="w-full pl-9 pr-3 py-2 bg-white border border-[#E2E8F0] rounded-lg text-sm text-[#0F172A] placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-[#1D4ED8]"
        />
      </div>
    </div>

    <!-- Product Grid -->
    <div v-if="filteredInventory.length === 0" class="bg-white border border-[#E2E8F0] rounded-xl p-10 text-center text-sm text-[#475569]">
      No products match the current filter.
    </div>

    <div v-else class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
      <div
        v-for="item in filteredInventory"
        :key="item.id"
        class="bg-white border border-[#E2E8F0] rounded-xl p-4 flex flex-col justify-between gap-4 hover:border-slate-300 transition-colors"
      >
        <div class="space-y-3">
          <div class="flex items-start justify-between gap-2">
            <div class="w-10 h-10 rounded-lg bg-[#F8FAFC] border border-[#E2E8F0] text-[#1E3A8A] flex items-center justify-center shrink-0">
              <component :is="getCategoryIcon(item.category)" class="w-5 h-5" />
            </div>
            <div class="flex items-center gap-1.5 flex-wrap justify-end">
              <span class="text-xs font-medium px-2 py-0.5 rounded bg-slate-100 text-[#475569]">
                {{ item.aisle_code }}
              </span>
              <span
                v-if="item.stock_available === 0"
                class="text-xs font-medium px-2 py-0.5 rounded border bg-rose-50 text-rose-700 border-rose-200"
              >
                Out of Stock
              </span>
              <span
                v-else-if="item.stock_available <= item.reorder_threshold"
                class="inline-flex items-center gap-1 text-xs font-medium px-2 py-0.5 rounded border bg-amber-50 text-amber-800 border-amber-200"
              >
                <AlertTriangle class="w-3 h-3" />
                Only {{ item.stock_available }} left
              </span>
              <span
                v-else
                class="text-xs font-medium px-2 py-0.5 rounded border bg-emerald-50 text-emerald-700 border-emerald-200"
              >
                {{ item.stock_available }} in stock
              </span>
            </div>
          </div>

          <div>
            <p class="text-xs font-mono text-[#475569]">{{ item.sku }}</p>
            <h3 class="text-sm font-semibold text-[#0F172A] mt-0.5 leading-snug">
              {{ item.name }}
            </h3>
          </div>
        </div>

        <div class="flex items-center justify-between pt-3 border-t border-[#E2E8F0]">
          <div>
            <span class="text-base font-bold text-[#0F172A]">{{ formatCurrencyInr(item.price_inr) }}</span>
            <p v-if="item.stock_reserved > 0" class="text-[11px] text-[#475569]">
              {{ item.stock_reserved }} reserved in active orders
            </p>
          </div>

          <div v-if="getCartQty(item.product_id) > 0" class="inline-flex items-center border border-[#1E3A8A] rounded-lg overflow-hidden">
            <button
              type="button"
              @click="cartStore.updateQuantity(item.product_id, -1)"
              class="px-2.5 py-1.5 text-[#1E3A8A] hover:bg-[#EFF6FF] transition-colors"
              aria-label="Decrease quantity"
            >
              <Minus class="w-3.5 h-3.5" />
            </button>
            <span class="px-3 py-1.5 text-sm font-semibold text-[#0F172A] bg-white">
              {{ getCartQty(item.product_id) }}
            </span>
            <button
              type="button"
              @click="cartStore.addItem(item)"
              :disabled="getCartQty(item.product_id) >= item.stock_available"
              class="px-2.5 py-1.5 text-[#1E3A8A] hover:bg-[#EFF6FF] disabled:opacity-40 transition-colors"
              aria-label="Increase quantity"
            >
              <Plus class="w-3.5 h-3.5" />
            </button>
          </div>

          <button
            v-else
            type="button"
            :disabled="item.stock_available === 0"
            @click="cartStore.addItem(item)"
            class="inline-flex items-center gap-1.5 px-3.5 py-1.5 rounded-lg text-sm font-medium border transition-colors"
            :class="
              item.stock_available === 0
                ? 'bg-slate-100 text-slate-400 border-[#E2E8F0] cursor-not-allowed'
                : 'bg-white text-[#1E3A8A] border-[#1E3A8A] hover:bg-[#1E3A8A] hover:text-white'
            "
          >
            <Plus class="w-3.5 h-3.5" />
            <span>Add</span>
          </button>
        </div>
      </div>
    </div>
  </div>
</template>
