import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, expect, test, vi } from 'vitest'
import { MemoryRouter, Route, Routes } from 'react-router-dom'

import { EmployeeDetailPage } from './EmployeeDetailPage'

function response(status, body) {
  return {
    ok: status >= 200 && status < 300,
    status,
    json: async () => body,
  }
}

function detailResponse(overrides = {}) {
  return {
    employee: {
      id: 1,
      employee_code: 'EMP-00001',
      first_name: 'Ada',
      last_name: 'Lovelace',
      email: 'ada@example.com',
      department: 'Engineering',
      country: 'United States',
      band: 'L3',
      job_title: 'Engineer',
      hire_date: '2022-01-01',
      status: 'active',
      current_salary_amount: '95000.00',
      current_salary_currency: 'USD',
      current_salary_id: 2,
    },
    salary_history: [
      {
        id: 2,
        employee_id: 1,
        amount: '95000.00',
        currency: 'USD',
        effective_date: '2024-01-01',
        reason: 'promotion',
      },
      {
        id: 1,
        employee_id: 1,
        amount: '85000.50',
        currency: 'USD',
        effective_date: '2022-01-01',
        reason: 'hire',
      },
    ],
    ...overrides,
  }
}

function renderPage(initialEntry = '/employees/1?page=2&department=Engineering') {
  return render(
    <MemoryRouter initialEntries={[initialEntry]}>
      <Routes>
        <Route path="/employees/:employeeId" element={<EmployeeDetailPage />} />
        <Route path="/employees" element={<div>Employee list</div>} />
      </Routes>
    </MemoryRouter>,
  )
}

afterEach(() => {
  cleanup()
  vi.unstubAllGlobals()
})

test('renders profile data and a newest-first salary timeline', async () => {
  vi.stubGlobal('fetch', vi.fn().mockResolvedValue(response(200, detailResponse())))
  renderPage()

  expect(await screen.findByRole('heading', { name: 'Ada Lovelace' })).toBeInTheDocument()
  expect(screen.getByText('ada@example.com')).toBeInTheDocument()
  expect(screen.getAllByText('EMP-00001')).toHaveLength(2)
  expect(screen.getAllByText('$95,000.00')).toHaveLength(2)
  expect(screen.getByText('promotion - Current salary')).toBeInTheDocument()
  const entries = screen.getAllByTestId('salary-entry')
  expect(entries[0]).toHaveTextContent('95,000.00')
  expect(entries[1]).toHaveTextContent('85,000.50')
})

test('keeps the list query string on the back link', async () => {
  vi.stubGlobal('fetch', vi.fn().mockResolvedValue(response(200, detailResponse())))
  renderPage()

  const backLink = await screen.findByRole('link', { name: 'Back to list' })
  expect(backLink).toHaveAttribute('href', '/employees?page=2&department=Engineering')
})

test('submits the profile update payload', async () => {
  vi.stubGlobal(
    'fetch',
    vi
      .fn()
      .mockResolvedValueOnce(response(200, detailResponse()))
      .mockResolvedValueOnce(response(200, { ...detailResponse().employee, job_title: 'Senior Engineer' })),
  )
  const user = userEvent.setup()
  renderPage()
  await screen.findByRole('heading', { name: 'Ada Lovelace' })

  await user.click(screen.getByRole('button', { name: 'Edit profile' }))
  await user.clear(screen.getByLabelText(/Job title/))
  await user.type(screen.getByLabelText(/Job title/), 'Senior Engineer')
  await user.click(screen.getByRole('button', { name: 'Save profile' }))

  await waitFor(() => expect(fetch).toHaveBeenCalledTimes(2))
  const [url, options] = fetch.mock.calls[1]
  expect(url).toBe('http://localhost:8000/employees/1')
  expect(options.method).toBe('PATCH')
  expect(JSON.parse(options.body)).toEqual({
    first_name: 'Ada',
    last_name: 'Lovelace',
    department: 'Engineering',
    country: 'United States',
    band: 'L3',
    job_title: 'Senior Engineer',
    status: 'active',
  })
  expect(await screen.findByText('Profile updated.')).toBeInTheDocument()
})

test('shows the backend error when a profile update fails', async () => {
  vi.stubGlobal(
    'fetch',
    vi
      .fn()
      .mockResolvedValueOnce(response(200, detailResponse()))
      .mockResolvedValueOnce(response(409, { detail: 'An employee with this email already exists' })),
  )
  const user = userEvent.setup()
  renderPage()
  await screen.findByRole('heading', { name: 'Ada Lovelace' })

  await user.click(screen.getByRole('button', { name: 'Edit profile' }))
  await user.click(screen.getByRole('button', { name: 'Save profile' }))

  expect(await screen.findByText('An employee with this email already exists')).toBeInTheDocument()
})

test('submits a salary record and refreshes the detail response', async () => {
  const refreshed = detailResponse({
    employee: { ...detailResponse().employee, current_salary_amount: '100000.00', current_salary_id: 3 },
    salary_history: [
      {
        id: 3,
        employee_id: 1,
        amount: '100000.00',
        currency: 'USD',
        effective_date: '2025-01-01',
        reason: 'adjustment',
      },
      ...detailResponse().salary_history,
    ],
  })
  vi.stubGlobal(
    'fetch',
    vi
      .fn()
      .mockResolvedValueOnce(response(200, detailResponse()))
      .mockResolvedValueOnce(response(201, { id: 3 }))
      .mockResolvedValueOnce(response(200, refreshed)),
  )
  const user = userEvent.setup()
  renderPage()
  await screen.findByRole('heading', { name: 'Ada Lovelace' })

  await user.click(screen.getByRole('button', { name: 'Add salary' }))
  await user.type(screen.getByLabelText(/Amount/), '100000.00')
  await user.type(screen.getByLabelText(/Currency/), 'usd')
  fireEvent.change(screen.getByLabelText(/Effective date/), { target: { value: '2025-01-01' } })
  await user.selectOptions(screen.getByRole('combobox', { name: 'Reason' }), 'adjustment')
  await user.click(screen.getByRole('button', { name: 'Save salary record' }))

  await waitFor(() => expect(fetch).toHaveBeenCalledTimes(3))
  const [url, options] = fetch.mock.calls[1]
  expect(url).toBe('http://localhost:8000/employees/1/salaries')
  expect(options.method).toBe('POST')
  expect(JSON.parse(options.body)).toEqual({
    amount: '100000.00',
    currency: 'USD',
    effective_date: '2025-01-01',
    reason: 'adjustment',
  })
  expect(screen.getAllByText('$100,000.00')).toHaveLength(2)
  expect(screen.getByText('Salary record added.')).toBeInTheDocument()
})

test('does not submit an incomplete salary record', async () => {
  vi.stubGlobal('fetch', vi.fn().mockResolvedValue(response(200, detailResponse())))
  const user = userEvent.setup()
  renderPage()
  await screen.findByRole('heading', { name: 'Ada Lovelace' })

  await user.click(screen.getByRole('button', { name: 'Add salary' }))
  await user.click(screen.getByRole('button', { name: 'Save salary record' }))

  expect(await screen.findByText('Amount, currency, effective date, and reason are required.')).toBeInTheDocument()
  expect(fetch).toHaveBeenCalledTimes(1)
})

test('does not optimistically overwrite current salary for a backfill', async () => {
  let resolvePost
  const postResponse = new Promise((resolve) => {
    resolvePost = resolve
  })
  vi.stubGlobal(
    'fetch',
    vi
      .fn()
      .mockResolvedValueOnce(response(200, detailResponse()))
      .mockImplementationOnce(() => postResponse),
  )
  const user = userEvent.setup()
  renderPage()
  await screen.findByRole('heading', { name: 'Ada Lovelace' })

  await user.click(screen.getByRole('button', { name: 'Add salary' }))
  await user.type(screen.getByLabelText(/Amount/), '90000.00')
  await user.type(screen.getByLabelText(/Currency/), 'USD')
  fireEvent.change(screen.getByLabelText(/Effective date/), { target: { value: '2023-01-01' } })
  await user.selectOptions(screen.getByRole('combobox', { name: 'Reason' }), 'correction')
  await user.click(screen.getByRole('button', { name: 'Save salary record' }))

  expect(screen.getAllByText('$95,000.00')).toHaveLength(2)
  resolvePost(response(201, { id: 3 }))
})

test('renders an employee not-found state for a 404 response', async () => {
  vi.stubGlobal('fetch', vi.fn().mockResolvedValue(response(404, { detail: 'Employee not found' })))
  renderPage('/employees/999')

  expect(await screen.findByRole('heading', { name: 'Employee not found' })).toBeInTheDocument()
})
