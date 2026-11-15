import { useCallback } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Counterparty, CounterpartyType } from '../../types/Counterparty'
import { useApi } from '../../api/ApiContext'
import { getErrorMessage } from '../../types/ApiError'

const sortByName = (counterparties: Counterparty[]) => [...counterparties].sort((a, b) => a.name.localeCompare(b.name))

export const COUNTERPARTY_QUERY_KEYS = {
  all: ['counterparties'] as const,
}

export const useCounterparties = () => {
  const api = useApi()
  const queryClient = useQueryClient()

  const counterpartiesQuery = useQuery({
    queryKey: COUNTERPARTY_QUERY_KEYS.all,
    queryFn: async () => sortByName(await api.counterparties.getAll()),
  })

  const addMutation = useMutation({
    mutationFn: ({ name, type }: { name: string; type: CounterpartyType }) =>
      api.counterparties.createCounterparty(name, type),
    onSuccess: (created) => {
      queryClient.setQueryData<Counterparty[]>(COUNTERPARTY_QUERY_KEYS.all, (old) =>
        sortByName([...(old ?? []), created])
      )
    },
  })

  const updateMutation = useMutation({
    mutationFn: ({ id, name, type }: { id: string; name: string; type: CounterpartyType }) =>
      api.counterparties.updateCounterparty(id, name, type),
    onSuccess: (updated) => {
      queryClient.setQueryData<Counterparty[]>(COUNTERPARTY_QUERY_KEYS.all, (old) =>
        sortByName((old ?? []).map((c) => (c.id === updated.id ? updated : c)))
      )
    },
  })

  const deleteMutation = useMutation({
    mutationFn: async (id: string) => {
      await api.counterparties.deleteCounterparty(id)
      return id
    },
    onSuccess: (deletedId) => {
      queryClient.setQueryData<Counterparty[]>(COUNTERPARTY_QUERY_KEYS.all, (old) =>
        (old ?? []).filter((c) => c.id !== deletedId)
      )
    },
  })

  const addCounterparty = useCallback(
    async (name: string, type: CounterpartyType): Promise<Counterparty | null> => {
      try {
        return await addMutation.mutateAsync({ name, type })
      } catch {
        return null
      }
    },
    [addMutation]
  )

  const updateCounterparty = useCallback(
    async (id: string, name: string, type: CounterpartyType): Promise<Counterparty | null> => {
      try {
        return await updateMutation.mutateAsync({ id, name, type })
      } catch {
        return null
      }
    },
    [updateMutation]
  )

  const deleteCounterparty = useCallback(
    async (id: string): Promise<boolean> => {
      try {
        await deleteMutation.mutateAsync(id)
        return true
      } catch {
        return false
      }
    },
    [deleteMutation]
  )

  const exportCounterparties = useCallback(async (): Promise<boolean> => {
    try {
      await api.counterparties.exportCounterparties()
      return true
    } catch {
      return false
    }
  }, [api.counterparties])

  const uploadCounterparties = useCallback(
    async (file: File) => {
      try {
        const result = await api.counterparties.uploadCounterparties(file)
        await queryClient.invalidateQueries({ queryKey: COUNTERPARTY_QUERY_KEYS.all })
        return result
      } catch {
        return null
      }
    },
    [api.counterparties, queryClient]
  )

  const loading =
    counterpartiesQuery.isLoading || addMutation.isPending || updateMutation.isPending || deleteMutation.isPending

  const firstError = counterpartiesQuery.error || addMutation.error || updateMutation.error || deleteMutation.error

  return {
    counterparties: counterpartiesQuery.data ?? [],
    loading,
    error: firstError ? getErrorMessage(firstError) : null,
    fetchCounterparties: () => queryClient.invalidateQueries({ queryKey: COUNTERPARTY_QUERY_KEYS.all }),
    addCounterparty,
    updateCounterparty,
    deleteCounterparty,
    exportCounterparties,
    uploadCounterparties,
  }
}
