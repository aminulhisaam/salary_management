import { cleanup, render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, expect, test, vi } from 'vitest'
import { MemoryRouter } from 'react-router-dom'

import { InsightsPage } from './InsightsPage'

function response(status, body) {
  return {
    ok: status >= 200 && status < 300,
    status,
    json: async () => body,
  }
}

const headcount = {
  by_department: [{ group: 'Engineering', count: 12 }, { group: 'Sales', count: 7 }],
  by_country: [{ group: 'United States', count: 15 }, { group: 'India', count: 4 }],
}

const salarySummary = {
  by_department: [
    { group: 'Engineering', currency: 'INR', average: '1000.00', median: '1000.00' },
    { group: 'Engineering', currency: 'USD', average: '200.00', median: '200.00' },
    { group: 'Sales', currency: 'USD', average: '150.00', median: '150.00' },
  ],
  by_country: [{ group: 'United States', currency: 'USD', average: '180.00', median: '180.00' }],
}

const bands = { bands: [{ band: 'L2', count: 4 }, { band: 'L3', count: 10 }] }

const salaryRange = {
  by_department: [
    { group: 'Engineering', currency: 'INR', minimum: '1000.00', maximum: '1000.00' },
    { group: 'Engineering', currency: 'USD', minimum: '100.00', maximum: '300.00' },
  ],
  by_country: [{ group: 'United States', currency: 'USD', minimum: '100.00', maximum: '300.00' }],
}

function mockAnalytics({ headcountResponse = response(200, headcount) } = {}) {
  vi.stubGlobal(
    'fetch',
    vi
      .fn()
      .mockResolvedValueOnce(headcountResponse)
      .mockResolvedValueOnce(response(200, salarySummary))
      .mockResolvedValueOnce(response(200, bands))
      .mockResolvedValueOnce(response(200, salaryRange)),
  )
}

function renderPage() {
  return render(<MemoryRouter><InsightsPage /></MemoryRouter>)
}

afterEach(() => {
  cleanup()
  vi.unstubAllGlobals()
})

test('renders all aggregate chart sections from their API responses', async () => {
  mockAnalytics()
  renderPage()

  expect(await screen.findByText('Engineering has the highest headcount at 12, followed by Sales at 7.')).toBeInTheDocument()
  expect(screen.getByLabelText('Headcount by department')).toBeInTheDocument()
  expect(screen.getByLabelText('Employee count by band')).toBeInTheDocument()
  expect(screen.getByText('Minimum and maximum current salaries remain separated by currency.')).toBeInTheDocument()
})

test('shows salary summary figures in separate currency panels', async () => {
  mockAnalytics()
  renderPage()

  expect(await screen.findByText('INR department salary summary')).toBeInTheDocument()
  expect(screen.getByText('USD department salary summary')).toBeInTheDocument()
  expect(screen.getByText(/Engineering: ₹1,000.00 average, ₹1,000.00 median/)).toBeInTheDocument()
  expect(screen.getByText(/Engineering: \$200.00 average, \$200.00 median/)).toBeInTheDocument()
})

test('band distribution filters request a new aggregate with the selected filters', async () => {
  mockAnalytics()
  fetch.mockResolvedValueOnce(response(200, { bands: [{ band: 'L3', count: 5 }] }))
  const user = userEvent.setup()
  renderPage()
  await screen.findByLabelText('Employee count by band')

  await user.selectOptions(screen.getByRole('combobox', { name: 'Department' }), 'Engineering')

  await waitFor(() => expect(fetch).toHaveBeenCalledTimes(5))
  const query = new URL(fetch.mock.calls[4][0]).searchParams
  expect(query.get('department')).toBe('Engineering')
  expect(query.get('country')).toBeNull()
})

test('an analytics failure leaves other sections usable', async () => {
  mockAnalytics({ headcountResponse: response(500, { detail: 'Analytics unavailable' }) })
  renderPage()

  expect(await screen.findByText('Unable to load this insight.')).toBeInTheDocument()
  expect(await screen.findByText('USD department salary summary')).toBeInTheDocument()
  expect(screen.getByLabelText('Employee count by band')).toBeInTheDocument()
})
