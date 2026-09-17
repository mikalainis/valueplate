import type { ReactElement } from 'react'
import './BottomNav.css'

interface NavItem {
  key: string
  label: string
  icon: ReactElement
  available: boolean
}

const ICON_PROPS = {
  width: 22,
  height: 22,
  viewBox: '0 0 24 24',
  fill: 'none',
  'aria-hidden': true,
} as const

const ITEMS: NavItem[] = [
  {
    key: 'deals',
    label: 'Deals',
    available: true,
    icon: (
      <svg {...ICON_PROPS}>
        <path
          d="M20 12 12.6 3.6a2 2 0 0 0-1.5-.6H5a2 2 0 0 0-2 2v6.1c0 .5.2 1 .6 1.4l8.4 8.4a2 2 0 0 0 2.8 0l5.2-5.2a2 2 0 0 0 0-2.8Z"
          stroke="currentColor"
          strokeWidth="2"
          strokeLinejoin="round"
        />
        <circle cx="8" cy="8" r="1.5" fill="currentColor" />
      </svg>
    ),
  },
  {
    key: 'recipes',
    label: 'Recipes',
    available: false,
    icon: (
      <svg {...ICON_PROPS}>
        <path
          d="M5 4h11a2 2 0 0 1 2 2v14l-7.5-3L3 20V6a2 2 0 0 1 2-2Z"
          stroke="currentColor"
          strokeWidth="2"
          strokeLinejoin="round"
        />
      </svg>
    ),
  },
  {
    key: 'list',
    label: 'List',
    available: false,
    icon: (
      <svg {...ICON_PROPS}>
        <path d="M9 6h11M9 12h11M9 18h11" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
        <path
          d="m4 6 .8.8L6.5 5"
          stroke="currentColor"
          strokeWidth="2"
          strokeLinecap="round"
          strokeLinejoin="round"
        />
        <path
          d="m4 12 .8.8L6.5 11"
          stroke="currentColor"
          strokeWidth="2"
          strokeLinecap="round"
          strokeLinejoin="round"
        />
        <path
          d="m4 18 .8.8L6.5 17"
          stroke="currentColor"
          strokeWidth="2"
          strokeLinecap="round"
          strokeLinejoin="round"
        />
      </svg>
    ),
  },
]

interface BottomNavProps {
  active?: string
}

export default function BottomNav({ active = 'deals' }: BottomNavProps) {
  return (
    <nav className="bottom-nav" aria-label="Primary">
      {ITEMS.map((item) => (
        <button
          key={item.key}
          type="button"
          className={`bottom-nav-item${item.key === active ? ' bottom-nav-item--active' : ''}`}
          disabled={!item.available}
          aria-current={item.key === active ? 'page' : undefined}
        >
          {item.icon}
          <span>{item.label}</span>
          {!item.available && <span className="bottom-nav-soon">Soon</span>}
        </button>
      ))}
    </nav>
  )
}
