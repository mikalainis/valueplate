import type { ReactNode } from 'react'
import './PriceTag.css'

interface PriceTagProps {
  salePrice: number | null
  regularPrice?: number | null
  pricePerUnit?: string | null
}

type ParsedDeal =
  | { kind: 'multiBuy'; qty: number; total: number }
  | { kind: 'bogo'; label: string }
  | { kind: 'unit'; suffix: string }
  | { kind: 'raw'; text: string }
  | { kind: 'none' }

// The live shelf-tag field is overloaded: a per-unit suffix ("/LB."), a
// multi-buy ratio ("4/$5"), or a BOGO promo string all show up in the same
// field - see docs/existing-infrastructure.md §2.
const MULTI_BUY_RE = /^(\d+)\s*\/\s*\$\s*(\d+(?:\.\d+)?)$/
const BOGO_RE = /\bBUY\b.*\bFREE\b/i

function parseDeal(raw: string | null | undefined): ParsedDeal {
  const trimmed = raw?.trim()
  if (!trimmed) return { kind: 'none' }

  const multiBuy = trimmed.match(MULTI_BUY_RE)
  if (multiBuy) return { kind: 'multiBuy', qty: Number(multiBuy[1]), total: Number(multiBuy[2]) }

  if (BOGO_RE.test(trimmed)) return { kind: 'bogo', label: trimmed }

  if (trimmed.startsWith('/')) return { kind: 'unit', suffix: trimmed }

  return { kind: 'raw', text: trimmed }
}

const money = (n: number) => `$${n.toFixed(2)}`

export default function PriceTag({ salePrice, regularPrice, pricePerUnit }: PriceTagProps) {
  const deal = parseDeal(pricePerUnit)
  const hasRegular = regularPrice != null && salePrice != null && regularPrice > salePrice

  let primary: ReactNode = salePrice != null ? money(salePrice) : null
  let each: ReactNode = null

  if (deal.kind === 'multiBuy') {
    primary = `${deal.qty} for ${money(deal.total)}`
    const eachPrice = salePrice ?? deal.total / deal.qty
    each = `(${money(eachPrice)} each)`
  } else if (deal.kind === 'bogo') {
    primary = deal.label
    if (salePrice != null) each = `(${money(salePrice)} each)`
  }

  return (
    <div className="price-tag">
      <div className="price-tag-row">
        {primary != null && (
          <span className={`price-tag-sale${deal.kind === 'bogo' ? ' price-tag-sale--promo' : ''}`}>
            {primary}
          </span>
        )}
        {each && <span className="price-tag-each">{each}</span>}
      </div>
      {/* Fixed-height slots below keep card heights stable regardless of
          which fields a given item happens to have - see design feedback
          round 1 item 4. */}
      <span className="price-tag-regular-slot">
        {hasRegular && <span className="price-tag-regular">{money(regularPrice!)}</span>}
      </span>
      <span className="price-tag-unit-slot">
        {deal.kind === 'unit' && salePrice != null && (
          <span className="price-tag-unit">
            {money(salePrice)}
            {deal.suffix}
          </span>
        )}
        {deal.kind === 'raw' && <span className="price-tag-unit">{deal.text}</span>}
      </span>
    </div>
  )
}
