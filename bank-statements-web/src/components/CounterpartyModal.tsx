import { useState, useEffect } from 'react'
import { Counterparty, CounterpartyType, COUNTERPARTY_TYPES, COUNTERPARTY_TYPE_LABELS } from '../types/Counterparty'
import { StyledSelect } from './StyledSelect'

interface CounterpartyModalProps {
  isOpen: boolean
  counterparty: Counterparty | null
  onSave: (name: string, type: CounterpartyType, counterpartyId?: string) => Promise<void>
  onClose: () => void
}

export const CounterpartyModal = ({ isOpen, counterparty, onSave, onClose }: CounterpartyModalProps) => {
  const [name, setName] = useState('')
  const [type, setType] = useState<CounterpartyType>('other')
  const [saving, setSaving] = useState(false)

  const isEditing = !!counterparty
  const title = isEditing ? 'Edit Counterparty' : 'Create Counterparty'

  useEffect(() => {
    if (isOpen) {
      setName(counterparty?.name ?? '')
      setType(counterparty?.type ?? 'other')
    }
  }, [isOpen, counterparty])

  if (!isOpen) return null

  const handleSave = async () => {
    const trimmedName = name.trim()
    if (!trimmedName) return

    setSaving(true)
    try {
      await onSave(trimmedName, type, counterparty?.id)
    } catch (error) {
      console.error('Failed to save counterparty:', error)
    } finally {
      setSaving(false)
    }
  }

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !saving && name.trim()) {
      handleSave()
    } else if (e.key === 'Escape') {
      onClose()
    }
  }

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <h2>{title}</h2>
          <button className="modal-close" onClick={onClose}>
            ×
          </button>
        </div>

        <div className="modal-body">
          <div className="form-group">
            <label htmlFor="counterparty-name" className="form-label">
              Name *
            </label>
            <input
              id="counterparty-name"
              type="text"
              className="form-input"
              value={name}
              onChange={(e) => setName(e.target.value)}
              onKeyDown={handleKeyPress}
              placeholder="Enter a person, company or merchant"
              disabled={saving}
              autoFocus
            />
          </div>
          <div className="form-group">
            <label htmlFor="counterparty-type" className="form-label">
              Type
            </label>
            <StyledSelect
              id="counterparty-type"
              value={type}
              onChange={(value) => setType(value as CounterpartyType)}
              disabled={saving}
              options={COUNTERPARTY_TYPES.map((t) => ({
                value: t,
                label: COUNTERPARTY_TYPE_LABELS[t],
              }))}
            />
          </div>
        </div>

        <div className="modal-footer">
          <button className="button-secondary" onClick={onClose} disabled={saving}>
            Cancel
          </button>
          <button className="button-primary" onClick={handleSave} disabled={saving || !name.trim()}>
            {saving ? 'Saving...' : isEditing ? 'Update Counterparty' : 'Create Counterparty'}
          </button>
        </div>
      </div>
    </div>
  )
}
