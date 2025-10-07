import type { ReactNode } from 'react'
import React, { createContext, useContext, useState, useEffect } from 'react'
import { useDarkMode } from '@/hooks/useDarkMode'

interface ThemeContextType {
  isDarkMode: boolean
  toggleDarkMode: () => void
  currentTheme: string
  setTheme: (themeId: string) => void
  isCompactMode: boolean
  toggleCompactMode: () => void
}

const ThemeContext = createContext<ThemeContextType | undefined>(undefined)

const availableThemes = ['default', 'blue', 'purple', 'orange', 'gray']

export const ThemeProvider: React.FC<{ children: ReactNode }> = ({ children }) => {
  const { isDarkMode, toggleDarkMode } = useDarkMode()
  const [currentTheme, setCurrentTheme] = useState('default')
  const [isCompactMode, setIsCompactMode] = useState(false)

  useEffect(() => {
    // Load theme and settings from localStorage on mount
    const savedTheme = localStorage.getItem('makermatrix-theme')
    if (savedTheme && availableThemes.includes(savedTheme)) {
      setCurrentTheme(savedTheme)
    }

    const savedCompactMode = localStorage.getItem('makermatrix-compact-mode')
    if (savedCompactMode === 'true') {
      setIsCompactMode(true)
    }
  }, [])

  useEffect(() => {
    // Remove any existing theme classes
    document.documentElement.className = document.documentElement.className
      .replace(/theme-\w+/g, '')
      .trim()

    // Add new theme class
    document.documentElement.classList.add(`theme-${currentTheme}`)

    // Set data attribute for CSS selectors
    document.documentElement.setAttribute('data-theme', currentTheme)

    console.log('Theme applied:', currentTheme)
  }, [currentTheme])

  useEffect(() => {
    // Apply compact mode class
    if (isCompactMode) {
      document.documentElement.classList.add('compact-mode')
    } else {
      document.documentElement.classList.remove('compact-mode')
    }
  }, [isCompactMode])

  const setTheme = (themeId: string) => {
    if (availableThemes.includes(themeId)) {
      setCurrentTheme(themeId)
      localStorage.setItem('makermatrix-theme', themeId)
    }
  }

  const toggleCompactMode = () => {
    const newCompactMode = !isCompactMode
    setIsCompactMode(newCompactMode)
    localStorage.setItem('makermatrix-compact-mode', newCompactMode.toString())
  }

  return (
    <ThemeContext.Provider
      value={{
        isDarkMode,
        toggleDarkMode,
        currentTheme,
        setTheme,
        isCompactMode,
        toggleCompactMode,
      }}
    >
      {children}
    </ThemeContext.Provider>
  )
}

export const useTheme = () => {
  const context = useContext(ThemeContext)
  if (context === undefined) {
    throw new Error('useTheme must be used within a ThemeProvider')
  }
  return context
}
