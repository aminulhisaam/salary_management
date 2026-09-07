import {
  Alert,
  Box,
  Button,
  CircularProgress,
  FormControl,
  InputLabel,
  NativeSelect,
  Paper,
  Stack,
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableRow,
  TextField,
  Typography,
} from '@mui/material'
import { useCallback, useEffect, useState } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'

import { api } from '../api/client'
import { ImportCsvPanel } from '../components/ImportCsvPanel'
import { BANDS, COUNTRIES, DEPARTMENTS, STATUSES } from '../referenceData'

const PAGE_SIZE = 25

function readPage(value) {
  const page = Number(value)
  return Number.isInteger(page) && page > 0 ? page : 1
}

function formatSalary(amount, currency) {
  if (amount == null || !currency) return 'Not set'
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency,
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(Number(amount))
}

function FilterSelect({ label, name, options, value, onChange }) {
  const id = `${name}-filter`
  return (
    <FormControl fullWidth size="small">
      <InputLabel htmlFor={id} shrink>
        {label}
      </InputLabel>
      <NativeSelect
        id={id}
        inputProps={{ 'aria-label': label }}
        label={label}
        name={name}
        onChange={onChange}
        value={value}
      >
        <option value="">All {label.toLowerCase()}s</option>
        {options.map((option) => (
          <option key={option} value={option}>
            {option}
          </option>
        ))}
      </NativeSelect>
    </FormControl>
  )
}

export function EmployeeListPage() {
  const navigate = useNavigate()
  const [searchParams, setSearchParams] = useSearchParams()
  const page = readPage(searchParams.get('page'))
  const search = searchParams.get('search') ?? ''
  const department = searchParams.get('department') ?? ''
  const country = searchParams.get('country') ?? ''
  const band = searchParams.get('band') ?? ''
  const status = searchParams.get('status') ?? ''
  const [searchInput, setSearchInput] = useState(search)
  const [data, setData] = useState({ items: [], total: 0 })
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [showImport, setShowImport] = useState(false)
  const [refreshKey, setRefreshKey] = useState(0)

  const updateQuery = useCallback(
    (changes) => {
      const next = new URLSearchParams(searchParams)
      Object.entries(changes).forEach(([key, value]) => {
        if (value) next.set(key, value)
        else next.delete(key)
      })
      setSearchParams(next)
    },
    [searchParams, setSearchParams],
  )

  useEffect(() => {
    if (searchInput === search) return undefined
    const timeoutId = window.setTimeout(() => {
      updateQuery({ page: '1', search: searchInput })
    }, 300)
    return () => window.clearTimeout(timeoutId)
  }, [search, searchInput, updateQuery])

  useEffect(() => {
    let active = true
    const params = {
      limit: String(PAGE_SIZE),
      offset: String((page - 1) * PAGE_SIZE),
    }
    if (search) params.search = search
    if (department) params.department = department
    if (country) params.country = country
    if (band) params.band = band
    if (status) params.status = status

    async function loadEmployees() {
      await Promise.resolve()
      if (!active) return
      setLoading(true)
      setError('')
      try {
        const response = await api.getEmployees(params)
        if (active) setData(response)
      } catch {
        if (active) setError('Unable to load employees.')
      } finally {
        if (active) setLoading(false)
      }
    }
    loadEmployees()
    return () => {
      active = false
    }
  }, [band, country, department, page, refreshKey, search, status])

  const totalPages = Math.max(1, Math.ceil(data.total / PAGE_SIZE))

  function handleFilterChange(event) {
    updateQuery({ [event.target.name]: event.target.value, page: '1' })
  }

  return (
    <Stack spacing={3}>
      <Box sx={{ alignItems: { sm: 'center' }, display: 'flex', justifyContent: 'space-between', gap: 2 }}>
        <Box>
          <Typography component="h1" variant="h4">
            Employees
          </Typography>
          <Typography color="text.secondary">{data.total.toLocaleString()} employees</Typography>
        </Box>
        <Button onClick={() => setShowImport((current) => !current)} variant="outlined">
          Import CSV
        </Button>
      </Box>

      {showImport && <ImportCsvPanel onImported={() => setRefreshKey((current) => current + 1)} />}

      <Paper sx={{ p: 2 }}>
        <Box
          sx={{
            display: 'grid',
            gap: 2,
            gridTemplateColumns: { xs: '1fr', md: '2fr repeat(4, 1fr)' },
          }}
        >
          <TextField
            label="Search name or email"
            onChange={(event) => setSearchInput(event.target.value)}
            size="small"
            value={searchInput}
          />
          <FilterSelect
            label="Department"
            name="department"
            onChange={handleFilterChange}
            options={DEPARTMENTS}
            value={department}
          />
          <FilterSelect
            label="Country"
            name="country"
            onChange={handleFilterChange}
            options={COUNTRIES}
            value={country}
          />
          <FilterSelect
            label="Band"
            name="band"
            onChange={handleFilterChange}
            options={BANDS}
            value={band}
          />
          <FilterSelect
            label="Status"
            name="status"
            onChange={handleFilterChange}
            options={STATUSES}
            value={status}
          />
        </Box>
      </Paper>

      {error && <Alert severity="error">{error}</Alert>}
      {loading ? (
        <Stack alignItems="center" sx={{ py: 6 }}>
          <CircularProgress aria-label="Loading employees" />
        </Stack>
      ) : data.items.length === 0 ? (
        <Paper sx={{ p: 4 }}>
          <Typography>No employees match these filters.</Typography>
        </Paper>
      ) : (
        <Paper sx={{ overflowX: 'auto' }}>
          <Table aria-label="Employees">
            <TableHead>
              <TableRow>
                <TableCell>Employee code</TableCell>
                <TableCell>Name</TableCell>
                <TableCell>Department</TableCell>
                <TableCell>Country</TableCell>
                <TableCell>Band</TableCell>
                <TableCell>Current salary</TableCell>
                <TableCell>Status</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {data.items.map((employee) => (
                <TableRow
                  hover
                  key={employee.id}
                  onClick={() => navigate({
                    pathname: `/employees/${employee.id}`,
                    search: searchParams.toString(),
                  })}
                  sx={{ cursor: 'pointer' }}
                >
                  <TableCell>{employee.employee_code}</TableCell>
                  <TableCell>{employee.first_name} {employee.last_name}</TableCell>
                  <TableCell>{employee.department}</TableCell>
                  <TableCell>{employee.country}</TableCell>
                  <TableCell>{employee.band}</TableCell>
                  <TableCell>
                    {formatSalary(employee.current_salary_amount, employee.current_salary_currency)}
                  </TableCell>
                  <TableCell>{employee.status}</TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </Paper>
      )}

      <Stack alignItems="center" direction="row" justifyContent="space-between">
        <Button disabled={page === 1} onClick={() => updateQuery({ page: String(page - 1) })}>
          Previous
        </Button>
        <Typography>
          Page {page} of {totalPages}
        </Typography>
        <Button
          disabled={page >= totalPages}
          onClick={() => updateQuery({ page: String(page + 1) })}
        >
          Next
        </Button>
      </Stack>
    </Stack>
  )
}
