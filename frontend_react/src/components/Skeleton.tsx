import React from 'react'

interface SkeletonProps {
  className?: string
  style?: React.CSSProperties
}

/** A generic shimmer rectangle */
export function Skeleton({ className = '', style }: SkeletonProps) {
  return (
    <div className={`skeleton rounded-lg ${className}`} style={style} />
  )
}

/** Space page header skeleton */
export function SpaceHeaderSkeleton() {
  return (
    <div className="border-b border-white/5 bg-surface-900/80 backdrop-blur-sm">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 py-4">
        {/* Breadcrumb */}
        <div className="flex items-center gap-2 mb-3">
          <Skeleton className="h-3 w-20" />
          <Skeleton className="h-3 w-3" />
          <Skeleton className="h-3 w-16" />
        </div>
        {/* Title row */}
        <div className="flex items-center gap-3 mb-4">
          <Skeleton className="w-10 h-10 rounded-xl" />
          <div className="space-y-2">
            <Skeleton className="h-4 w-36" />
            <Skeleton className="h-3 w-24" />
          </div>
        </div>
        {/* Tab bar */}
        <div className="flex gap-2">
          {[80, 64, 80, 72, 72, 64].map((w, i) => (
            <Skeleton key={i} className="h-8 rounded-lg" style={{ width: w }} />
          ))}
        </div>
      </div>
    </div>
  )
}

/** Dashboard subject card skeleton */
export function SubjectCardSkeleton() {
  return (
    <div className="glass-card rounded-2xl p-5">
      <Skeleton className="w-12 h-12 rounded-xl mb-4" />
      <Skeleton className="h-4 w-24 mb-2" />
      <Skeleton className="h-3 w-32 mb-4" />
      <Skeleton className="h-7 w-full rounded-lg" />
    </div>
  )
}

/** Recent space list item skeleton */
export function SpaceListSkeleton() {
  return (
    <div className="glass-card rounded-xl p-4 flex items-center gap-3">
      <Skeleton className="w-10 h-10 rounded-xl flex-shrink-0" />
      <div className="flex-1 space-y-2">
        <Skeleton className="h-3.5 w-32" />
        <Skeleton className="h-3 w-24" />
      </div>
      <Skeleton className="h-7 w-20 rounded-lg" />
    </div>
  )
}

/** Chat message skeleton */
export function MessageSkeleton() {
  return (
    <div className="space-y-4">
      <div className="flex gap-3 justify-end">
        <div className="max-w-[70%] space-y-1">
          <Skeleton className="h-10 w-48 rounded-2xl" />
        </div>
        <Skeleton className="w-8 h-8 rounded-full flex-shrink-0" />
      </div>
      <div className="flex gap-3">
        <Skeleton className="w-8 h-8 rounded-full flex-shrink-0" />
        <div className="max-w-[80%] space-y-2">
          <Skeleton className="h-4 w-64" />
          <Skeleton className="h-4 w-48" />
          <Skeleton className="h-4 w-56" />
        </div>
      </div>
    </div>
  )
}
