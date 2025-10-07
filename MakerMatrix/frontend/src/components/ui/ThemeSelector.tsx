import { useState, useEffect } from 'react'
import { Palette, Check, Monitor, Sun, Moon, Laptop } from 'lucide-react'
import { useTheme } from '@/contexts/ThemeContext'

interface Theme {
  id: string
  name: string
  description: string
  icon: any
  primary: string
  background: string
  text: string
  preview: {
    bg: string
    card: string
    text: string
    accent: string
  }
}

const themes: Theme[] = [
  {
    id: 'default',
    name: 'Matrix',
    description: 'Cyberpunk tech with monospace fonts',
    icon: Palette,
    primary: '#00ff9d',
    background: '#ffffff',
    text: '#111827',
    preview: {
      bg: 'bg-white',
      card: 'bg-gray-50',
      text: 'text-gray-900',
      accent: 'bg-primary',
    },
  },
  {
    id: 'blue',
    name: 'Arctic',
    description: 'Clean modern with Inter fonts',
    icon: Palette,
    primary: '#3b82f6',
    background: '#ffffff',
    text: '#111827',
    preview: {
      bg: 'bg-white',
      card: 'bg-gray-50',
      text: 'text-gray-900',
      accent: 'bg-primary',
    },
  },
  {
    id: 'purple',
    name: 'Nebula',
    description: 'Creative with serif display fonts',
    icon: Palette,
    primary: '#8b5cf6',
    background: '#ffffff',
    text: '#111827',
    preview: {
      bg: 'bg-white',
      card: 'bg-gray-50',
      text: 'text-gray-900',
      accent: 'bg-primary',
    },
  },
  {
    id: 'orange',
    name: 'Sunset',
    description: 'Warm friendly with clean fonts',
    icon: Palette,
    primary: '#f59e0b',
    background: '#ffffff',
    text: '#111827',
    preview: {
      bg: 'bg-white',
      card: 'bg-gray-50',
      text: 'text-gray-900',
      accent: 'bg-primary',
    },
  },
  {
    id: 'gray',
    name: 'Monolith',
    description: 'Professional with system fonts',
    icon: Palette,
    primary: '#6b7280',
    background: '#ffffff',
    text: '#111827',
    preview: {
      bg: 'bg-white',
      card: 'bg-gray-50',
      text: 'text-gray-900',
      accent: 'bg-primary',
    },
  },
]

interface ThemeSelectorProps {
  currentTheme?: string
  onThemeChange?: (themeId: string) => void
}

const ThemeSelector = ({
  currentTheme: propCurrentTheme,
  onThemeChange: propOnThemeChange,
}: ThemeSelectorProps = {}) => {
  const themeContext = useTheme()
  const { currentTheme: contextTheme, setTheme } = themeContext || {
    currentTheme: 'default',
    setTheme: () => {},
  }

  // Use props if provided, otherwise use context
  const currentTheme = propCurrentTheme ?? contextTheme
  const onThemeChange = propOnThemeChange ?? setTheme

  const [selectedTheme, setSelectedTheme] = useState(currentTheme)

  // Update local state when currentTheme changes
  useEffect(() => {
    setSelectedTheme(currentTheme)
  }, [currentTheme])

  const handleThemeSelect = (themeId: string) => {
    setSelectedTheme(themeId)
    onThemeChange(themeId)
  }

  return (
    <div className="space-y-4">
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
        {themes.map((theme) => (
          <button
            key={theme.id}
            onClick={() => handleThemeSelect(theme.id)}
            className={`relative p-4 rounded-lg border-2 transition-all hover:shadow-md bg-theme-primary ${
              selectedTheme === theme.id
                ? 'border-primary shadow-md ring-2 ring-primary-20'
                : 'border-theme-primary hover:border-theme-secondary'
            }`}
          >
            {/* Check mark for selected theme */}
            {selectedTheme === theme.id && (
              <div className="absolute top-2 right-2 w-6 h-6 bg-primary rounded-full flex items-center justify-center">
                <Check className="w-4 h-4 text-white" />
              </div>
            )}

            {/* Theme preview */}
            <div className="mb-3">
              <div
                className={`w-full h-20 rounded-lg bg-theme-primary border border-theme-primary overflow-hidden`}
              >
                <div className="flex h-full">
                  {/* Sidebar preview */}
                  <div className={`w-1/3 bg-theme-secondary border-r border-theme-primary p-2`}>
                    <div
                      className="h-2 rounded mb-1"
                      style={{ backgroundColor: theme.primary }}
                    ></div>
                    <div className="h-1 bg-theme-tertiary rounded mb-1"></div>
                    <div className="h-1 bg-theme-tertiary rounded w-3/4"></div>
                  </div>
                  {/* Main content preview */}
                  <div className="flex-1 p-2">
                    <div className="h-1 bg-theme-tertiary rounded mb-2"></div>
                    <div className="h-1 bg-theme-tertiary rounded mb-1 w-4/5"></div>
                    <div className="h-1 bg-theme-tertiary rounded w-2/3"></div>
                    <div
                      className="h-4 rounded mt-2 w-1/2"
                      style={{ backgroundColor: theme.primary }}
                    ></div>
                  </div>
                </div>
              </div>
            </div>

            {/* Theme info */}
            <div className="text-left">
              <h4 className="font-semibold text-theme-primary">{theme.name}</h4>
              <p className="text-sm text-theme-secondary">{theme.description}</p>
            </div>
          </button>
        ))}
      </div>

      {/* Color preview for selected theme */}
      <div className="p-4 bg-theme-secondary rounded-lg">
        <h4 className="font-medium text-theme-primary mb-3">Theme Colors</h4>
        <div className="flex items-center gap-4">
          <div className="flex items-center gap-2">
            <div
              className="w-8 h-8 rounded-full border border-theme-primary"
              style={{ backgroundColor: themes.find((t) => t.id === selectedTheme)?.primary }}
            ></div>
            <span className="text-sm text-theme-secondary">Primary</span>
          </div>
          <div className="flex items-center gap-2">
            <div
              className="w-8 h-8 rounded-full border border-theme-primary"
              style={{ backgroundColor: themes.find((t) => t.id === selectedTheme)?.background }}
            ></div>
            <span className="text-sm text-theme-secondary">Background</span>
          </div>
          <div className="flex items-center gap-2">
            <div
              className="w-8 h-8 rounded-full border border-theme-primary"
              style={{ backgroundColor: themes.find((t) => t.id === selectedTheme)?.text }}
            ></div>
            <span className="text-sm text-theme-secondary">Text</span>
          </div>
        </div>
      </div>
    </div>
  )
}

export default ThemeSelector
