export function getApiBaseUrl() {
  const configured = import.meta.env.VITE_API_URL
  if (configured && configured.trim()) {
    return configured.trim().replace(/\/+$/, '')
  }
  return 'http://localhost:8000'
}

export function getWsUrl() {
  const base = getApiBaseUrl()
  if (base.startsWith('https://')) {
    return `${base.replace('https://', 'wss://')}/ws`
  }
  return `${base.replace('http://', 'ws://')}/ws`
}

async function request(path, options = {}) {
  const url = `${getApiBaseUrl()}${path}`
  const response = await fetch(url, {
    headers: {
      'Content-Type': 'application/json',
      ...(options.headers || {}),
    },
    ...options,
  })

  if (!response.ok) {
    let detail = `Request failed with status ${response.status}`
    try {
      const data = await response.json()
      if (data?.detail) {
        detail = typeof data.detail === 'string' ? data.detail : JSON.stringify(data.detail)
      }
    } catch {
      // ignore JSON parse failure
    }
    const err = new Error(detail)
    err.status = response.status
    throw err
  }

  return response.json()
}

export const api = {
  fetchStores: () => request('/api/stores'),
  fetchInventory: (storeId, params = {}) => {
    const query = new URLSearchParams()
    if (params.category && params.category !== 'All') query.set('category', params.category)
    if (params.q) query.set('q', params.q)
    if (params.lowStockOnly) query.set('low_stock_only', 'true')
    const suffix = query.toString() ? `?${query.toString()}` : ''
    return request(`/api/stores/${storeId}/inventory${suffix}`)
  },
  fetchOrders: (storeId = null) => {
    const suffix = storeId ? `?store_id=${storeId}` : ''
    return request(`/api/orders${suffix}`)
  },
  fetchOrder: (orderId) => request(`/api/orders/${orderId}`),
  createOrder: (payload) =>
    request('/api/orders', {
      method: 'POST',
      body: JSON.stringify(payload),
    }),
  updateOrderStatus: (orderId, status, note = null) =>
    request(`/api/orders/${orderId}/status`, {
      method: 'PATCH',
      body: JSON.stringify({ status, note }),
    }),
  restockItem: (storeId, productId, quantity = 10) =>
    request(`/api/stores/${storeId}/inventory/${productId}/restock`, {
      method: 'POST',
      body: JSON.stringify({ quantity }),
    }),
  fetchRiders: (storeId = null) => {
    const suffix = storeId ? `?store_id=${storeId}` : ''
    return request(`/api/riders${suffix}`)
  },
  fetchAnalytics: (storeId = null) => {
    const suffix = storeId ? `?store_id=${storeId}` : ''
    return request(`/api/analytics${suffix}`)
  },
  triggerSimulation: (storeId = null) =>
    request('/api/simulation/trigger', {
      method: 'POST',
      body: JSON.stringify({ store_id: storeId }),
    }),
}
