import './CategoryPill.css'

interface CategoryPillProps {
  label: string
  active?: boolean
  onClick: () => void
}

export default function CategoryPill({ label, active, onClick }: CategoryPillProps) {
  return (
    <button
      type="button"
      className={`category-pill${active ? ' category-pill--active' : ''}`}
      aria-pressed={active}
      onClick={onClick}
    >
      {label}
    </button>
  )
}
