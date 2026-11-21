import { describe, expect, it } from 'vitest'
import {
  formatCountdown,
  formatCurrencyInr,
  formatDuration,
  getRemainingSlaSeconds,
  getSlaRiskMeta,
  getStepIndex,
} from '../utils/sla'

describe('SLA utility helpers', () => {
  it('formats positive and overdue countdowns accurately', () => {
    expect(formatCountdown(600)).toBe('10:00')
    expect(formatCountdown(95)).toBe('01:35')
    expect(formatCountdown(0)).toBe('00:00')
    expect(formatCountdown(-45)).toBe('-00:45')
  })

  it('computes remaining SLA seconds from order timestamp', () => {
    const now = Date.parse('2026-11-20T12:05:00Z')
    const created = '2026-11-20T12:00:00Z'
    expect(getRemainingSlaSeconds(created, now)).toBe(300)
  })

  it('classifies SLA breach risk thresholds properly', () => {
    expect(getSlaRiskMeta(0.15).level).toBe('LOW')
    expect(getSlaRiskMeta(0.45).level).toBe('MEDIUM')
    expect(getSlaRiskMeta(0.78).level).toBe('HIGH')
    expect(getSlaRiskMeta(0.78).pct).toBe(78)
  })

  it('formats durations, INR currency, and order steps', () => {
    expect(formatDuration(45)).toBe('45s')
    expect(formatDuration(425)).toBe('7m 05s')
    expect(formatCurrencyInr(195)).toBe('INR 195')
    expect(getStepIndex('PACKED')).toBe(2)
  })
})
