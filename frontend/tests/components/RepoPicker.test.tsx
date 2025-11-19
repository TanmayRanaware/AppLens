/// <reference types="vitest" />
import React from 'react'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { vi } from 'vitest'

// Mock the API module used by RepoPicker
vi.mock('@/lib/api', () => ({
  api: {
    get: vi.fn()
  }
}))

import RepoPicker from '@/components/RepoPicker'
import { api } from '@/lib/api'

describe('RepoPicker', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('searches and displays results, selecting a repo calls onSelect', async () => {
    const repos = ['owner/repo-one', 'owner/repo-two']
    ;(api.get as any).mockResolvedValue({ data: { repos } })

    const onSelect = vi.fn()
    render(<RepoPicker onSelect={onSelect} />)

    const input = screen.getByPlaceholderText(/Search repositories/i)
    await userEvent.type(input, 'repo')

    const searchBtn = screen.getByRole('button')
    await userEvent.click(searchBtn)

    await waitFor(() => expect(api.get).toHaveBeenCalled())

    // Results should be rendered
    expect(screen.getByText('owner/repo-one')).toBeInTheDocument()
    expect(screen.getByText('owner/repo-two')).toBeInTheDocument()

    // Click the first repo
    await userEvent.click(screen.getByText('owner/repo-one'))

    expect(onSelect).toHaveBeenCalledWith('owner/repo-one')
  })
})
