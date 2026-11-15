import { Account } from '../types/Transaction'
import { Counterparty } from '../types/Counterparty'
import { AccountSelector } from './AccountSelector'
import { CounterpartySelector } from './CounterpartySelector'
import './OtherSideSelector.css'

export type OtherSideMode = 'none' | 'counterparty' | 'transfer'

export const otherSideModeFor = (counterpartyId?: string, transferAccountId?: string): OtherSideMode => {
  if (counterpartyId) return 'counterparty'
  if (transferAccountId) return 'transfer'
  return 'none'
}

interface OtherSideSelectorProps {
  mode: OtherSideMode
  onModeChange: (mode: OtherSideMode) => void
  accounts: Account[]
  counterparties: Counterparty[]
  counterpartyId?: string
  transferAccountId?: string
  onCounterpartyChange: (counterpartyId: string) => void
  onTransferAccountChange: (accountId: string) => void
  excludeAccountId?: string
}

export const OtherSideSelector = ({
  mode,
  onModeChange,
  accounts,
  counterparties,
  counterpartyId,
  transferAccountId,
  onCounterpartyChange,
  onTransferAccountChange,
  excludeAccountId,
}: OtherSideSelectorProps) => {
  const transferTargets = excludeAccountId ? accounts.filter((a) => a.id !== excludeAccountId) : accounts

  return (
    <div className="other-side-selector">
      <div className="other-side-selector__modes" role="radiogroup" aria-label="Other side of the transaction">
        {(
          [
            ['none', 'Not set'],
            ['counterparty', 'Counterparty'],
            ['transfer', 'My own account'],
          ] as const
        ).map(([value, label]) => (
          <label key={value} className="other-side-selector__mode">
            <input
              type="radio"
              name="other-side-mode"
              value={value}
              checked={mode === value}
              onChange={() => onModeChange(value)}
            />
            {label}
          </label>
        ))}
      </div>

      {mode === 'counterparty' && (
        <CounterpartySelector
          counterparties={counterparties}
          selectedCounterpartyId={counterpartyId}
          onCounterpartyChange={onCounterpartyChange}
          placeholder="Select the person or company"
        />
      )}

      {mode === 'transfer' && (
        <AccountSelector
          accounts={transferTargets}
          selectedAccountId={transferAccountId}
          onAccountChange={onTransferAccountChange}
          placeholder="Select your other account"
        />
      )}
    </div>
  )
}
