import { describe, it, expect, vi, beforeEach } from 'vitest'
import { PerfLogger } from '@/lib/perf'

describe('PerfLogger', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    global.performance = {
      now: vi.fn(() => 1000),
    } as any
  })

  it('should create a performance logger instance', () => {
    const logger = new PerfLogger('test-operation')
    expect(logger).toBeDefined()
    expect(logger.operationName).toBe('test-operation')
  })

  it('should start and end timing correctly', () => {
    const logger = new PerfLogger('test-operation')
    
    // Mock performance.now to return different values
    vi.mocked(global.performance.now)
      .mockReturnValueOnce(1000)  // start time
      .mockReturnValueOnce(1500)  // end time

    logger.start()
    const duration = logger.end()

    expect(duration).toBe(500) // 1500 - 1000 = 500ms
  })

  it('should handle timing without explicit start', () => {
    const logger = new PerfLogger('test-operation')
    
    vi.mocked(global.performance.now)
      .mockReturnValueOnce(1000)
      .mockReturnValueOnce(1200)

    const duration = logger.end()

    expect(duration).toBe(200)
  })
})

describe('Performance utilities', () => {
  it('should measure function execution time', () => {
    const testFunction = vi.fn(() => 'result')
    const measureFunction = (fn: () => string) => {
      const start = performance.now()
      const result = fn()
      const end = performance.now()
      return { result, duration: end - start }
    }

    vi.mocked(global.performance.now)
      .mockReturnValueOnce(1000)
      .mockReturnValueOnce(1100)

    const { result, duration } = measureFunction(testFunction)

    expect(result).toBe('result')
    expect(duration).toBe(100)
    expect(testFunction).toHaveBeenCalledTimes(1)
  })
})