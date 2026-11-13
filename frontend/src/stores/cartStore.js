import { defineStore } from 'pinia'
import { computed, ref } from 'vue'
import { api } from '../api/client'

export const useCartStore = defineStore('cart', () => {
  const items = ref([])
  const isOpen = ref(false)
  const isSubmitting = ref(false)
  const checkoutError = ref('')

  const itemCount = computed(() =>
    items.value.reduce((sum, item) => sum + item.quantity, 0)
  )

  const subtotalInr = computed(() =>
    items.value.reduce((sum, item) => sum + item.price_inr * item.quantity, 0)
  )

  function openDrawer() {
    checkoutError.value = ''
    isOpen.value = true
  }

  function closeDrawer() {
    isOpen.value = false
  }

  function addItem(inventoryItem) {
    checkoutError.value = ''
    if (inventoryItem.stock_available <= 0) return

    const existing = items.value.find((i) => i.product_id === inventoryItem.product_id)
    if (existing) {
      if (existing.quantity < inventoryItem.stock_available) {
        existing.quantity += 1
      }
      existing.max_stock = inventoryItem.stock_available
    } else {
      items.value.push({
        product_id: inventoryItem.product_id,
        sku: inventoryItem.sku,
        name: inventoryItem.name,
        category: inventoryItem.category,
        aisle_code: inventoryItem.aisle_code,
        price_inr: inventoryItem.price_inr,
        quantity: 1,
        max_stock: inventoryItem.stock_available,
      })
    }
  }

  function updateQuantity(productId, delta) {
    checkoutError.value = ''
    const idx = items.value.findIndex((i) => i.product_id === productId)
    if (idx === -1) return

    const nextQty = items.value[idx].quantity + delta
    if (nextQty <= 0) {
      items.value.splice(idx, 1)
    } else if (nextQty <= items.value[idx].max_stock) {
      items.value[idx].quantity = nextQty
    }
  }

  function removeItem(productId) {
    items.value = items.value.filter((i) => i.product_id !== productId)
  }

  function clearCart() {
    items.value = []
    checkoutError.value = ''
  }

  async function submitCheckout({ storeId, customerName, deliveryLat, deliveryLng }) {
    if (items.value.length === 0) {
      checkoutError.value = 'Your cart is empty.'
      return null
    }
    if (!customerName || !customerName.trim()) {
      checkoutError.value = 'Please enter a customer name.'
      return null
    }

    isSubmitting.value = true
    checkoutError.value = ''
    try {
      const order = await api.createOrder({
        store_id: storeId,
        customer_name: customerName.trim(),
        delivery_lat: deliveryLat,
        delivery_lng: deliveryLng,
        items: items.value.map((i) => ({
          product_id: i.product_id,
          quantity: i.quantity,
        })),
      })
      clearCart()
      closeDrawer()
      return order
    } catch (err) {
      if (err.status === 409) {
        checkoutError.value = `Stock conflict: ${err.message}`
      } else {
        checkoutError.value = err.message || 'Checkout failed. Please try again.'
      }
      return null
    } finally {
      isSubmitting.value = false
    }
  }

  return {
    items,
    isOpen,
    isSubmitting,
    checkoutError,
    itemCount,
    subtotalInr,
    openDrawer,
    closeDrawer,
    addItem,
    updateQuantity,
    removeItem,
    clearCart,
    submitCheckout,
  }
})
