import { defineStore } from 'pinia'
import { computed, ref } from 'vue'
import { api } from '../api/client'
import { useAuthStore } from './authStore'

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

  function getStoreById(storeId) {
    return stores.value.find((s) => s.id === storeId) || null
  }

  async function initialize() {
    const authStore = useAuthStore()
    loading.value = true
    error.value = ''
    try {
      const storeList = await api.fetchStores()
      stores.value = storeList

      if (authStore.isBranchAdmin && authStore.user?.store_id) {
        selectedStoreId.value = authStore.user.store_id
      } else if (
        !selectedStoreId.value ||
        !storeList.some((s) => s.id === selectedStoreId.value)
      ) {
        selectedStoreId.value = storeList.length > 0 ? storeList[0].id : null
      }

      await refreshForRole()
    } catch (err) {
      error.value = err.message || 'Failed to load SwiftHub data'
    } finally {
      loading.value = false
    }
  }

  async function selectStore(storeId) {
    const authStore = useAuthStore()
    if (authStore.isBranchAdmin) {
      // Branch Admins are strictly locked to their assigned hub
      selectedStoreId.value = authStore.user.store_id
      return
    }
    selectedStoreId.value = Number(storeId)
    await refreshInventory()
  }

  async function refreshForRole() {
    const authStore = useAuthStore()
    if (authStore.isBranchAdmin && authStore.user?.store_id) {
      selectedStoreId.value = authStore.user.store_id
      await Promise.all([
        refreshInventory(),
        refreshOrders(),
        refreshRiders(),
        refreshAnalytics(),
      ])
    } else if (authStore.isCustomer) {
      riders.value = []
      analytics.value = null
      await Promise.all([refreshInventory(), refreshOrders()])
    } else {
      orders.value = []
      riders.value = []
      analytics.value = null
      trackedOrderId.value = null
      await refreshInventory()
    }
  }

  async function refreshInventory() {
    if (!selectedStoreId.value) return
    inventory.value = await api.fetchInventory(selectedStoreId.value)
  }

  async function refreshOrders() {
    const authStore = useAuthStore()
    if (!authStore.isAuthenticated) {
      orders.value = []
      return
    }
    if (authStore.isBranchAdmin) {
      orders.value = await api.fetchOrders(authStore.user.store_id)
    } else {
      // Customers see all of their own orders across branches
      orders.value = await api.fetchOrders()
    }
  }

  async function refreshRiders() {
    const authStore = useAuthStore()
    if (!authStore.isBranchAdmin || !authStore.user?.store_id) {
      riders.value = []
      return
    }
    riders.value = await api.fetchRiders(authStore.user.store_id)
  }

  async function refreshAnalytics() {
    const authStore = useAuthStore()
    if (!authStore.isBranchAdmin || !authStore.user?.store_id) {
      analytics.value = null
      return
    }
    analytics.value = await api.fetchAnalytics(authStore.user.store_id)
  }

  function upsertOrder(order) {
    const authStore = useAuthStore()
    if (!authStore.isAuthenticated) return
    if (authStore.isBranchAdmin && order.store_id !== authStore.user.store_id) return
    if (authStore.isCustomer && order.customer_id !== authStore.user.id) return

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

  async function cancelMyOrder(orderId) {
    const updated = await api.cancelOrder(orderId)
    upsertOrder(updated)
    await refreshInventory()
    return updated
  }

  async function restockSku(productId, quantity = 10) {
    const authStore = useAuthStore()
    if (!authStore.isBranchAdmin || !authStore.user?.store_id) return null
    const updated = await api.restockItem(authStore.user.store_id, productId, quantity)
    const idx = inventory.value.findIndex((i) => i.product_id === productId)
    if (idx !== -1) {
      inventory.value[idx] = updated
    }
    return updated
  }

  async function runDemoSimulation() {
    const authStore = useAuthStore()
    if (!authStore.isBranchAdmin || !authStore.user?.store_id) return null
    simulationRunning.value = true
    try {
      const order = await api.triggerSimulation(authStore.user.store_id)
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
    const authStore = useAuthStore()
    const { type, payload } = event

    if (type === 'ORDER_CREATED' || type === 'ORDER_UPDATED') {
      if (!authStore.isAuthenticated) return
      if (authStore.isBranchAdmin && payload.store_id === authStore.user.store_id) {
        upsertOrder(payload)
        refreshAnalytics()
      } else if (authStore.isCustomer && payload.customer_id === authStore.user.id) {
        upsertOrder(payload)
      }
    } else if (type === 'INVENTORY_UPDATED') {
      if (!payload?.store_id || payload.store_id === selectedStoreId.value) {
        refreshInventory()
      }
    } else if (type === 'RIDERS_UPDATED') {
      if (
        authStore.isBranchAdmin &&
        payload?.store_id === authStore.user.store_id &&
        Array.isArray(payload.riders)
      ) {
        riders.value = payload.riders
      }
    } else if (type === 'RIDER_LOCATION') {
      if (
        authStore.isBranchAdmin &&
        payload?.store_id === authStore.user.store_id &&
        payload.rider
      ) {
        const idx = riders.value.findIndex((r) => r.id === payload.rider.id)
        if (idx !== -1) {
          riders.value[idx] = payload.rider
        }
      }
      if (payload?.order_id && payload.rider) {
        const ordIdx = orders.value.findIndex((o) => o.id === payload.order_id)
        if (ordIdx !== -1) {
          orders.value[ordIdx] = {
            ...orders.value[ordIdx],
            rider_lat: payload.rider.current_lat,
            rider_lng: payload.rider.current_lng,
            rider_status: payload.rider.status,
          }
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
    getStoreById,
    initialize,
    selectStore,
    refreshForRole,
    refreshInventory,
    refreshOrders,
    refreshRiders,
    refreshAnalytics,
    upsertOrder,
    advanceOrderStatus,
    cancelMyOrder,
    restockSku,
    runDemoSimulation,
    handleWsEvent,
  }
})
