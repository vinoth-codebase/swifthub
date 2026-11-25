const TOKEN_STORAGE_KEY = 'swifthub_auth_token'

export function getStoredToken() {
  try {
    return localStorage.getItem(TOKEN_STORAGE_KEY) || ''
  } catch {
    return ''
  }
}

export function setStoredToken(token) {
  try {
    if (token) {
      localStorage.setItem(TOKEN_STORAGE_KEY, token)
    } else {
      localStorage.removeItem(TOKEN_STORAGE_KEY)
    }
  } catch {
    // ignore storage errors in non-browser test environments
  }
}

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
  const token = getStoredToken()
  const headers = {
    'Content-Type': 'application/json',
    ...(options.headers || {}),
  }
  if (token && !headers.Authorization) {
    headers.Authorization = `Bearer ${token}`
  }

  const response = await fetch(url, {
    ...options,
    headers,
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
  // Auth
  register: (payload) =>
    request('/api/auth/register', {
      method: 'POST',
      body: JSON.stringify(payload),
    }),
  login: (payload) =>
    request('/api/auth/login', {
      method: 'POST',
      body: JSON.stringify(payload),
    }),
  fetchMe: () => request('/api/auth/me'),

  // Public storefront & inventory
  fetchStores: () => request('/api/stores'),
  fetchInventory: (storeId, params = {}) => {
    const query = new URLSearchParams()
    if (params.category && params.category !== 'All') query.set('category', params.category)
    if (params.q) query.set('q', params.q)
    if (params.lowStockOnly) query.set('low_stock_only', 'true')
    const suffix = query.toString() ? `?${query.toString()}` : ''
    return request(`/api/stores/${storeId}/inventory${suffix}`)
  },

  // Orders (role-scoped)
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
  cancelOrder: (orderId) =>
    request(`/api/orders/${orderId}/cancel`, {
      method: 'POST',
    }),

  // Branch Admin endpoints
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
