import React from 'react'
import { cn } from '@/lib/utils'

interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'primary' | 'secondary' | 'ghost' | 'destructive' | 'danger'
  size?: 'xs' | 'sm' | 'md' | 'lg'
  children: React.ReactNode
  className?: string
}

const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  ({ variant = 'primary', size = 'md', className, children, ...props }, ref) => {
    const baseClasses = 'btn'
    
    const variantClasses = {
      primary: 'btn-primary',
      secondary: 'btn-secondary', 
      ghost: 'btn-ghost',
      destructive: 'btn-destructive',
      danger: 'btn-danger'
    }
    
    const sizeClasses = {
      xs: 'btn-xs',
      sm: 'btn-sm',
      md: '', // Default size uses base btn padding
      lg: 'btn-lg'
    }
    
    const classes = cn(
      baseClasses,
      variantClasses[variant],
      sizeClasses[size],
      className
    )
    
    return (
      <button
        ref={ref}
        className={classes}
        {...props}
      >
        {children}
      </button>
    )
  }
)

Button.displayName = 'Button'

export { Button, type ButtonProps }