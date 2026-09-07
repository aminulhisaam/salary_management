import { cleanup, render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, expect, test, vi } from 'vitest'
import { MemoryRouter } from 'react-router-dom'

import { EmployeeListPage } from './EmployeeListPage'

function response(body) {
  return {
    ok: true,
    status: 200,
    json: async () => body,
  }
}

function errorResponse(status, body) {
  return {
    ok: false,
    status,
    json: async () => body,
  }
}

function employee(overrides = {}) {
  return {
    id: 1,
    employee_code: 'EMP-00001',
    first_name: 'Ada',
    last_name: 'Lovelace',
    department: 'Engineering',
    country: 'United States',
    band: 'L3',
    current_salary_amount: '85000.50',
    current_salary_currency: 'USD',
    status: 'active',
    ...overrides,
  }
}

function renderPage(initialEntry = '/employees') {
  return render(
    <MemoryRouter initialEntries={[initialEntry]}>
      <EmployeeListPage />
    </MemoryRouter>,
  )
}

function queryFromCall(callIndex) {
  return new URL(fetch.mock.calls[callIndex][0]).searchParams
}

afterEach(() => {
  cleanup()
  vi.unstubAllGlobals()
})

test('renders the employee table with formatted salaries', async () => {
  vi.stubGlobal('fetch', vi.fn().mockResolvedValue(response({
    items: [employee()], total: 1, limit: 25, offset: 0,
  })))
  renderPage()

  expect(await screen.findByText('EMP-00001')).toBeInTheDocument()
  expect(screen.getByText('Ada Lovelace')).toBeInTheDocument()
  expect(screen.getByText('$85,000.50')).toBeInTheDocument()
  expect(screen.getByText('1 employees')).toBeInTheDocument()
})

test('changing a filter requests the first page with that filter', async () => {
  vi.stubGlobal('fetch', vi.fn().mockResolvedValue(response({
    items: [employee()], total: 1, limit: 25, offset: 0,
  })))
  const user = userEvent.setup()
  renderPage()
  await screen.findByText('EMP-00001')

  await user.selectOptions(screen.getByRole('combobox', { name: 'Department' }), 'Engineering')

  await waitFor(() => expect(fetch).toHaveBeenCalledTimes(2))
  const query = queryFromCall(1)
  expect(query.get('department')).toBe('Engineering')
  expect(query.get('offset')).toBe('0')
})

test('search waits for the debounce before requesting filtered results', async () => {
  vi.stubGlobal('fetch', vi.fn().mockResolvedValue(response({
    items: [employee()], total: 1, limit: 25, offset: 0,
  })))
  const user = userEvent.setup()
  renderPage()
  await screen.findByText('EMP-00001')

  await user.type(screen.getByLabelText('Search name or email'), 'ada')
  await new Promise((resolve) => window.setTimeout(resolve, 299))
  expect(fetch).toHaveBeenCalledTimes(1)

  await waitFor(() => expect(fetch).toHaveBeenCalledTimes(2))
  expect(queryFromCall(1).get('search')).toBe('ada')
})

test('pagination requests the next server-side page', async () => {
  vi.stubGlobal('fetch', vi.fn().mockResolvedValue(response({
    items: [employee()], total: 30, limit: 25, offset: 0,
  })))
  const user = userEvent.setup()
  renderPage()
  await screen.findByText('EMP-00001')

  await user.click(screen.getByRole('button', { name: 'Next' }))

  await waitFor(() => expect(fetch).toHaveBeenCalledTimes(2))
  expect(queryFromCall(1).get('offset')).toBe('25')
  expect(queryFromCall(1).get('limit')).toBe('25')
  expect(screen.getByText('Page 2 of 2')).toBeInTheDocument()
})

test('renders the empty state when no employees match', async () => {
  vi.stubGlobal('fetch', vi.fn().mockResolvedValue(response({
    items: [], total: 0, limit: 25, offset: 0,
  })))
  renderPage()

  expect(await screen.findByText('No employees match these filters.')).toBeInTheDocument()
})

test('shows a successful CSV import summary', async () => {
  vi.stubGlobal(
    'fetch',
    vi
      .fn()
      .mockResolvedValueOnce(response({ items: [], total: 0, limit: 25, offset: 0 }))
      .mockResolvedValueOnce({ ok: true, status: 201, json: async () => ({ rows_imported: 2, rows_rejected: [] }) })
      .mockResolvedValueOnce(response({ items: [], total: 2, limit: 25, offset: 0 })),
  )
  const user = userEvent.setup()
  renderPage()
  await screen.findByRole('button', { name: 'Import CSV' })

  await user.click(screen.getByRole('button', { name: 'Import CSV' }))
  await user.upload(screen.getByLabelText('CSV file'), new File(['employee_code\n'], 'employees.csv', { type: 'text/csv' }))
  await user.click(screen.getByRole('button', { name: 'Upload CSV' }))

  expect(await screen.findByText('2 employees imported successfully.')).toBeInTheDocument()
  expect(fetch.mock.calls[1][0]).toBe('http://localhost:8000/employees/import')
  expect(fetch.mock.calls[1][1].body).toBeInstanceOf(FormData)
})

test('shows CSV row errors returned by the backend', async () => {
  vi.stubGlobal(
    'fetch',
    vi
      .fn()
      .mockResolvedValueOnce(response({ items: [], total: 0, limit: 25, offset: 0 }))
      .mockResolvedValueOnce(errorResponse(422, {
        rows_processed: 1,
        rows_imported: 0,
        rows_rejected: [{ row: 2, message: "department 'Enginering' is not in the canonical list" }],
        error: null,
      })),
  )
  const user = userEvent.setup()
  renderPage()
  await screen.findByRole('button', { name: 'Import CSV' })

  await user.click(screen.getByRole('button', { name: 'Import CSV' }))
  await user.upload(screen.getByLabelText('CSV file'), new File(['employee_code\n'], 'invalid.csv', { type: 'text/csv' }))
  await user.click(screen.getByRole('button', { name: 'Upload CSV' }))

  expect(await screen.findByText("Row 2: department 'Enginering' is not in the canonical list")).toBeInTheDocument()
})

test('links to the CSV template download', async () => {
  vi.stubGlobal('fetch', vi.fn().mockResolvedValue(response({
    items: [], total: 0, limit: 25, offset: 0,
  })))
  const user = userEvent.setup()
  renderPage()
  await user.click(await screen.findByRole('button', { name: 'Import CSV' }))

  expect(screen.getByRole('link', { name: 'Download template' })).toHaveAttribute(
    'href',
    '/employee-import-template.csv',
  )
})
