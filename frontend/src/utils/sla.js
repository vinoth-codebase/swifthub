export const SLA_TARGET_SECONDS = 600

export const ORDER_STEPS = [
  { key: 'PLACED', label: 'Order Placed' },
  { key: 'PICKING', label: 'Picking Items' },
  { key: 'PACKED', label: 'Packed at Hub' },
  { key: 'OUT_FOR_DELIVERY', label: 'Out for Delivery' },
  { key: 'DELIVERED', label: 'Delivered' },
]

export function getStepIndex(status) {
  const idx = ORDER_STEPS.findIndex((s) => s.key === status)
  return idx === -1 ? 0 : idx
}

export function getRemainingSlaSeconds(createdAt, nowMs = Date.now()) {
  if (!createdAt) return SLA_TARGET_SECONDS
  const createdMs = new Date(createdAt).getTime()
  if (Number.isNaN(createdMs)) return SLA_TARGET_SECONDS
  const elapsedSec = Math.floor((nowMs - createdMs) / 1000)
  return SLA_TARGET_SECONDS - elapsedSec
}

export function formatCountdown(totalSeconds) {
  const isOverdue = totalSeconds < 0
  const absSec = Math.abs(Math.round(totalSeconds))
  const mins = Math.floor(absSec / 60)
  const secs = absSec % 60
  const padded = `${String(mins).padStart(2, '0')}:${String(secs).padStart(2, '0')}`
  return isOverdue ? `-${padded}` : padded
}

export function formatDuration(seconds) {
  const safe = Math.max(0, Math.round(Number(seconds) || 0))
  const mins = Math.floor(safe / 60)
  const secs = safe % 60
  if (mins === 0) return `${secs}s`
  return `${mins}m ${String(secs).padStart(2, '0')}s`
}

export function getSlaRiskMeta(score) {
  const val = Number(score) || 0
  if (val >= 0.65) {
    return {
      level: 'HIGH',
      label: 'High SLA Risk',
      pct: Math.round(val * 100),
      badgeClass: 'bg-rose-50 text-rose-700 border-rose-200',
      dotClass: 'bg-rose-600',
    }
  }
  if (val >= 0.35) {
    return {
      level: 'MEDIUM',
      label: 'Watch SLA',
      pct: Math.round(val * 100),
      badgeClass: 'bg-amber-50 text-amber-800 border-amber-200',
      dotClass: 'bg-amber-500',
    }
  }
  return {
    level: 'LOW',
    label: 'On-Time SLA',
    pct: Math.round(val * 100),
    badgeClass: 'bg-emerald-50 text-emerald-700 border-emerald-200',
    dotClass: 'bg-emerald-600',
  }
}

export function formatCurrencyInr(amount) {
  const num = Number(amount) || 0
  return `INR ${num.toFixed(0)}`
}
