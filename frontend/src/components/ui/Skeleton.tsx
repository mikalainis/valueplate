import './Skeleton.css'

export function DealCardSkeleton() {
  return (
    <div className="ui-card skeleton-card" aria-hidden="true">
      <div className="skeleton-block skeleton-title" />
      <div className="skeleton-block skeleton-title skeleton-title--short" />
      <div className="skeleton-block skeleton-price" />
    </div>
  )
}

export function DealsGridSkeleton({ count = 8 }: { count?: number }) {
  return (
    <div className="deals-grid" role="status" aria-label="Loading deals">
      {Array.from({ length: count }).map((_, i) => (
        <DealCardSkeleton key={i} />
      ))}
    </div>
  )
}
