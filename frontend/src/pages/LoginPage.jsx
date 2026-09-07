import { Alert, Box, Button, Paper, Stack, TextField, Typography } from '@mui/material'
import { useState } from 'react'
import { Link, useLocation, useNavigate } from 'react-router-dom'

import { ApiError } from '../api/client'
import { useAuth } from '../auth/useAuth'

function validate(email, password) {
  if (!email || !password) return 'Email and password are required.'
  if (!/^\S+@\S+\.\S+$/.test(email)) return 'Enter a valid email address.'
  return null
}

export function LoginPage() {
  const { login } = useAuth()
  const navigate = useNavigate()
  const location = useLocation()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [submitting, setSubmitting] = useState(false)

  async function handleSubmit(event) {
    event.preventDefault()
    const validationError = validate(email, password)
    if (validationError) {
      setError(validationError)
      return
    }
    setError('')
    setSubmitting(true)
    try {
      await login(email, password)
      navigate(location.state?.from ?? '/', { replace: true })
    } catch (requestError) {
      setError(requestError instanceof ApiError ? requestError.message : 'Unable to sign in.')
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <AuthForm
      email={email}
      error={error}
      footer={<>Need an account? <Link to="/register">Register</Link></>}
      onSubmit={handleSubmit}
      password={password}
      setEmail={setEmail}
      setPassword={setPassword}
      submitLabel="Sign in"
      submitting={submitting}
      subtitle="Access your HR workspace."
      success={location.state?.message}
      title="Sign in"
    />
  )
}

export function AuthForm({
  title,
  subtitle,
  error,
  success,
  email,
  password,
  setEmail,
  setPassword,
  onSubmit,
  submitting,
  submitLabel,
  footer,
}) {
  return (
    <Box sx={{ display: 'grid', minHeight: '70vh', placeItems: 'center' }}>
      <Paper component="form" onSubmit={onSubmit} sx={{ p: 4, width: '100%', maxWidth: 420 }}>
        <Stack spacing={2.5}>
          <Box>
            <Typography component="h1" variant="h4">{title}</Typography>
            <Typography color="text.secondary">{subtitle}</Typography>
          </Box>
          {success && <Alert severity="success">{success}</Alert>}
          {error && <Alert severity="error">{error}</Alert>}
          <TextField autoComplete="email" label="Email" onChange={(event) => setEmail(event.target.value)} required type="email" value={email} />
          <TextField autoComplete="current-password" label="Password" onChange={(event) => setPassword(event.target.value)} required type="password" value={password} />
          <Button disabled={submitting} size="large" type="submit" variant="contained">{submitLabel}</Button>
          <Typography variant="body2">{footer}</Typography>
        </Stack>
      </Paper>
    </Box>
  )
}
