import { Counterparty, COUNTERPARTY_TYPE_LABELS } from '../types/Counterparty'
import { StyledSelect } from './StyledSelect'

interface CounterpartySelectorProps {
  counterparties: Counterparty[]
  selectedCounterpartyId?: string
  onCounterpartyChange: (counterpartyId: string) => void
  placeholder?: string
}

export const CounterpartySelector = ({
  counterparties,
  selectedCounterpartyId,
  onCounterpartyChange,
  placeholder = 'Select a counterparty',
}: CounterpartySelectorProps) => {
  return (
    <div className="counterparty-selector">
      <StyledSelect
        value={selectedCounterpartyId || ''}
        onChange={onCounterpartyChange}
        placeholder={placeholder}
        options={counterparties.map((counterparty) => ({
          value: counterparty.id,
          label: `${counterparty.name} (${COUNTERPARTY_TYPE_LABELS[counterparty.type]})`,
        }))}
      />
    </div>
  )
}
