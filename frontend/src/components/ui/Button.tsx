import type { ButtonHTMLAttributes } from 'react'
import './Button.css'

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'primary' | 'secondary' | 'ghost'
}

export default function Button({ variant = 'primary', className, ...props }: ButtonProps) {
  const classes = ['ui-btn', `ui-btn--${variant}`, className].filter(Boolean).join(' ')
  return <button type="button" className={classes} {...props} />
}
