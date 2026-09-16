import { useEffect, useMemo, useState } from 'react'
import './DealsPage.css'

const API_BASE = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'
const PAGE_SIZE = 200

interface DealItem {
  id: string
  name: string
  brand: string | null
  category: string | null
  store_id: string | null
  sale_price: number | null
  regular_price: number | null
  unit: string | null
  price_per_unit: string | null
  image_url: string | null
  valid_from: string | null
  valid_to: string | null
}

interface DealsResponse {
  items: DealItem[]
  total: number
  as_of: string | null
}

const UNCATEGORIZED = 'Uncategorized'

// The dataset is small (a few hundred rows) so we page through the whole
// thing once on load and do filtering/grouping client-side from there.
async function fetchAllDeals(): Promise<{ items: DealItem[]; asOf: string | null }> {
  let offset = 0
  let all: DealItem[] = []
  let asOf: string | null = null

  for (;;) {
    const res = await fetch(`${API_BASE}/api/deals?limit=${PAGE_SIZE}&offset=${offset}`)
    if (!res.ok) throw new Error(`Failed to load deals (${res.status})`)
    const data: DealsResponse = await res.json()
    all = all.concat(data.items)
    asOf = data.as_of
    offset += PAGE_SIZE
    if (data.items.length === 0 || offset >= data.total) break
  }

  return { items: all, asOf }
}

export default function DealsPage() {
  const [items, setItems] = useState<DealItem[]>([])
  const [asOf, setAsOf] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [category, setCategory] = useState('all')
  const [search, setSearch] = useState('')

  useEffect(() => {
    let cancelled = false
    setLoading(true)
    fetchAllDeals()
      .then(({ items, asOf }) => {
        if (cancelled) return
        setItems(items)
        setAsOf(asOf)
        setError(null)
      })
      .catch((err: Error) => {
        if (!cancelled) setError(err.message)
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })
    return () => {
      cancelled = true
    }
  }, [])

  const categories = useMemo(() => {
    const set = new Set<string>()
    items.forEach((item) => set.add(item.category || UNCATEGORIZED))
    return Array.from(set).sort()
  }, [items])

  const filtered = useMemo(() => {
    const needle = search.trim().toLowerCase()
    return items.filter((item) => {
      const itemCategory = item.category || UNCATEGORIZED
      if (category !== 'all' && itemCategory !== category) return false
      if (needle && !item.name.toLowerCase().includes(needle)) return false
      return true
    })
  }, [items, category, search])

  const grouped = useMemo(() => {
    const map = new Map<string, DealItem[]>()
    filtered.forEach((item) => {
      const key = item.category || UNCATEGORIZED
      if (!map.has(key)) map.set(key, [])
      map.get(key)!.push(item)
    })
    return Array.from(map.entries()).sort(([a], [b]) => a.localeCompare(b))
  }, [filtered])

  if (loading) {
    return <div className="deals-status">Loading this week's deals…</div>
  }

  if (error) {
    return <div className="deals-status deals-status--error">Couldn't load deals: {error}</div>
  }

  return (
    <div className="deals-page">
      <header className="deals-header">
        <h1>This Week's ShopRite Deals</h1>
        {asOf && (
          <p className="deals-asof">
            Prices as of{' '}
            {new Date(asOf).toLocaleDateString(undefined, {
              year: 'numeric',
              month: 'long',
              day: 'numeric',
            })}
          </p>
        )}
      </header>

      <div className="deals-controls">
        <input
          type="search"
          placeholder="Search deals…"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          aria-label="Search deals"
        />
        <select
          value={category}
          onChange={(e) => setCategory(e.target.value)}
          aria-label="Filter by category"
        >
          <option value="all">All categories</option>
          {categories.map((c) => (
            <option key={c} value={c}>
              {c}
            </option>
          ))}
        </select>
      </div>

      {grouped.length === 0 && <p className="deals-empty">No deals match your search.</p>}

      {grouped.map(([categoryName, categoryItems]) => (
        <section key={categoryName} className="deals-category">
          <h2>{categoryName}</h2>
          <div className="deals-grid">
            {categoryItems.map((item) => (
              <article key={item.id} className="deal-card">
                <h3>{item.name}</h3>
                <div className="deal-card-price">
                  {item.sale_price != null && (
                    <span className="deal-card-price-sale">${item.sale_price.toFixed(2)}</span>
                  )}
                  {item.price_per_unit && (
                    <span className="deal-card-price-unit">{item.price_per_unit}</span>
                  )}
                </div>
                {item.store_id && <div className="deal-card-store">Store #{item.store_id}</div>}
              </article>
            ))}
          </div>
        </section>
      ))}
    </div>
  )
}
