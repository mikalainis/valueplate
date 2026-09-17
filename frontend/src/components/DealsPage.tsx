import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import './DealsPage.css'
import Card from './ui/Card'
import PriceTag from './ui/PriceTag'
import CategoryPill from './ui/CategoryPill'
import SearchInput from './ui/SearchInput'
import StoreSelect, { type StoreOption } from './ui/StoreSelect'
import StoreFinder from './ui/StoreFinder'
import EmptyState from './ui/EmptyState'
import Button from './ui/Button'
import { DealsGridSkeleton } from './ui/Skeleton'

const API_BASE = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000'
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

interface StoreItem {
  id: string
  name: string | null
  city: string | null
  state: string | null
}

interface StoresResponse {
  items: StoreItem[]
}

const UNCATEGORIZED = 'Uncategorized'
const STORE_STORAGE_KEY = 'valueplate:selectedStore'

function storeLabel(store: StoreItem): string {
  const name = store.name || `Store #${store.id}`
  // Most store names already are "ShopRite of {town}" - only append the town
  // separately when it isn't already part of the name.
  if (store.city && !name.toLowerCase().includes(store.city.toLowerCase())) {
    return `${name} — ${store.city}`
  }
  return name
}

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

async function fetchStores(): Promise<StoreItem[]> {
  const res = await fetch(`${API_BASE}/api/stores`)
  if (!res.ok) throw new Error(`Failed to load stores (${res.status})`)
  const data: StoresResponse = await res.json()
  return data.items
}

export default function DealsPage() {
  const [items, setItems] = useState<DealItem[]>([])
  const [asOf, setAsOf] = useState<string | null>(null)
  const [stores, setStores] = useState<StoreItem[]>([])
  const [selectedStore, setSelectedStore] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [category, setCategory] = useState('all')
  const [search, setSearch] = useState('')

  useEffect(() => {
    let cancelled = false
    setLoading(true)
    // Store names come from a separate, less critical lookup - if it fails,
    // fall back to deriving bare store ids from the deals data itself rather
    // than failing the whole page.
    Promise.all([fetchAllDeals(), fetchStores().catch(() => [])])
      .then(([{ items, asOf }, storeItems]) => {
        if (cancelled) return
        setItems(items)
        setAsOf(asOf)
        setStores(storeItems)
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

  const storeOptions = useMemo<StoreOption[]>(() => {
    if (stores.length > 0) {
      return stores.map((s) => ({ id: s.id, label: storeLabel(s) }))
    }
    const ids = new Set<string>()
    items.forEach((item) => {
      if (item.store_id) ids.add(item.store_id)
    })
    return Array.from(ids)
      .sort()
      .map((id) => ({ id, label: `Store #${id}` }))
  }, [stores, items])

  useEffect(() => {
    if (selectedStore !== null) return
    if (storeOptions.length === 0) return
    const saved = localStorage.getItem(STORE_STORAGE_KEY)
    const initial = saved && storeOptions.some((s) => s.id === saved) ? saved : storeOptions[0].id
    setSelectedStore(initial)
  }, [storeOptions, selectedStore])

  const persistStore = (id: string) => {
    setSelectedStore(id)
    localStorage.setItem(STORE_STORAGE_KEY, id)
  }

  const categories = useMemo(() => {
    const set = new Set<string>()
    items.forEach((item) => {
      if (selectedStore && item.store_id !== selectedStore) return
      set.add(item.category || UNCATEGORIZED)
    })
    return Array.from(set).sort()
  }, [items, selectedStore])

  const filtered = useMemo(() => {
    const needle = search.trim().toLowerCase()
    return items.filter((item) => {
      if (selectedStore && item.store_id !== selectedStore) return false
      const itemCategory = item.category || UNCATEGORIZED
      if (category !== 'all' && itemCategory !== category) return false
      if (needle && !item.name.toLowerCase().includes(needle)) return false
      return true
    })
  }, [items, selectedStore, category, search])

  const grouped = useMemo(() => {
    const map = new Map<string, DealItem[]>()
    filtered.forEach((item) => {
      const key = item.category || UNCATEGORIZED
      if (!map.has(key)) map.set(key, [])
      map.get(key)!.push(item)
    })
    return Array.from(map.entries()).sort(([a], [b]) => a.localeCompare(b))
  }, [filtered])

  const clearFilters = () => {
    setSearch('')
    setCategory('all')
  }

  const handleStoreChange = (id: string) => {
    persistStore(id)
    setCategory('all')
  }

  const [finderOpen, setFinderOpen] = useState(false)

  const handleFinderSelect = (dealsStoreId: string) => {
    handleStoreChange(dealsStoreId)
    setFinderOpen(false)
  }

  const pillsRef = useRef<HTMLDivElement>(null)
  const [scrollState, setScrollState] = useState({ left: false, right: false })

  const updateScrollState = useCallback(() => {
    const el = pillsRef.current
    if (!el) return
    setScrollState({
      left: el.scrollLeft > 4,
      right: el.scrollLeft + el.clientWidth < el.scrollWidth - 4,
    })
  }, [])

  useEffect(() => {
    updateScrollState()
    window.addEventListener('resize', updateScrollState)
    return () => window.removeEventListener('resize', updateScrollState)
  }, [categories, updateScrollState])

  return (
    <div className="deals-page">
      <div className="deals-sticky-bar">
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

        <div className="deals-store-row">
          {storeOptions.length > 0 && selectedStore && (
            <StoreSelect value={selectedStore} options={storeOptions} onChange={handleStoreChange} />
          )}
          <button
            type="button"
            className="deals-find-store-btn"
            onClick={() => setFinderOpen((open) => !open)}
          >
            {finderOpen ? 'Cancel' : 'Find your store'}
          </button>
        </div>

        {finderOpen && (
          <StoreFinder apiBase={API_BASE} onSelect={handleFinderSelect} onClose={() => setFinderOpen(false)} />
        )}

        <SearchInput
          placeholder="Search deals…"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          aria-label="Search deals"
        />

        {categories.length > 0 && (
          <div
            className={`deals-category-scroll${scrollState.left ? ' can-scroll-left' : ''}${
              scrollState.right ? ' can-scroll-right' : ''
            }`}
          >
            <div
              className="deals-category-pills"
              role="group"
              aria-label="Filter by category"
              ref={pillsRef}
              onScroll={updateScrollState}
            >
              <CategoryPill label="All" active={category === 'all'} onClick={() => setCategory('all')} />
              {categories.map((c) => (
                <CategoryPill key={c} label={c} active={category === c} onClick={() => setCategory(c)} />
              ))}
            </div>
          </div>
        )}
      </div>

      <div className="deals-content">
        {loading && <DealsGridSkeleton />}

        {!loading && error && (
          <EmptyState
            tone="error"
            title="Couldn't load deals"
            message={error}
            action={
              <Button variant="secondary" onClick={() => window.location.reload()}>
                Try again
              </Button>
            }
          />
        )}

        {!loading && !error && grouped.length === 0 && (
          <EmptyState
            title="No deals match your search"
            message="Try a different search term or clear the category filter."
            action={
              <Button variant="secondary" onClick={clearFilters}>
                Clear filters
              </Button>
            }
          />
        )}

        {!loading &&
          !error &&
          grouped.map(([categoryName, categoryItems]) => (
            <section key={categoryName} className="deals-category">
              <h2>{categoryName}</h2>
              <div className="deals-grid">
                {categoryItems.map((item) => {
                  const percentOff =
                    item.sale_price != null && item.regular_price != null && item.regular_price > item.sale_price
                      ? Math.round((1 - item.sale_price / item.regular_price) * 100)
                      : null
                  return (
                    <Card as="article" key={item.id} className="deal-card">
                      {/* Absolutely positioned so a missing badge never reflows
                          the card - see design feedback round 1 item 4. */}
                      <div className="deal-card-badge-slot">
                        {percentOff != null && percentOff > 0 && (
                          <span className="price-tag-badge">-{percentOff}%</span>
                        )}
                      </div>
                      <h3>{item.name}</h3>
                      <PriceTag
                        salePrice={item.sale_price}
                        regularPrice={item.regular_price}
                        pricePerUnit={item.price_per_unit}
                      />
                    </Card>
                  )
                })}
              </div>
            </section>
          ))}
      </div>
    </div>
  )
}
