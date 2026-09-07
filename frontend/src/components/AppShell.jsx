import { AppBar, Box, Button, Container, Toolbar, Typography } from '@mui/material'
import { Link } from 'react-router-dom'

import { useAuth } from '../auth/useAuth'

export function AppShell({ children }) {
  const { user, logout } = useAuth()
  return (
    <Box sx={{ minHeight: '100vh', bgcolor: 'grey.50' }}>
      {user && (
        <AppBar color="default" elevation={0} position="static">
          <Toolbar sx={{ borderBottom: 1, borderColor: 'divider' }}>
            <Typography color="text.primary" fontWeight={700} variant="h6">
              Salary Management
            </Typography>
            <Box sx={{ flexGrow: 1 }} />
            <Button component={Link} to="/employees">Employees</Button>
            <Button component={Link} to="/insights">Insights</Button>
            <Typography color="text.secondary" sx={{ mr: 2 }} variant="body2">
              {user.email}
            </Typography>
            <Button color="inherit" onClick={logout} variant="outlined">
              Log out
            </Button>
          </Toolbar>
        </AppBar>
      )}
      <Container component="main" maxWidth="lg" sx={{ py: 5 }}>
        {children}
      </Container>
    </Box>
  )
}
