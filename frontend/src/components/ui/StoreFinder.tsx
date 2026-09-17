import { useState } from 'react'
import Button from './Button'
import './StoreFinder.css'

export interface StoreSearchResult {
  id: string
  deals_store_id: string | null
  name: string
  city: string | null
  state: string | null
  zip: string
  distance_miles: number
  has_deals: boolean
}

interface StoreSearchResponse {
  items: StoreSearchResult[]
}

interface StoreFinderProps {
  apiBase: string
  onSelect: (dealsStoreId: string) => void
  onClose: () => void
}

export default function StoreFinder({ apiBase, onSelect, onClose }: StoreFinderProps) {
  const [zip, setZip] = useState('')
  const [results, setResults] = useState<StoreSearchResult[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [requestedIds, setRequestedIds] = useState<Set<string>>(new Set())

  const handleSearch = async (e: React.FormEvent) => {
    e.preventDefault()
    if (zip.length !== 5) return
    setLoading(true)
    setError(null)
    try {
      const res = await fetch(`${apiBase}/api/stores/search?zip=${zip}`)
      if (!res.ok) {
        const body = await res.json().catch(() => null)
        throw new Error(body?.detail || `Search failed (${res.status})`)
      }
      const data: StoreSearchResponse = await res.json()
      setResults(data.items)
    } catch (err) {
      setResults([])
      setError(err instanceof Error ? err.message : 'Search failed')
    } finally {
      setLoading(false)
    }
  }

  const handleRequest = async (storeId: string) => {
    setRequestedIds((prev) => new Set(prev).add(storeId))
    try {
      await fetch(`${apiBase}/api/stores/request`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ store_id: storeId, zip }),
      })
    } catch {
      // Best-effort - the button already shows "Requested" optimistically;
      // worst case we just don't learn about this one request.
    }
  }

  return (
    <div className="store-finder">
      <div className="store-finder-header">
        <h2>Find your store</h2>
        <button type="button" className="store-finder-close" onClick={onClose} aria-label="Close">
          ×
        </button>
      </div>

      <form className="store-finder-form" onSubmit={handleSearch}>
        <input
          type="text"
          inputMode="numeric"
          placeholder="Zip code"
          value={zip}
          onChange={(e) => setZip(e.target.value.replace(/\D/g, '').slice(0, 5))}
          aria-label="Zip code"
        />
        <Button type="submit" disabled={zip.length !== 5 || loading}>
          {loading ? 'Searching…' : 'Search'}
        </Button>
      </form>

      {error && <p className="store-finder-error">{error}</p>}

      {results.length > 0 && (
        <ul className="store-finder-results">
          {results.map((r) => (
            <li key={r.id} className="store-finder-result">
              <div className="store-finder-result-info">
                <span className="store-finder-result-name">{r.name}</span>
                <span className="store-finder-result-meta">
                  {r.city ? `${r.city}${r.state ? `, ${r.state}` : ''} · ` : ''}
                  {r.distance_miles} mi
                </span>
              </div>
              {r.has_deals && r.deals_store_id ? (
                <Button variant="secondary" onClick={() => onSelect(r.deals_store_id!)}>
                  Select
                </Button>
              ) : requestedIds.has(r.id) ? (
                <span className="store-finder-requested">Requested ✓</span>
              ) : (
                <div className="store-finder-unavailable">
                  <span className="store-finder-unavailable-label">Not yet available</span>
                  <button
                    type="button"
                    className="store-finder-request-btn"
                    onClick={() => handleRequest(r.id)}
                  >
                    Request this store
                  </button>
                </div>
              )}
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}
