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
  TextField,
  Typography,
} from '@mui/material'
import { useCallback, useEffect, useState } from 'react'
import { Link, useLocation, useParams } from 'react-router-dom'

import { ApiError, api } from '../api/client'
import { BANDS, COUNTRIES, DEPARTMENTS, STATUSES } from '../referenceData'

const SALARY_REASONS = ['hire', 'promotion', 'adjustment', 'correction']

function formatSalary(amount, currency) {
  if (amount == null || !currency) return 'Not set'
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency,
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(Number(amount))
}

function SelectField({ label, name, options, value, onChange }) {
  const id = `${name}-field`
  return (
    <FormControl fullWidth size="small">
      <InputLabel htmlFor={id} shrink>
        {label}
      </InputLabel>
      <NativeSelect
        id={id}
        inputProps={{ 'aria-label': label }}
        name={name}
        onChange={onChange}
        value={value}
      >
        {options.map((option) => (
          <option key={option} value={option}>
            {option}
          </option>
        ))}
      </NativeSelect>
    </FormControl>
  )
}

function ProfileFields({ employee }) {
  const fields = [
    ['Employee code', employee.employee_code],
    ['Email', employee.email],
    ['Department', employee.department],
    ['Country', employee.country],
    ['Band', employee.band],
    ['Job title', employee.job_title],
    ['Hire date', employee.hire_date],
    ['Status', employee.status],
  ]
  return (
    <Box sx={{ display: 'grid', gap: 2, gridTemplateColumns: { xs: '1fr', sm: 'repeat(2, 1fr)' } }}>
      {fields.map(([label, value]) => (
        <Box key={label}>
          <Typography color="text.secondary" variant="caption">
            {label}
          </Typography>
          <Typography>{value}</Typography>
        </Box>
      ))}
    </Box>
  )
}

function EditProfileForm({ employee, onCancel, onSaved }) {
  const [values, setValues] = useState({
    first_name: employee.first_name,
    last_name: employee.last_name,
    department: employee.department,
    country: employee.country,
    band: employee.band,
    job_title: employee.job_title,
    status: employee.status,
  })
  const [error, setError] = useState('')
  const [success, setSuccess] = useState('')
  const [submitting, setSubmitting] = useState(false)

  function updateValue(event) {
    setValues((current) => ({ ...current, [event.target.name]: event.target.value }))
  }

  async function submit(event) {
    event.preventDefault()
    if (!values.first_name.trim() || !values.last_name.trim() || !values.job_title.trim()) {
      setError('First name, last name, and job title are required.')
      return
    }
    setError('')
    setSuccess('')
    setSubmitting(true)
    try {
      const updated = await api.updateEmployee(employee.id, {
        ...values,
        first_name: values.first_name.trim(),
        last_name: values.last_name.trim(),
        job_title: values.job_title.trim(),
      })
      onSaved(updated)
      setSuccess('Profile updated.')
    } catch (requestError) {
      setError(requestError instanceof ApiError ? requestError.message : 'Unable to update profile.')
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <Paper component="form" noValidate onSubmit={submit} sx={{ p: 3 }}>
      <Stack spacing={2.5}>
        <Typography component="h2" variant="h6">
          Edit profile
        </Typography>
        {success && <Alert severity="success">{success}</Alert>}
        {error && <Alert severity="error">{error}</Alert>}
        <Box sx={{ display: 'grid', gap: 2, gridTemplateColumns: { xs: '1fr', sm: 'repeat(2, 1fr)' } }}>
          <TextField label="First name" name="first_name" onChange={updateValue} required size="small" value={values.first_name} />
          <TextField label="Last name" name="last_name" onChange={updateValue} required size="small" value={values.last_name} />
          <SelectField label="Department" name="department" onChange={updateValue} options={DEPARTMENTS} value={values.department} />
          <SelectField label="Country" name="country" onChange={updateValue} options={COUNTRIES} value={values.country} />
          <SelectField label="Band" name="band" onChange={updateValue} options={BANDS} value={values.band} />
          <SelectField label="Status" name="status" onChange={updateValue} options={STATUSES} value={values.status} />
          <TextField label="Job title" name="job_title" onChange={updateValue} required size="small" value={values.job_title} />
        </Box>
        <Stack direction="row" spacing={1}>
          <Button disabled={submitting} type="submit" variant="contained">
            Save profile
          </Button>
          <Button disabled={submitting} onClick={onCancel} type="button">
            Cancel
          </Button>
        </Stack>
      </Stack>
    </Paper>
  )
}

function AddSalaryForm({ employeeId, onCancel, onSaved }) {
  const [values, setValues] = useState({ amount: '', currency: '', effective_date: '', reason: '' })
  const [error, setError] = useState('')
  const [success, setSuccess] = useState('')
  const [submitting, setSubmitting] = useState(false)

  function updateValue(event) {
    setValues((current) => ({ ...current, [event.target.name]: event.target.value }))
  }

  async function submit(event) {
    event.preventDefault()
    if (!values.amount || !values.currency.trim() || !values.effective_date || !values.reason) {
      setError('Amount, currency, effective date, and reason are required.')
      return
    }
    if (Number(values.amount) <= 0) {
      setError('Amount must be greater than zero.')
      return
    }
    setError('')
    setSuccess('')
    setSubmitting(true)
    try {
      await api.addSalary(employeeId, { ...values, currency: values.currency.trim().toUpperCase() })
      await onSaved()
      setSuccess('Salary record added.')
    } catch (requestError) {
      setError(requestError instanceof ApiError ? requestError.message : 'Unable to add salary record.')
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <Paper component="form" noValidate onSubmit={submit} sx={{ p: 3 }}>
      <Stack spacing={2.5}>
        <Typography component="h2" variant="h6">
          Add salary record
        </Typography>
        {success && <Alert severity="success">{success}</Alert>}
        {error && <Alert severity="error">{error}</Alert>}
        <Box sx={{ display: 'grid', gap: 2, gridTemplateColumns: { xs: '1fr', sm: 'repeat(2, 1fr)' } }}>
          <TextField
            inputProps={{ inputMode: 'decimal', pattern: '^\\d+(\\.\\d{1,2})?$' }}
            label="Amount"
            name="amount"
            onChange={updateValue}
            required
            size="small"
            value={values.amount}
          />
          <TextField inputProps={{ maxLength: 3 }} label="Currency" name="currency" onChange={updateValue} required size="small" value={values.currency} />
          <TextField InputLabelProps={{ shrink: true }} label="Effective date" name="effective_date" onChange={updateValue} required size="small" type="date" value={values.effective_date} />
          <SelectField label="Reason" name="reason" onChange={updateValue} options={SALARY_REASONS} value={values.reason} />
        </Box>
        <Stack direction="row" spacing={1}>
          <Button disabled={submitting} type="submit" variant="contained">
            Save salary record
          </Button>
          <Button disabled={submitting} onClick={onCancel} type="button">
            Cancel
          </Button>
        </Stack>
      </Stack>
    </Paper>
  )
}

function SalaryTimeline({ employee, salaryHistory }) {
  return (
    <Paper sx={{ p: 3 }}>
      <Typography component="h2" variant="h6">
        Salary history
      </Typography>
      <Stack component="ol" spacing={0} sx={{ listStyle: 'none', m: 0, mt: 2, p: 0 }}>
        {salaryHistory.map((salary) => {
          const isCurrent = salary.id === employee.current_salary_id
          return (
            <Box component="li" data-testid="salary-entry" key={salary.id} sx={{ borderLeft: 2, borderColor: isCurrent ? 'primary.main' : 'divider', pb: 3, pl: 2 }}>
              <Stack alignItems="baseline" direction="row" justifyContent="space-between" spacing={2}>
                <Typography fontWeight={isCurrent ? 700 : 500}>
                  {formatSalary(salary.amount, salary.currency)}
                </Typography>
                <Typography color="text.secondary" variant="body2">
                  {salary.effective_date}
                </Typography>
              </Stack>
              <Typography color="text.secondary" variant="body2">
                {salary.reason}{isCurrent ? ' - Current salary' : ''}
              </Typography>
            </Box>
          )
        })}
      </Stack>
    </Paper>
  )
}

export function EmployeeDetailPage() {
  const { employeeId } = useParams()
  const location = useLocation()
  const [detail, setDetail] = useState(null)
  const [loading, setLoading] = useState(true)
  const [notFound, setNotFound] = useState(false)
  const [error, setError] = useState('')
  const [editing, setEditing] = useState(false)
  const [addingSalary, setAddingSalary] = useState(false)

  const loadDetail = useCallback(async (showLoading = true) => {
    if (showLoading) setLoading(true)
    setError('')
    setNotFound(false)
    try {
      setDetail(await api.getEmployee(employeeId))
    } catch (requestError) {
      if (requestError instanceof ApiError && requestError.status === 404) setNotFound(true)
      else setError(requestError instanceof ApiError ? requestError.message : 'Unable to load employee.')
    } finally {
      if (showLoading) setLoading(false)
    }
  }, [employeeId])

  useEffect(() => {
    void Promise.resolve().then(() => loadDetail())
  }, [loadDetail])

  if (loading) {
    return (
      <Stack alignItems="center" sx={{ py: 8 }}>
        <CircularProgress aria-label="Loading employee" />
      </Stack>
    )
  }

  if (notFound) {
    return (
      <Stack spacing={2}>
        <Typography component="h1" variant="h4">Employee not found</Typography>
        <Button component={Link} to={`/employees${location.search}`} variant="outlined">Back to list</Button>
      </Stack>
    )
  }

  if (error || !detail) return <Alert severity="error">{error || 'Unable to load employee.'}</Alert>

  const { employee, salary_history: salaryHistory } = detail
  return (
    <Stack spacing={3}>
      <Button component={Link} sx={{ alignSelf: 'flex-start' }} to={`/employees${location.search}`}>
        Back to list
      </Button>

      <Paper sx={{ p: 3 }}>
        <Stack spacing={3}>
          <Stack alignItems={{ sm: 'center' }} direction={{ xs: 'column', sm: 'row' }} justifyContent="space-between" spacing={2}>
            <Box>
              <Typography component="h1" variant="h4">
                {employee.first_name} {employee.last_name}
              </Typography>
              <Typography color="text.secondary">{employee.employee_code}</Typography>
            </Box>
            <Stack direction="row" spacing={1}>
              <Button onClick={() => setEditing((current) => !current)} variant="outlined">Edit profile</Button>
              <Button onClick={() => setAddingSalary((current) => !current)} variant="contained">Add salary</Button>
            </Stack>
          </Stack>
          <Box sx={{ borderLeft: 4, borderColor: 'primary.main', pl: 2 }}>
            <Typography color="text.secondary" variant="body2">Current salary</Typography>
            <Typography variant="h5">
              {formatSalary(employee.current_salary_amount, employee.current_salary_currency)}
            </Typography>
          </Box>
          <ProfileFields employee={employee} />
        </Stack>
      </Paper>

      {editing && (
        <EditProfileForm
          employee={employee}
          onCancel={() => setEditing(false)}
          onSaved={(updated) => setDetail((current) => ({ ...current, employee: updated }))}
        />
      )}
      {addingSalary && <AddSalaryForm employeeId={employee.id} onCancel={() => setAddingSalary(false)} onSaved={() => loadDetail(false)} />}
      <SalaryTimeline employee={employee} salaryHistory={salaryHistory} />
    </Stack>
  )
}
