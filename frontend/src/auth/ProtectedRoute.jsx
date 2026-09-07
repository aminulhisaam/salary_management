import { CircularProgress, Stack } from '@mui/material'
import { Navigate, useLocation } from 'react-router-dom'

import { useAuth } from './useAuth'

export function ProtectedRoute({ children }) {
  const { loading, user } = useAuth()
  const location = useLocation()
  if (loading) {
    return (
      <Stack alignItems="center" sx={{ pt: 8 }}>
        <CircularProgress aria-label="Checking session" />
      </Stack>
    )
  }
  if (!user) return <Navigate to="/login" replace state={{ from: location.pathname }} />
  return children
}
