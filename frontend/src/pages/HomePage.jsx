import { Paper, Typography } from '@mui/material'

import { useAuth } from '../auth/useAuth'

export function HomePage() {
  const { user } = useAuth()
  return (
    <Paper sx={{ p: 4 }}>
      <Typography component="h1" variant="h4">Welcome, {user.email}</Typography>
      <Typography color="text.secondary" sx={{ mt: 1 }}>
        Your salary management workspace is ready.
      </Typography>
    </Paper>
  )
}
