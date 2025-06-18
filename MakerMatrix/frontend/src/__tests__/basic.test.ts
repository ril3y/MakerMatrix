import { describe, it, expect } from 'vitest'
import { createMockPart, createMockLocation } from './utils/test-utils'

describe('Basic Test Setup', () => {
  it('should run basic test', () => {
    expect(1 + 1).toBe(2)
  })

  it('should create mock data', () => {
    const mockPart = createMockPart()
    expect(mockPart).toHaveProperty('id')
    expect(mockPart).toHaveProperty('part_name')
    expect(mockPart.part_name).toBe('Test Resistor')
  })

  it('should create mock location', () => {
    const mockLocation = createMockLocation()
    expect(mockLocation).toHaveProperty('id')
    expect(mockLocation).toHaveProperty('name')
    expect(mockLocation.name).toBe('Test Storage')
  })

  it('should create mock with overrides', () => {
    const mockPart = createMockPart({ part_name: 'Custom Part' })
    expect(mockPart.part_name).toBe('Custom Part')
  })
})