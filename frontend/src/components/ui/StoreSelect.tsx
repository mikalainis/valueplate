import './StoreSelect.css'

export interface StoreOption {
  id: string
  label: string
}

interface StoreSelectProps {
  value: string
  options: StoreOption[]
  onChange: (id: string) => void
}

export default function StoreSelect({ value, options, onChange }: StoreSelectProps) {
  return (
    <label className="store-select">
      <span className="store-select-icon" aria-hidden="true">
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none">
          <path
            d="M12 21s-7-6.3-7-11a7 7 0 1 1 14 0c0 4.7-7 11-7 11Z"
            stroke="currentColor"
            strokeWidth="2"
            strokeLinejoin="round"
          />
          <circle cx="12" cy="10" r="2.5" stroke="currentColor" strokeWidth="2" />
        </svg>
      </span>
      <select
        className="store-select-input"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        aria-label="Select store"
      >
        {options.map((opt) => (
          <option key={opt.id} value={opt.id}>
            {opt.label}
          </option>
        ))}
      </select>
    </label>
  )
}
