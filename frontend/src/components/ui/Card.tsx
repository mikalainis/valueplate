import type { ElementType, ComponentPropsWithoutRef } from 'react'
import './Card.css'

type CardProps<T extends ElementType> = {
  as?: T
} & ComponentPropsWithoutRef<T>

export default function Card<T extends ElementType = 'div'>({ as, className, ...props }: CardProps<T>) {
  const Tag = as || 'div'
  const classes = ['ui-card', className].filter(Boolean).join(' ')
  return <Tag className={classes} {...props} />
}
