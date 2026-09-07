import {
  Alert,
  Box,
  CircularProgress,
  FormControl,
  InputLabel,
  NativeSelect,
  Paper,
  Stack,
  Typography,
} from '@mui/material'
import { useCallback, useEffect, useState } from 'react'
import {
  Bar,
  BarChart,
  CartesianGrid,
  Legend,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'

import { api } from '../api/client'
import { COUNTRIES, DEPARTMENTS } from '../referenceData'

const CHART_HEIGHT = 280
const BLUE = '#1769aa'
const TEAL = '#00897b'

function formatMoney(amount, currency) {
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency,
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(Number(amount))
}

function ChartFrame({ data, dataKey, height = CHART_HEIGHT, label, secondaryDataKey }) {
  return (
    <Box aria-label={label} sx={{ height }}>
      <ResponsiveContainer height="100%" width="100%">
        <BarChart data={data} margin={{ top: 8, right: 8, bottom: 36, left: 0 }}>
          <CartesianGrid strokeDasharray="3 3" />
          <XAxis angle={-25} dataKey="group" interval={0} textAnchor="end" tick={{ fontSize: 12 }} />
          <YAxis allowDecimals={false} />
          <Tooltip />
          {secondaryDataKey && <Legend />}
          <Bar dataKey={dataKey} fill={BLUE} name={dataKey} />
          {secondaryDataKey && <Bar dataKey={secondaryDataKey} fill={TEAL} name={secondaryDataKey} />}
        </BarChart>
      </ResponsiveContainer>
    </Box>
  )
}

function Section({ children, error, loading, title }) {
  return (
    <Paper sx={{ minHeight: 180, p: 3 }}>
      <Typography component="h2" variant="h6">{title}</Typography>
      {loading ? (
        <Stack alignItems="center" sx={{ py: 6 }}>
          <CircularProgress aria-label={`Loading ${title}`} />
        </Stack>
      ) : error ? (
        <Alert severity="error">{error}</Alert>
      ) : children}
    </Paper>
  )
}

function useAnalyticsRequest(request) {
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  const load = useCallback(async () => {
    setLoading(true)
    setError('')
    try {
      setData(await request())
    } catch {
      setError('Unable to load this insight.')
    } finally {
      setLoading(false)
    }
  }, [request])

  useEffect(() => {
    void Promise.resolve().then(load)
  }, [load])

  return { data, error, loading }
}

function leadingSummary(items, noun) {
  if (!items?.length) return `No ${noun} data is available.`
  const [first, second] = [...items].sort((left, right) => right.count - left.count)
  return second
    ? `${first.group} has the highest ${noun} at ${first.count.toLocaleString()}, followed by ${second.group} at ${second.count.toLocaleString()}.`
    : `${first.group} has ${first.count.toLocaleString()} ${noun}.`
}

function HeadcountSection() {
  const request = useCallback(() => api.getHeadcount(), [])
  const { data, error, loading } = useAnalyticsRequest(request)
  return (
    <Section error={error} loading={loading} title="Headcount">
      {data && (
        <Stack spacing={4} sx={{ mt: 2 }}>
          <Box>
            <Typography sx={{ mb: 1 }} variant="body2">{leadingSummary(data.by_department, 'headcount')}</Typography>
            <ChartFrame data={data.by_department} dataKey="count" label="Headcount by department" />
          </Box>
          <Box>
            <Typography sx={{ mb: 1 }} variant="body2">{leadingSummary(data.by_country, 'headcount')}</Typography>
            <ChartFrame data={data.by_country} dataKey="count" label="Headcount by country" />
          </Box>
        </Stack>
      )}
    </Section>
  )
}

function groupByCurrency(items) {
  return items.reduce((groups, item) => {
    const current = groups.get(item.currency) ?? []
    current.push(item)
    groups.set(item.currency, current)
    return groups
  }, new Map())
}

function CurrencyMetricCharts({ items, metric, title, valueKeys }) {
  const currencies = groupByCurrency(items)
  if (currencies.size === 0) return <Typography sx={{ mt: 2 }}>No salary data is available.</Typography>
  return (
    <Stack spacing={3} sx={{ mt: 2 }}>
      {[...currencies.entries()].map(([currency, rows]) => {
        const chartData = rows.map((row) => ({
          group: row.group,
          [valueKeys[0]]: Number(row[valueKeys[0]]),
          [valueKeys[1]]: Number(row[valueKeys[1]]),
        }))
        const first = chartData[0]
        return (
          <Box key={currency} sx={{ borderLeft: 3, borderColor: 'primary.main', pl: 2 }}>
            <Typography fontWeight={700}>{currency} {title}</Typography>
            <Typography color="text.secondary" sx={{ mb: 1 }} variant="body2">
              {first.group}: {metric(first[valueKeys[0]], currency)} {valueKeys[0]}, {metric(first[valueKeys[1]], currency)} {valueKeys[1]}. Values are shown only within {currency}.
            </Typography>
            <ChartFrame
              data={chartData}
              dataKey={valueKeys[0]}
              label={`${currency} ${title}`}
              secondaryDataKey={valueKeys[1]}
            />
          </Box>
        )
      })}
    </Stack>
  )
}

function SalarySummarySection() {
  const request = useCallback(() => api.getSalarySummary(), [])
  const { data, error, loading } = useAnalyticsRequest(request)
  return (
    <Section error={error} loading={loading} title="Salary summary">
      <Typography sx={{ mt: 1 }} variant="body2">
        Average and median current salaries are grouped into separate currency charts. No currency conversion is applied.
      </Typography>
      {data && (
        <Stack spacing={4} sx={{ mt: 2 }}>
          <Box>
            <Typography variant="subtitle1">By department</Typography>
            <CurrencyMetricCharts items={data.by_department} metric={formatMoney} title="department salary summary" valueKeys={['average', 'median']} />
          </Box>
          <Box>
            <Typography variant="subtitle1">By country</Typography>
            <CurrencyMetricCharts items={data.by_country} metric={formatMoney} title="country salary summary" valueKeys={['average', 'median']} />
          </Box>
        </Stack>
      )}
    </Section>
  )
}

function BandDistributionSection() {
  const [department, setDepartment] = useState('')
  const [country, setCountry] = useState('')
  const request = useCallback(() => api.getBandDistribution({ department, country }), [department, country])
  const { data, error, loading } = useAnalyticsRequest(request)
  const chartData = data?.bands.map((item) => ({ group: item.band, count: item.count })) ?? []
  return (
    <Section error={error} loading={loading} title="Band distribution">
      <Box sx={{ display: 'grid', gap: 2, gridTemplateColumns: { xs: '1fr', sm: 'repeat(2, 220px)' }, mt: 2 }}>
        <SelectFilter label="Department" onChange={setDepartment} options={DEPARTMENTS} value={department} />
        <SelectFilter label="Country" onChange={setCountry} options={COUNTRIES} value={country} />
      </Box>
      {data && (
        <Box sx={{ mt: 2 }}>
          <Typography sx={{ mb: 1 }} variant="body2">{leadingSummary(chartData, 'employees by band')}</Typography>
          <ChartFrame data={chartData} dataKey="count" label="Employee count by band" />
        </Box>
      )}
    </Section>
  )
}

function SelectFilter({ label, onChange, options, value }) {
  const id = `${label.toLowerCase()}-insights-filter`
  return (
    <FormControl fullWidth size="small">
      <InputLabel htmlFor={id} shrink>{label}</InputLabel>
      <NativeSelect id={id} inputProps={{ 'aria-label': label }} onChange={(event) => onChange(event.target.value)} value={value}>
        <option value="">All {label.toLowerCase()}s</option>
        {options.map((option) => <option key={option} value={option}>{option}</option>)}
      </NativeSelect>
    </FormControl>
  )
}

function SalaryRangeSection() {
  const request = useCallback(() => api.getSalaryRange(), [])
  const { data, error, loading } = useAnalyticsRequest(request)
  return (
    <Section error={error} loading={loading} title="Salary range">
      <Typography sx={{ mt: 1 }} variant="body2">
        Minimum and maximum current salaries remain separated by currency.
      </Typography>
      {data && (
        <Stack spacing={4} sx={{ mt: 2 }}>
          <Box>
            <Typography variant="subtitle1">By department</Typography>
            <CurrencyMetricCharts items={data.by_department} metric={formatMoney} title="department salary range" valueKeys={['minimum', 'maximum']} />
          </Box>
          <Box>
            <Typography variant="subtitle1">By country</Typography>
            <CurrencyMetricCharts items={data.by_country} metric={formatMoney} title="country salary range" valueKeys={['minimum', 'maximum']} />
          </Box>
        </Stack>
      )}
    </Section>
  )
}

export function InsightsPage() {
  return (
    <Stack spacing={3}>
      <Box>
        <Typography component="h1" variant="h4">Insights</Typography>
        <Typography color="text.secondary">A current view of headcount and pay, without blending currencies.</Typography>
      </Box>
      <HeadcountSection />
      <SalarySummarySection />
      <BandDistributionSection />
      <SalaryRangeSection />
    </Stack>
  )
}
