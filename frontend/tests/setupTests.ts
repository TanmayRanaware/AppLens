/// <reference types="vitest" />
import '@testing-library/jest-dom'
import React from 'react'

// Add a simple global setup for testing
global.performance = {
  now: () => 1000,
} as any

// Ensure React is available in the global scope for testing
global.React = React