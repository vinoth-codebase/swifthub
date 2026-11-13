import { defineStore } from 'pinia'
import { computed, ref } from 'vue'
import { api } from '../api/client'

export const useHubStore = defineStore('hub', () => {
  const stores = ref([])
  const selectedStoreId = ref(null)
  const inventory = ref([])
  const orders = ref([])
  const riders = ref([])
  const analytics = ref(null)
  const trackedOrderId = ref(null)
  const loading = ref(false)
  const error = ref('')
  const simulationRunning = ref(false)

  const currentStore = computed(() =>
    stores.value.find((s) => s.id === selectedStoreId.value) || stores.value[0] || null
  )

  const trackedOrder = computed(() => {
    if (!trackedOrderId.value) return null
    return orders.value.find((o) => o.id === trackedOrderId.value) || null
  })

  const lowStockItems = computed(() =>
    inventory.value.filter((item) => item.stock_available <= item.reorder_threshold)
  )

  async function initialize() {
    loading.value = true
    error.value = ''
    try {
      const storeList = await api.fetchStores()
      stores.value = storeList
      if (!selectedStoreId.value && storeList.length > 0) {
        selectedStoreId.value = storeList[0].id
      }
      await refreshAll()
    } catch (err) {
      error.value = err.message || 'Failed to load SwiftHub data'
    } finally {
      loading.value = false
    }
  }

  async function selectStore(storeId) {
    selectedStoreId.value = Number(storeId)
    await refreshAll()
  }

  async function refreshAll() {
    if (!selectedStoreId.value) return
    await Promise.all([
      refreshInventory(),
      refreshOrders(),
      refreshRiders(),
      refreshAnalytics(),
    ])
  }

  async function refreshInventory() {
    if (!selectedStoreId.value) return
    inventory.value = await api.fetchInventory(selectedStoreId.value)
  }

  async function refreshOrders() {
    if (!selectedStoreId.value) return
    orders.value = await api.fetchOrders(selectedStoreId.value)
  }

  async function refreshRiders() {
    if (!selectedStoreId.value) return
    riders.value = await api.fetchRiders(selectedStoreId.value)
  }

  async function refreshAnalytics() {
    if (!selectedStoreId.value) return
    analytics.value = await api.fetchAnalytics(selectedStoreId.value)
  }

  function upsertOrder(order) {
    if (selectedStoreId.value && order.store_id !== selectedStoreId.value) return
    const idx = orders.value.findIndex((o) => o.id === order.id)
    if (idx === -1) {
      orders.value.unshift(order)
    } else {
      orders.value[idx] = order
    }
  }

  async function advanceOrderStatus(orderId, targetStatus, note = null) {
    const updated = await api.updateOrderStatus(orderId, targetStatus, note)
    upsertOrder(updated)
    await Promise.all([refreshRiders(), refreshAnalytics()])
    if (targetStatus === 'CANCELLED') {
      await refreshInventory()
    }
    return updated
  }

  async function restockSku(productId, quantity = 10) {
    if (!selectedStoreId.value) return null
    const updated = await api.restockItem(selectedStoreId.value, productId, quantity)
    const idx = inventory.value.findIndex((i) => i.product_id === productId)
    if (idx !== -1) {
      inventory.value[idx] = updated
    }
    return updated
  }

  async function runDemoSimulation() {
    simulationRunning.value = true
    try {
      const order = await api.triggerSimulation(selectedStoreId.value)
      upsertOrder(order)
      trackedOrderId.value = order.id
      await refreshInventory()
      return order
    } finally {
      setTimeout(() => {
        simulationRunning.value = false
      }, 2500)
    }
  }

  function handleWsEvent(event) {
    if (!event || !event.type) return
    const { type, payload } = event

    if (type === 'ORDER_CREATED' || type === 'ORDER_UPDATED') {
      upsertOrder(payload)
      refreshAnalytics()
    } else if (type === 'INVENTORY_UPDATED') {
      if (!payload?.store_id || payload.store_id === selectedStoreId.value) {
        refreshInventory()
      }
    } else if (type === 'RIDERS_UPDATED') {
      if (payload?.store_id === selectedStoreId.value && Array.isArray(payload.riders)) {
        riders.value = payload.riders
      }
    } else if (type === 'RIDER_LOCATION') {
      if (payload?.store_id === selectedStoreId.value && payload.rider) {
        const idx = riders.value.findIndex((r) => r.id === payload.rider.id)
        if (idx !== -1) {
          riders.value[idx] = payload.rider
        }
      }
    }
  }

  return {
    stores,
    selectedStoreId,
    currentStore,
    inventory,
    lowStockItems,
    orders,
    riders,
    analytics,
    trackedOrderId,
    trackedOrder,
    loading,
    error,
    simulationRunning,
    initialize,
    selectStore,
    refreshAll,
    refreshInventory,
    refreshOrders,
    refreshRiders,
    refreshAnalytics,
    upsertOrder,
    advanceOrderStatus,
    restockSku,
    runDemoSimulation,
    handleWsEvent,
  }
})
