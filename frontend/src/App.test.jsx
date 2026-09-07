import { cleanup, render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, expect, test, vi } from 'vitest'
import { MemoryRouter } from 'react-router-dom'

import { TOKEN_STORAGE_KEY } from './api/client'
import { AppRoutes } from './App'
import { AuthProvider } from './auth/AuthContext'

function response(status, body) {
  return {
    ok: status >= 200 && status < 300,
    status,
    json: async () => body,
  }
}

function renderApp(initialEntry = '/login') {
  return render(
    <MemoryRouter initialEntries={[initialEntry]}>
      <AuthProvider>
        <AppRoutes />
      </AuthProvider>
    </MemoryRouter>,
  )
}

afterEach(() => {
  cleanup()
  window.localStorage.clear()
  vi.unstubAllGlobals()
})

test('login form shows the backend error for wrong credentials', async () => {
  vi.stubGlobal('fetch', vi.fn().mockResolvedValue(response(401, { detail: 'Incorrect email or password' })))
  const user = userEvent.setup()
  renderApp()

  await user.type(screen.getByLabelText(/Email/), 'hr@example.com')
  await user.type(screen.getByLabelText(/Password/), 'wrong-password')
  await user.click(screen.getByRole('button', { name: 'Sign in' }))

  expect(await screen.findByText('Incorrect email or password')).toBeInTheDocument()
})

test('login redirects to the authenticated home page on success', async () => {
  vi.stubGlobal(
    'fetch',
    vi
      .fn()
      .mockResolvedValueOnce(response(200, { access_token: 'valid-token', token_type: 'bearer' }))
      .mockResolvedValueOnce(response(200, { id: 1, email: 'hr@example.com', role: 'hr_admin' }))
      .mockResolvedValueOnce(response(200, { items: [], total: 0, limit: 25, offset: 0 })),
  )
  const user = userEvent.setup()
  renderApp()

  await user.type(screen.getByLabelText(/Email/), 'hr@example.com')
  await user.type(screen.getByLabelText(/Password/), 'correct-password')
  await user.click(screen.getByRole('button', { name: 'Sign in' }))

  expect(await screen.findByRole('heading', { name: 'Employees' })).toBeInTheDocument()
  expect(window.localStorage.getItem(TOKEN_STORAGE_KEY)).toBe('valid-token')
})

test('protected routes redirect unauthenticated users to login', async () => {
  renderApp('/')

  expect(await screen.findByRole('heading', { name: 'Sign in' })).toBeInTheDocument()
})

test('protected routes render their content for an authenticated user', async () => {
  window.localStorage.setItem(TOKEN_STORAGE_KEY, 'valid-token')
  vi.stubGlobal(
    'fetch',
    vi
      .fn()
      .mockResolvedValueOnce(response(200, { id: 1, email: 'hr@example.com', role: 'hr_admin' }))
      .mockResolvedValueOnce(response(200, { items: [], total: 0, limit: 25, offset: 0 })),
  )
  renderApp('/')

  expect(await screen.findByRole('heading', { name: 'Employees' })).toBeInTheDocument()
  expect(screen.getByRole('button', { name: 'Log out' })).toBeInTheDocument()
})
