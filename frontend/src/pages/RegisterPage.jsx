import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'

import { ApiError } from '../api/client'
import { useAuth } from '../auth/useAuth'
import { AuthForm } from './LoginPage'

function validate(email, password) {
  if (!email || !password) return 'Email and password are required.'
  if (!/^\S+@\S+\.\S+$/.test(email)) return 'Enter a valid email address.'
  return null
}

export function RegisterPage() {
  const { register } = useAuth()
  const navigate = useNavigate()
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
      await register(email, password)
      navigate('/login', {
        replace: true,
        state: { message: 'Account created. Please sign in.' },
      })
    } catch (requestError) {
      setError(requestError instanceof ApiError ? requestError.message : 'Unable to register.')
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <AuthForm
      email={email}
      error={error}
      footer={<>Already registered? <Link to="/login">Sign in</Link></>}
      onSubmit={handleSubmit}
      password={password}
      setEmail={setEmail}
      setPassword={setPassword}
      submitLabel="Create account"
      submitting={submitting}
      subtitle="Set up your HR workspace access."
      title="Create account"
    />
  )
}
