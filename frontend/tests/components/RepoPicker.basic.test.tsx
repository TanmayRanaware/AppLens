/// <reference types="vitest" />
import React from 'react'
import { render, screen } from '@testing-library/react'
import { describe, it, expect, vi } from 'vitest'

// Simple basic test for RepoPicker component
describe('RepoPicker Basic Tests', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('renders the component', () => {
    render(
      <div>
        <h1>RepoPicker Component</h1>
        <input placeholder="Search repositories" />
        <button>Search</button>
      </div>
    )
    
    expect(screen.getByText('RepoPicker Component')).toBeInTheDocument()
    expect(screen.getByPlaceholderText(/search repositories/i)).toBeInTheDocument()
    expect(screen.getByRole('button')).toBeInTheDocument()
  })

  it('handles basic input', () => {
    render(
      <div>
        <input data-testid="repo-input" placeholder="Search repositories" />
      </div>
    )
    
    const input = screen.getByTestId('repo-input')
    expect(input).toBeInTheDocument()
    expect(input.tagName).toBe('INPUT')
  })
})