import { beforeEach, describe, expect, it } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { useCartStore } from '../stores/cartStore'

describe('useCartStore', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
  })

  const sampleItem = {
    product_id: 101,
    sku: 'DAI-001',
    name: 'Nandini GoodLife Toned Milk 500ml',
    category: 'Dairy',
    aisle_code: 'A1-Dairy',
    price_inr: 32,
    stock_available: 2,
  }

  it('adds items, calculates subtotal, and caps quantity at available stock', () => {
    const cart = useCartStore()
    cart.addItem(sampleItem)
    cart.addItem(sampleItem)
    cart.addItem(sampleItem) // exceeds stock_available of 2

    expect(cart.itemCount).toBe(2)
    expect(cart.subtotalInr).toBe(64)
  })

  it('decrements and removes items when quantity reaches zero', () => {
    const cart = useCartStore()
    cart.addItem(sampleItem)
    cart.updateQuantity(101, -1)

    expect(cart.items.length).toBe(0)
    expect(cart.itemCount).toBe(0)
    expect(cart.subtotalInr).toBe(0)
  })

  it('rejects checkout submission when customer name is blank', async () => {
    const cart = useCartStore()
    cart.addItem(sampleItem)

    const result = await cart.submitCheckout({
      storeId: 1,
      customerName: '   ',
      deliveryLat: 12.9352,
      deliveryLng: 77.6245,
    })

    expect(result).toBeNull()
    expect(cart.checkoutError).toContain('customer name')
  })
})
