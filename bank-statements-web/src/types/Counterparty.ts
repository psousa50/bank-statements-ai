export type CounterpartyType = 'person' | 'company' | 'merchant' | 'other'

export const COUNTERPARTY_TYPES: CounterpartyType[] = ['person', 'company', 'merchant', 'other']

export const COUNTERPARTY_TYPE_LABELS: Record<CounterpartyType, string> = {
  person: 'Person',
  company: 'Company',
  merchant: 'Merchant',
  other: 'Other',
}

export interface Counterparty {
  id: string
  name: string
  type: CounterpartyType
}

export interface AccountConversionCandidate {
  account_id: string
  name: string
  referenced_as_other_side: number
}

export interface AccountConversionResult {
  counterparty: Counterparty
  transactions_repointed: number
  rules_repointed: number
}
