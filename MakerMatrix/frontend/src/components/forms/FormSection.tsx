import { ReactNode, useState } from 'react'
import { ChevronDown, ChevronRight } from 'lucide-react'

interface FormSectionProps {
  title: string
  description?: string
  children: ReactNode
  collapsible?: boolean
  defaultOpen?: boolean
  className?: string
  required?: boolean
}

const FormSection = ({
  title,
  description,
  children,
  collapsible = false,
  defaultOpen = true,
  className,
  required = false,
}: FormSectionProps) => {
  const [isOpen, setIsOpen] = useState(defaultOpen)

  const handleToggle = () => {
    if (collapsible) {
      setIsOpen(!isOpen)
    }
  }

  return (
    <div className={`space-y-4 ${className || ''}`}>
      <div
        className={`flex items-center justify-between ${collapsible ? 'cursor-pointer' : ''}`}
        onClick={handleToggle}
      >
        <div className="flex-1">
          <h3 className="text-lg font-medium text-primary flex items-center gap-2">
            {title}
            {required && <span className="text-red-500">*</span>}
          </h3>
          {description && <p className="text-sm text-secondary mt-1">{description}</p>}
        </div>
        {collapsible && (
          <div className="ml-2">
            {isOpen ? (
              <ChevronDown className="h-5 w-5 text-secondary" />
            ) : (
              <ChevronRight className="h-5 w-5 text-secondary" />
            )}
          </div>
        )}
      </div>

      {(!collapsible || isOpen) && <div className="space-y-4">{children}</div>}
    </div>
  )
}

export default FormSection
