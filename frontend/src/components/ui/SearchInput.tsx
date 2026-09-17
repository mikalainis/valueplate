import type { InputHTMLAttributes } from 'react'
import './SearchInput.css'

type SearchInputProps = Omit<InputHTMLAttributes<HTMLInputElement>, 'type'>

export default function SearchInput({ className, ...props }: SearchInputProps) {
  return (
    <div className={['search-input', className].filter(Boolean).join(' ')}>
      <svg
        className="search-input-icon"
        width="18"
        height="18"
        viewBox="0 0 24 24"
        fill="none"
        aria-hidden="true"
      >
        <circle cx="11" cy="11" r="7" stroke="currentColor" strokeWidth="2" />
        <line x1="16.65" y1="16.65" x2="21" y2="21" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
      </svg>
      <input type="search" {...props} />
    </div>
  )
}
