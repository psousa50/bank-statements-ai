import { useCallback, useEffect, useState } from 'react'
import {
  Alert,
  Box,
  Button,
  Collapse,
  MenuItem,
  Paper,
  Select,
  Stack,
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableRow,
  Typography,
} from '@mui/material'
import { useApi } from '../api/ApiContext'
import { useQueryClient } from '@tanstack/react-query'
import {
  AccountConversionCandidate,
  CounterpartyType,
  COUNTERPARTY_TYPES,
  COUNTERPARTY_TYPE_LABELS,
} from '../types/Counterparty'
import { ACCOUNT_QUERY_KEYS } from '../services/hooks/useAccounts'

interface AccountConversionPanelProps {
  onConverted: (message: string) => void
  onFailed: (message: string) => void
}

export const AccountConversionPanel = ({ onConverted, onFailed }: AccountConversionPanelProps) => {
  const api = useApi()
  const queryClient = useQueryClient()
  const [candidates, setCandidates] = useState<AccountConversionCandidate[]>([])
  const [types, setTypes] = useState<Record<string, CounterpartyType>>({})
  const [expanded, setExpanded] = useState(false)
  const [converting, setConverting] = useState<string | null>(null)

  const loadCandidates = useCallback(async () => {
    try {
      setCandidates(await api.accounts.getConversionCandidates())
    } catch {
      setCandidates([])
    }
  }, [api.accounts])

  useEffect(() => {
    loadCandidates()
  }, [loadCandidates])

  const convert = useCallback(
    async (candidate: AccountConversionCandidate) => {
      setConverting(candidate.account_id)
      try {
        const result = await api.accounts.convertToCounterparty(
          candidate.account_id,
          types[candidate.account_id] ?? 'other'
        )
        onConverted(
          `"${candidate.name}" is now a counterparty (${result.transactions_repointed} transactions, ` +
            `${result.rules_repointed} rules repointed)`
        )
        await queryClient.invalidateQueries({ queryKey: ACCOUNT_QUERY_KEYS.all })
        await loadCandidates()
      } catch (error) {
        const detail =
          error && typeof error === 'object' && 'response' in error
            ? // eslint-disable-next-line @typescript-eslint/no-explicit-any
              ((error as any).response?.data?.detail as string | undefined)
            : undefined
        onFailed(detail ?? `Failed to convert "${candidate.name}"`)
      } finally {
        setConverting(null)
      }
    },
    [api.accounts, types, onConverted, onFailed, queryClient, loadCandidates]
  )

  if (candidates.length === 0) return null

  return (
    <Paper variant="outlined" sx={{ p: 2, mb: 2 }}>
      <Stack direction="row" justifyContent="space-between" alignItems="center">
        <Box>
          <Typography variant="subtitle1">
            {candidates.length} {candidates.length === 1 ? 'account' : 'accounts'} may really be counterparties
          </Typography>
          <Typography variant="body2" color="text.secondary">
            These accounts have no statements, transactions or balances of their own. If one is a person or company
            rather than an account of yours, convert it.
          </Typography>
        </Box>
        <Button onClick={() => setExpanded(!expanded)} sx={{ textTransform: 'none', flexShrink: 0 }}>
          {expanded ? 'Hide' : 'Review'}
        </Button>
      </Stack>

      <Collapse in={expanded}>
        <Alert severity="info" sx={{ mt: 2 }}>
          Converting moves every reference from the account to a counterparty of the same name, then deletes the
          account. Accounts that own statements, transactions or an initial balance cannot be converted.
        </Alert>

        <Table size="small" sx={{ mt: 1 }}>
          <TableHead>
            <TableRow>
              <TableCell>Account</TableCell>
              <TableCell align="right">Used as other side</TableCell>
              <TableCell sx={{ width: 160 }}>Type</TableCell>
              <TableCell align="right" sx={{ width: 120 }} />
            </TableRow>
          </TableHead>
          <TableBody>
            {candidates.map((candidate) => (
              <TableRow key={candidate.account_id}>
                <TableCell>{candidate.name}</TableCell>
                <TableCell align="right">{candidate.referenced_as_other_side}</TableCell>
                <TableCell>
                  <Select
                    size="small"
                    fullWidth
                    value={types[candidate.account_id] ?? 'other'}
                    onChange={(e) =>
                      setTypes((previous) => ({
                        ...previous,
                        [candidate.account_id]: e.target.value as CounterpartyType,
                      }))
                    }
                  >
                    {COUNTERPARTY_TYPES.map((type) => (
                      <MenuItem key={type} value={type}>
                        {COUNTERPARTY_TYPE_LABELS[type]}
                      </MenuItem>
                    ))}
                  </Select>
                </TableCell>
                <TableCell align="right">
                  <Button
                    size="small"
                    variant="outlined"
                    disabled={converting === candidate.account_id}
                    onClick={() => convert(candidate)}
                    sx={{ textTransform: 'none' }}
                  >
                    {converting === candidate.account_id ? 'Converting...' : 'Convert'}
                  </Button>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </Collapse>
    </Paper>
  )
}
