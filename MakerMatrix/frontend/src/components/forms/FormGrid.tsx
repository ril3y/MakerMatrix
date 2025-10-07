import type { ReactNode } from 'react'

interface FormGridProps {
  children: ReactNode
  columns?: 1 | 2 | 3 | 4
  className?: string
  gap?: 'sm' | 'md' | 'lg'
}

const FormGrid = ({ children, columns = 2, className, gap = 'md' }: FormGridProps) => {
  const gridColsClass = {
    1: 'grid-cols-1',
    2: 'grid-cols-1 md:grid-cols-2',
    3: 'grid-cols-1 md:grid-cols-2 lg:grid-cols-3',
    4: 'grid-cols-1 md:grid-cols-2 lg:grid-cols-4',
  }

  const gapClass = {
    sm: 'gap-3',
    md: 'gap-4',
    lg: 'gap-6',
  }

  return (
    <div
      className={`
      grid ${gridColsClass[columns]} ${gapClass[gap]}
      ${className || ''}
    `}
    >
      {children}
    </div>
  )
}

export default FormGrid
