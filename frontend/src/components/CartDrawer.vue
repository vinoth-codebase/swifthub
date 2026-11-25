<script setup>
import { computed, ref, watch } from 'vue'
import { X, Plus, Minus, Trash2, ShoppingBag, AlertCircle, MapPin, LogIn } from 'lucide-vue-next'
import { useAuthStore } from '../stores/authStore'
import { useCartStore } from '../stores/cartStore'
import { useHubStore } from '../stores/hubStore'
import { formatCurrencyInr } from '../utils/sla'

const emit = defineEmits(['order-placed'])

const authStore = useAuthStore()
const cartStore = useCartStore()
const hubStore = useHubStore()

const customerName = ref('')
const selectedDropPreset = ref('near')

const dropPresets = [
  { id: 'near', label: 'Block 4 Residence (~0.8 km)', dLat: 0.0055, dLng: 0.0045 },
  { id: 'mid', label: '100 Feet Road Office (~1.5 km)', dLat: -0.0095, dLng: 0.0085 },
  { id: 'far', label: 'Outer Ring Enclave (~2.4 km)', dLat: 0.0145, dLng: -0.0135 },
]

watch(
  () => [cartStore.isOpen, authStore.user?.full_name],
  ([open, fullName]) => {
    if (open && fullName && !customerName.value) {
      customerName.value = fullName
    }
  }
)

const selectedCoords = computed(() => {
  const store = hubStore.currentStore
  const preset = dropPresets.find((p) => p.id === selectedDropPreset.value) || dropPresets[0]
  if (!store) return { lat: 12.9116, lng: 77.6389 }
  return {
    lat: Number((store.lat + preset.dLat).toFixed(6)),
    lng: Number((store.lng + preset.dLng).toFixed(6)),
  }
})

function promptSignIn() {
  cartStore.closeDrawer()
  authStore.openAuthModal('login')
}

async function handleCheckout() {
  if (!authStore.isAuthenticated) {
    promptSignIn()
    return
  }
  if (!hubStore.currentStore) return
  const order = await cartStore.submitCheckout({
    storeId: hubStore.currentStore.id,
    customerName: customerName.value,
    deliveryLat: selectedCoords.value.lat,
    deliveryLng: selectedCoords.value.lng,
  })
  if (order) {
    customerName.value = authStore.user?.full_name || ''
    hubStore.upsertOrder(order)
    hubStore.trackedOrderId = order.id
    await hubStore.refreshInventory()
    emit('order-placed', order)
  } else {
    await hubStore.refreshInventory()
  }
}
</script>

<template>
  <div v-if="cartStore.isOpen" class="fixed inset-0 z-50 flex justify-end">
    <!-- Backdrop -->
    <div
      class="fixed inset-0 bg-slate-900/40 backdrop-blur-[1px]"
      @click="cartStore.closeDrawer()"
    />

    <!-- Drawer Panel -->
    <aside
      role="dialog"
      aria-modal="true"
      aria-label="Checkout Cart Drawer"
      class="relative z-10 w-full max-w-md bg-white h-full shadow-2xl border-l border-[#E9E5F5] flex flex-col"
    >
      <!-- Header with Explicit Top-Right Close (X) Button -->
      <div class="px-5 py-4 border-b border-[#E9E5F5] flex items-center justify-between">
        <div class="flex items-center gap-2.5">
          <ShoppingBag class="w-5 h-5 text-[#5B21B6]" />
          <div>
            <h2 class="text-base font-semibold text-[#1E1B4B]">Your Express Cart</h2>
            <p class="text-xs text-[#475569]">
              {{ hubStore.currentStore?.name || 'Active Hub' }}
            </p>
          </div>
        </div>

        <button
          type="button"
          @click="cartStore.closeDrawer()"
          aria-label="Close cart drawer"
          class="p-2 rounded-lg text-[#475569] hover:text-[#1E1B4B] hover:bg-[#F5F3FF] border border-transparent hover:border-[#E9E5F5] transition-colors"
        >
          <X class="w-5 h-5" />
        </button>
      </div>

      <!-- Cart Body -->
      <div class="flex-1 overflow-y-auto p-5 space-y-4">
        <div
          v-if="cartStore.checkoutError"
          class="p-3.5 rounded-lg bg-rose-50 border border-rose-200 text-rose-700 text-xs flex items-start gap-2"
        >
          <AlertCircle class="w-4 h-4 shrink-0 mt-0.5" />
          <span>{{ cartStore.checkoutError }}</span>
        </div>

        <div
          v-if="cartStore.items.length === 0"
          class="py-16 text-center text-sm text-[#475569] space-y-2"
        >
          <ShoppingBag class="w-8 h-8 text-slate-300 mx-auto" />
          <p class="font-medium text-[#1E1B4B]">Your cart is empty</p>
          <p class="text-xs">Add items from the catalog to place a quick order.</p>
        </div>

        <div v-else class="space-y-3">
          <div
            v-for="item in cartStore.items"
            :key="item.product_id"
            class="p-3.5 rounded-lg border border-[#E9E5F5] bg-[#FAF8FF] flex items-center justify-between gap-3"
          >
            <div class="min-w-0">
              <p class="text-sm font-medium text-[#0F172A] truncate">{{ item.name }}</p>
              <p class="text-xs text-[#475569] mt-0.5">
                {{ formatCurrencyInr(item.price_inr) }} each
              </p>
            </div>

            <div class="flex items-center gap-2 shrink-0">
              <div class="inline-flex items-center border border-[#E9E5F5] bg-white rounded-md">
                <button
                  type="button"
                  @click="cartStore.updateQuantity(item.product_id, -1)"
                  class="p-1.5 text-[#475569] hover:text-[#5B21B6]"
                  aria-label="Decrease quantity"
                >
                  <Minus class="w-3.5 h-3.5" />
                </button>
                <span class="px-2.5 text-xs font-semibold text-[#0F172A]">
                  {{ item.quantity }}
                </span>
                <button
                  type="button"
                  @click="cartStore.updateQuantity(item.product_id, 1)"
                  :disabled="item.quantity >= item.max_stock"
                  class="p-1.5 text-[#475569] hover:text-[#5B21B6] disabled:opacity-40"
                  aria-label="Increase quantity"
                >
                  <Plus class="w-3.5 h-3.5" />
                </button>
              </div>

              <button
                type="button"
                @click="cartStore.removeItem(item.product_id)"
                class="p-1.5 text-slate-400 hover:text-rose-600 transition-colors"
                aria-label="Remove item"
              >
                <Trash2 class="w-4 h-4" />
              </button>
            </div>
          </div>

          <!-- Sign-in Required Notice for Guests -->
          <div
            v-if="!authStore.isAuthenticated"
            class="p-4 rounded-xl bg-[#F5F3FF] border border-[#DDD6FE] space-y-2"
          >
            <p class="text-xs font-semibold text-[#5B21B6]">Sign in required to checkout</p>
            <p class="text-xs text-[#475569]">
              Please sign in or create a customer account to reserve inventory and track your delivery live.
            </p>
          </div>

          <!-- Customer & Drop-Off Form -->
          <div v-else class="pt-4 border-t border-[#E9E5F5] space-y-3">
            <div>
              <label for="customer-name-input" class="block text-xs font-semibold text-[#0F172A] mb-1">
                Recipient Name
              </label>
              <input
                id="customer-name-input"
                v-model="customerName"
                type="text"
                placeholder="Enter recipient full name"
                class="w-full px-3 py-2 rounded-lg border border-[#E9E5F5] bg-white text-sm text-[#0F172A] placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-[#7C3AED]"
              />
            </div>

            <div>
              <label for="drop-zone-select" class="block text-xs font-semibold text-[#0F172A] mb-1">
                Delivery Pin Location
              </label>
              <select
                id="drop-zone-select"
                v-model="selectedDropPreset"
                class="w-full px-3 py-2 rounded-lg border border-[#E9E5F5] bg-white text-sm text-[#0F172A] focus:outline-none focus:ring-2 focus:ring-[#7C3AED]"
              >
                <option v-for="preset in dropPresets" :key="preset.id" :value="preset.id">
                  {{ preset.label }}
                </option>
              </select>
              <p class="mt-1 text-[11px] text-[#475569] flex items-center gap-1">
                <MapPin class="w-3 h-3" />
                <span>Pin: {{ selectedCoords.lat }}, {{ selectedCoords.lng }}</span>
              </p>
            </div>
          </div>
        </div>
      </div>

      <!-- Footer -->
      <div class="p-5 border-t border-[#E9E5F5] bg-[#FAF8FF] space-y-3">
        <div class="flex items-center justify-between text-sm">
          <span class="text-[#475569]">Order Subtotal ({{ cartStore.itemCount }} items)</span>
          <span class="text-base font-bold text-[#0F172A]">
            {{ formatCurrencyInr(cartStore.subtotalInr) }}
          </span>
        </div>

        <button
          v-if="!authStore.isAuthenticated"
          type="button"
          :disabled="cartStore.items.length === 0"
          @click="promptSignIn"
          class="w-full py-2.5 px-4 rounded-lg bg-[#5B21B6] hover:bg-[#4C1D95] disabled:bg-slate-300 disabled:cursor-not-allowed text-white text-sm font-semibold transition-colors inline-flex items-center justify-center gap-2"
        >
          <LogIn class="w-4 h-4" />
          <span>Sign In to Place Order</span>
        </button>

        <button
          v-else
          type="button"
          :disabled="cartStore.items.length === 0 || cartStore.isSubmitting"
          @click="handleCheckout"
          class="w-full py-2.5 px-4 rounded-lg bg-[#5B21B6] hover:bg-[#4C1D95] disabled:bg-slate-300 disabled:cursor-not-allowed text-white text-sm font-semibold transition-colors"
        >
          {{ cartStore.isSubmitting ? 'Reserving Inventory...' : 'Place Order' }}
        </button>
      </div>
    </aside>
  </div>
</template>
