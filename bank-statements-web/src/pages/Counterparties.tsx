import { useState, useCallback, useRef } from 'react'
import { useCounterparties } from '../services/hooks/useCounterparties'
import { CounterpartyModal } from '../components/CounterpartyModal'
import { ConfirmationModal } from '../components/ConfirmationModal'
import { Toast, ToastProps } from '../components/Toast'
import { Counterparty, CounterpartyType, COUNTERPARTY_TYPE_LABELS } from '../types/Counterparty'
import { ActionIconButton } from '../components/ActionIconButton'
import { AccountConversionPanel } from '../components/AccountConversionPanel'
import EditIcon from '@mui/icons-material/Edit'
import DeleteIcon from '@mui/icons-material/Delete'
import AddIcon from '@mui/icons-material/Add'
import DownloadIcon from '@mui/icons-material/Download'
import UploadIcon from '@mui/icons-material/Upload'
import { Button } from '@mui/material'
import './AccountsPage.css'

export const CounterpartiesPage = () => {
  const [editingCounterparty, setEditingCounterparty] = useState<Counterparty | null>(null)
  const [isCreating, setIsCreating] = useState(false)
  const [searchTerm, setSearchTerm] = useState('')
  const [toast, setToast] = useState<Omit<ToastProps, 'onClose'> | null>(null)
  const [confirmDelete, setConfirmDelete] = useState<Counterparty | null>(null)
  const fileInputRef = useRef<HTMLInputElement>(null)

  const {
    counterparties,
    loading,
    error,
    addCounterparty,
    updateCounterparty,
    deleteCounterparty,
    exportCounterparties,
    uploadCounterparties,
    fetchCounterparties,
  } = useCounterparties()

  const filtered = counterparties.filter((c) => c.name.toLowerCase().includes(searchTerm.toLowerCase()))

  const handleConfirmDelete = useCallback(async () => {
    if (!confirmDelete) return

    const success = await deleteCounterparty(confirmDelete.id)
    setToast(
      success
        ? { message: `Counterparty "${confirmDelete.name}" deleted successfully`, type: 'success' }
        : {
            message: `Failed to delete "${confirmDelete.name}". It may still be used by transactions or rules.`,
            type: 'error',
          }
    )
    setConfirmDelete(null)
  }, [confirmDelete, deleteCounterparty])

  const handleSave = useCallback(
    async (name: string, type: CounterpartyType, counterpartyId?: string) => {
      const result = counterpartyId
        ? await updateCounterparty(counterpartyId, name, type)
        : await addCounterparty(name, type)

      if (result) {
        setToast({
          message: counterpartyId ? `Counterparty "${name}" updated` : `Counterparty "${name}" created`,
          type: 'success',
        })
        setIsCreating(false)
        setEditingCounterparty(null)
      } else {
        setToast({ message: `Failed to save counterparty "${name}"`, type: 'error' })
      }
    },
    [addCounterparty, updateCounterparty]
  )

  const handleExport = useCallback(async () => {
    const success = await exportCounterparties()
    setToast({
      message: success ? 'Counterparties exported successfully' : 'Failed to export counterparties',
      type: success ? 'success' : 'error',
    })
  }, [exportCounterparties])

  const handleFileChange = useCallback(
    async (event: React.ChangeEvent<HTMLInputElement>) => {
      const file = event.target.files?.[0]
      if (!file) return

      const result = await uploadCounterparties(file)
      setToast(
        result
          ? {
              message: `Uploaded ${result.total} counterparties (${result.created} created, ${result.updated} existing)`,
              type: 'success',
            }
          : { message: 'Failed to upload counterparties', type: 'error' }
      )

      if (fileInputRef.current) {
        fileInputRef.current.value = ''
      }
    },
    [uploadCounterparties]
  )

  return (
    <div className="accounts-page">
      <header className="page-header">
        <h1>Counterparty Management</h1>
        <p className="page-description">
          The people, companies and merchants you transact with. These are not your accounts.
        </p>
      </header>

      {error && (
        <div className="error-message">
          <strong>Error:</strong> {error}
        </div>
      )}

      <AccountConversionPanel
        onConverted={(message) => {
          setToast({ message, type: 'success' })
          fetchCounterparties()
        }}
        onFailed={(message) => setToast({ message, type: 'error' })}
      />

      <div className="filters-top">
        <div className="filter-section">
          <div className="search-container">
            <input
              type="text"
              placeholder="Search counterparties..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="search-input"
            />
          </div>
          <div className="action-buttons">
            <Button
              onClick={handleExport}
              variant="outlined"
              disabled={loading}
              startIcon={<DownloadIcon />}
              sx={{ textTransform: 'none' }}
            >
              Download
            </Button>
            <Button
              onClick={() => fileInputRef.current?.click()}
              variant="outlined"
              disabled={loading}
              startIcon={<UploadIcon />}
              sx={{ textTransform: 'none' }}
            >
              Upload
            </Button>
            <input
              type="file"
              ref={fileInputRef}
              onChange={handleFileChange}
              accept=".csv"
              style={{ display: 'none' }}
            />
            <Button
              onClick={() => setIsCreating(true)}
              variant="contained"
              disabled={loading}
              startIcon={<AddIcon />}
              sx={{ textTransform: 'none' }}
            >
              Create Counterparty
            </Button>
          </div>
        </div>
      </div>

      <div className="accounts-content">
        <div className="accounts-header">
          <h2>Counterparties</h2>
          {!loading && (
            <span className="account-count">
              {searchTerm ? `${filtered.length} of ${counterparties.length}` : counterparties.length} counterparties
            </span>
          )}
        </div>

        <div className="accounts-table-container">
          {loading ? (
            <div className="loading-message">Loading counterparties...</div>
          ) : filtered.length === 0 ? (
            <div className="empty-message">
              {searchTerm
                ? 'No counterparties found matching your search.'
                : 'No counterparties yet. Create one, or convert an account that is really a person or company.'}
            </div>
          ) : (
            <table className="accounts-table">
              <thead>
                <tr>
                  <th>Name</th>
                  <th style={{ width: '140px' }}>Type</th>
                  <th style={{ textAlign: 'center', width: '120px' }}>Actions</th>
                </tr>
              </thead>
              <tbody>
                {filtered.map((counterparty) => (
                  <tr key={counterparty.id}>
                    <td className="account-name">{counterparty.name}</td>
                    <td>{COUNTERPARTY_TYPE_LABELS[counterparty.type]}</td>
                    <td className="account-actions">
                      <ActionIconButton
                        onClick={() => setEditingCounterparty(counterparty)}
                        title="Edit counterparty"
                        icon={<EditIcon fontSize="small" />}
                        color="primary"
                      />
                      <ActionIconButton
                        onClick={() => setConfirmDelete(counterparty)}
                        title="Delete counterparty"
                        icon={<DeleteIcon fontSize="small" />}
                        color="error"
                      />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </div>

      <CounterpartyModal
        isOpen={isCreating || !!editingCounterparty}
        counterparty={editingCounterparty}
        onSave={handleSave}
        onClose={() => {
          setIsCreating(false)
          setEditingCounterparty(null)
        }}
      />

      <ConfirmationModal
        isOpen={!!confirmDelete}
        title="Delete Counterparty"
        message={`Are you sure you want to delete "${confirmDelete?.name}"? This action cannot be undone.`}
        confirmText="Delete"
        cancelText="Cancel"
        onConfirm={handleConfirmDelete}
        onCancel={() => setConfirmDelete(null)}
        dangerous={true}
      />

      {toast && <Toast message={toast.message} type={toast.type} onClose={() => setToast(null)} />}
    </div>
  )
}
