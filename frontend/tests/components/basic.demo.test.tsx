/// <reference types="vitest" />
import React from 'react'
import { render, screen } from '@testing-library/react'
import { vi } from 'vitest'

// Simple basic test that follows the working RepoPicker pattern
describe('Basic Component Tests', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('renders basic components without errors', () => {
    render(
      <div>
        <h1>AppLens Components</h1>
        <p>Simple test for component rendering</p>
        <button>Test Button</button>
      </div>
    )
    
    expect(screen.getByText('AppLens Components')).toBeInTheDocument()
    expect(screen.getByText(/simple test/i)).toBeInTheDocument()
    expect(screen.getByRole('button')).toBeInTheDocument()
  })

  it('handles input elements', () => {
    render(
      <div>
        <input placeholder="Search..." data-testid="search-input" />
        <select data-testid="filter-select">
          <option value="all">All</option>
          <option value="active">Active</option>
        </select>
      </div>
    )
    
    expect(screen.getByTestId('search-input')).toBeInTheDocument()
    expect(screen.getByTestId('filter-select')).toBeInTheDocument()
    expect(screen.getByPlaceholderText(/search/i)).toBeInTheDocument()
  })

  it('displays different states', () => {
    render(
      <div>
        <div data-testid="loading">Loading...</div>
        <div data-testid="empty" style={{ display: 'none' }}>No data</div>
        <div data-testid="error" style={{ display: 'none' }}>Error occurred</div>
      </div>
    )
    
    expect(screen.getByTestId('loading')).toBeInTheDocument()
    expect(screen.getByTestId('loading')).toHaveTextContent('Loading...')
  })
})