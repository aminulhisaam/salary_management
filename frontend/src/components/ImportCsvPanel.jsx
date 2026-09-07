import { Alert, Box, Button, Link, Paper, Stack, Typography } from '@mui/material'
import { useState } from 'react'

import { ApiError, api } from '../api/client'

export function ImportCsvPanel({ onImported }) {
  const [file, setFile] = useState(null)
  const [result, setResult] = useState(null)
  const [submitting, setSubmitting] = useState(false)

  async function upload() {
    if (!file) {
      setResult({ error: 'Choose a CSV file before uploading.', rows_rejected: [] })
      return
    }
    setSubmitting(true)
    setResult(null)
    try {
      const response = await api.importEmployees(file)
      setResult(response)
      onImported()
    } catch (requestError) {
      if (requestError instanceof ApiError && requestError.body) setResult(requestError.body)
      else setResult({ error: 'Unable to import this CSV file.', rows_rejected: [] })
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <Paper sx={{ p: 2 }}>
      <Stack spacing={2}>
        <Box>
          <Typography component="h2" variant="h6">Import employees</Typography>
          <Typography color="text.secondary" variant="body2">
            Each row creates an employee and an initial hire salary. The full file is validated before anything is written.
          </Typography>
        </Box>
        <Stack alignItems={{ sm: 'center' }} direction={{ xs: 'column', sm: 'row' }} spacing={2}>
          <Button component="label" variant="outlined">
            Choose CSV
            <input
              accept=".csv,text/csv"
              aria-label="CSV file"
              hidden
              onChange={(event) => setFile(event.target.files?.[0] ?? null)}
              type="file"
            />
          </Button>
          <Typography color="text.secondary" variant="body2">{file?.name ?? 'No file selected'}</Typography>
          <Button disabled={!file || submitting} onClick={upload} variant="contained">
            {submitting ? 'Importing...' : 'Upload CSV'}
          </Button>
          <Link download href="/employee-import-template.csv">Download template</Link>
        </Stack>
        {result?.rows_imported > 0 && (
          <Alert severity="success">{result.rows_imported} employees imported successfully.</Alert>
        )}
        {result?.error && <Alert severity="error">{result.error}</Alert>}
        {result?.rows_rejected?.length > 0 && (
          <Box sx={{ maxHeight: 180, overflowY: 'auto' }}>
            <Typography fontWeight={700} variant="body2">Rows to fix</Typography>
            <Stack component="ul" spacing={0.5} sx={{ m: 0, mt: 1, pl: 2.5 }}>
              {result.rows_rejected.map((rowError, index) => (
                <Typography component="li" key={`${rowError.row}-${index}`} variant="body2">
                  Row {rowError.row}: {rowError.message}
                </Typography>
              ))}
            </Stack>
          </Box>
        )}
      </Stack>
    </Paper>
  )
}
