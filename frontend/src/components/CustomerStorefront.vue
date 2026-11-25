<script setup>
import { computed, reactive, ref } from 'vue'
import {
  Search,
  MapPin,
  Plus,
  Minus,
  ShoppingBag,
  AlertTriangle,
  Package,
} from 'lucide-vue-next'
import { useAuthStore } from '../stores/authStore'
import { useHubStore } from '../stores/hubStore'
import { useCartStore } from '../stores/cartStore'
import { formatCurrencyInr } from '../utils/sla'
import LiveOrderTracker from './LiveOrderTracker.vue'

const authStore = useAuthStore()
const hubStore = useHubStore()
const cartStore = useCartStore()

const searchQuery = ref('')
const selectedCategory = ref('All')
const failedImages = reactive({})

const categories = ['All', 'Dairy', 'Bakery', 'Produce', 'Snacks', 'Beverages', 'Pantry']

const filteredInventory = computed(() => {
  return hubStore.inventory.filter((item) => {
    const matchCategory =
      selectedCategory.value === 'All' || item.category === selectedCategory.value
    const term = searchQuery.value.trim().toLowerCase()
    const matchSearch =
      !term ||
      item.name.toLowerCase().includes(term) ||
      item.category.toLowerCase().includes(term)
    return matchCategory && matchSearch
  })
})

function getCartQty(productId) {
  const found = cartStore.items.find((i) => i.product_id === productId)
  return found ? found.quantity : 0
}

function getEncodedImageUrl(url) {
  if (!url) return ''
  return encodeURI(url)
}

function onImageError(itemId) {
  failedImages[itemId] = true
}

async function onHubChange(event) {
  cartStore.clearCart()
  await hubStore.selectStore(Number(event.target.value))
}
</script>

<template>
  <div class="space-y-5">
    <!-- Hub Selector & Summary Banner -->
    <div class="relative overflow-hidden bg-white border border-[#E9E5F5] rounded-xl p-5 flex flex-col md:flex-row md:items-center md:justify-between gap-4 shadow-sm">
      <div class="absolute inset-x-0 top-0 h-1 bg-gradient-to-r from-[#4C1D95] via-[#6D28D9] to-[#A21CAF]" />
      <div class="flex items-start gap-3">
        <div class="w-10 h-10 rounded-lg bg-[#EDE9FE] text-[#5B21B6] flex items-center justify-center shrink-0">
          <MapPin class="w-5 h-5" />
        </div>
        <div>
          <h1 class="text-lg font-bold text-[#1E1B4B]">Swift the groceries in minutes</h1>
          <p class="text-sm text-[#475569] mt-0.5">
            Fresh essentials delivered from your nearest Bangalore hub.
          </p>
        </div>
      </div>

      <div class="flex items-center gap-3 flex-wrap">
        <label class="flex items-center gap-2 text-sm text-[#475569]">
          <span class="font-medium text-[#1E1B4B]">Delivery Hub:</span>
          <select
            :value="hubStore.selectedStoreId"
            @change="onHubChange"
            class="bg-[#FAF8FF] border border-[#E9E5F5] rounded-lg px-3 py-2 text-sm font-medium text-[#1E1B4B] focus:outline-none focus:ring-2 focus:ring-[#7C3AED]"
          >
            <option v-for="store in hubStore.stores" :key="store.id" :value="store.id">
              {{ store.name }}
            </option>
          </select>
        </label>

        <button
          type="button"
          @click="cartStore.openDrawer()"
          class="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-[#5B21B6] hover:bg-[#4C1D95] text-white text-sm font-medium transition-colors shadow-sm"
        >
          <ShoppingBag class="w-4 h-4" />
          <span>Cart</span>
          <span
            v-if="cartStore.itemCount > 0"
            class="ml-0.5 px-1.5 py-0.5 text-xs font-semibold rounded-full bg-white text-[#5B21B6]"
          >
            {{ cartStore.itemCount }}
          </span>
        </button>
      </div>
    </div>

    <!-- Live Order Tracker (Authenticated Customers with Orders) -->
    <LiveOrderTracker v-if="authStore.isCustomer && hubStore.orders.length > 0" />

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
              ? 'bg-[#5B21B6] text-white border-[#5B21B6]'
              : 'bg-white text-[#475569] border-[#E9E5F5] hover:bg-[#F5F3FF] hover:text-[#1E1B4B]'
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
          placeholder="Search groceries, milk, snacks..."
          class="w-full pl-9 pr-3 py-2 bg-white border border-[#E9E5F5] rounded-lg text-sm text-[#0F172A] placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-[#7C3AED]"
        />
      </div>
    </div>

    <!-- Product Grid (Compact 5-Column Quick-Commerce Layout) -->
    <div
      v-if="filteredInventory.length === 0"
      class="bg-white border border-[#E9E5F5] rounded-xl p-10 text-center text-sm text-[#475569]"
    >
      No products match the current filter.
    </div>

    <div v-else class="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 gap-3.5">
      <div
        v-for="item in filteredInventory"
        :key="item.id"
        class="bg-white border border-[#E9E5F5] rounded-xl p-3 flex flex-col justify-between hover:border-[#C4B5FD] hover:shadow-sm transition-all"
      >
        <div>
          <!-- Compact Product Image Container with Conditional Stock Badge -->
          <div class="relative h-32 w-full rounded-lg bg-white border border-[#E9E5F5] overflow-hidden flex items-center justify-center p-2">
            <img
              v-if="item.image_url && !failedImages[item.id]"
              :src="getEncodedImageUrl(item.image_url)"
              :alt="item.name"
              loading="lazy"
              @error="onImageError(item.id)"
              class="w-full h-full object-contain"
            />
            <div v-else class="flex flex-col items-center justify-center text-slate-400 gap-1">
              <Package class="w-7 h-7" />
              <span class="text-[11px] font-medium">Product Photo</span>
            </div>

            <!-- Conditional Stock Badge: Out of Stock (0) or Low Stock (1..4) ONLY -->
            <span
              v-if="item.stock_available === 0"
              class="absolute top-1.5 right-1.5 text-[11px] font-semibold px-2 py-0.5 rounded-md border bg-rose-50 text-rose-700 border-rose-200 shadow-sm"
            >
              Out of Stock
            </span>
            <span
              v-else-if="item.stock_available > 0 && item.stock_available < 5"
              class="absolute top-1.5 right-1.5 inline-flex items-center gap-1 text-[11px] font-semibold px-2 py-0.5 rounded-md border bg-amber-50 text-amber-800 border-amber-200 shadow-sm"
            >
              <AlertTriangle class="w-3 h-3" />
              <span>Only {{ item.stock_available }} left</span>
            </span>
          </div>

          <!-- Compact Product Name -->
          <h3 class="text-xs sm:text-sm font-semibold text-slate-900 line-clamp-2 min-h-[2.25rem] leading-snug mt-2">
            {{ item.name }}
          </h3>
        </div>

        <!-- Bottom Row: Price + Compact Add / Solid Violet Stepper -->
        <div class="flex items-center justify-between pt-2.5 mt-2 border-t border-[#E9E5F5]">
          <span class="text-sm font-bold text-slate-900">
            {{ formatCurrencyInr(item.price_inr) }}
          </span>

          <div
            v-if="getCartQty(item.product_id) > 0"
            class="inline-flex items-center bg-[#6D28D9] text-white rounded-lg overflow-hidden shadow-sm"
          >
            <button
              type="button"
              @click="cartStore.updateQuantity(item.product_id, -1)"
              class="px-2 py-1 text-white hover:bg-[#5B21B6] transition-colors"
              aria-label="Decrease quantity"
            >
              <Minus class="w-3 h-3" />
            </button>
            <span class="px-2 py-1 text-xs font-semibold text-white">
              {{ getCartQty(item.product_id) }}
            </span>
            <button
              type="button"
              @click="cartStore.addItem(item)"
              :disabled="getCartQty(item.product_id) >= item.stock_available"
              class="px-2 py-1 text-white hover:bg-[#5B21B6] disabled:opacity-40 transition-colors"
              aria-label="Increase quantity"
            >
              <Plus class="w-3 h-3" />
            </button>
          </div>

          <button
            v-else
            type="button"
            :disabled="item.stock_available === 0"
            @click="cartStore.addItem(item)"
            class="inline-flex items-center gap-1 px-3 py-1 text-xs font-semibold rounded-lg border transition-colors"
            :class="
              item.stock_available === 0
                ? 'bg-slate-100 text-slate-400 border-[#E9E5F5] cursor-not-allowed'
                : 'border-[#7C3AED] text-[#6D28D9] bg-[#F5F3FF]/50 hover:bg-[#6D28D9] hover:text-white'
            "
          >
            <Plus class="w-3 h-3" />
            <span>Add</span>
          </button>
        </div>
      </div>
    </div>
  </div>
</template>
