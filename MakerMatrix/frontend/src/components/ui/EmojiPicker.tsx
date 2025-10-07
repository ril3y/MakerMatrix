import { useState, useEffect, useRef } from 'react'
import { ChevronDown, X, Search } from 'lucide-react'

interface EmojiPickerProps {
  value?: string
  onChange: (emoji: string | null) => void
  placeholder?: string
}

const EMOJI_CATEGORIES = {
  'Location Types': ['🏢', '🏠', '🏪', '🏬', '🏭', '🏗️', '🏛️', '🏤', '🏦', '🏨'],
  'Storage & Boxes': ['📦', '🗃️', '📋', '📁', '🗂️', '📇', '🗄️', '🧰', '📚', '📖', '🗳️', '🎁'],
  'Electronics & Chips': ['🔌', '💾', '💿', '📀', '💽', '🔋', '🪫', '⚡', '🧮', '🖲️', '🕹️', '📟'],
  'Components & Parts': ['🔧', '🔩', '⚙️', '🧲', '📡', '🛰️', '📻', '📺', '🎛️', '🎚️', '🔘', '⚪'],
  'Hand Tools': ['🔧', '🔨', '🪛', '🔩', '⚙️', '🛠️', '⚒️', '🪚', '🗜️', '📏', '📐', '✂️'],
  'Power Tools': ['⚡', '🔌', '💡', '🔋', '🪫', '🪥', '🧲', '⚠️', '🔥', '💥', '⭐', '🌟'],
  'Workshop & Garage': ['🏭', '🏗️', '🚗', '🛞', '🛢️', '⛽', '🧯', '🚨', '🦺', '👷', '🏴‍☠️', '⚙️'],
  'Toolboxes & Cases': ['🧰', '💼', '👜', '🎒', '🗃️', '📦', '🗳️', '🛄', '📱', '💻', '🖥️', '⌨️'],
  Colors: ['🔴', '🟠', '🟡', '🟢', '🔵', '🟣', '⚫', '⚪', '🟤', '🔶', '🟥', '🟨'],
  Numbers: ['1️⃣', '2️⃣', '3️⃣', '4️⃣', '5️⃣', '6️⃣', '7️⃣', '8️⃣', '9️⃣', '🔟', '💯', '#️⃣'],
  Letters: ['🅰️', '🅱️', '🅾️', '🆎', '🆑', '🆒', '🆓', '🆔', '🆕', '🆗', '🔤', '🔡'],
  'Arrows & Shapes': ['⬆️', '⬇️', '⬅️', '➡️', '↗️', '↘️', '↙️', '↖️', '↕️', '↔️', '🔺', '🔻'],
}

// Emoji search keywords mapping
const EMOJI_KEYWORDS = {
  '🧰': ['tool', 'toolbox', 'tools', 'box', 'storage', 'workshop'],
  '🔧': ['wrench', 'tool', 'repair', 'fix', 'mechanic'],
  '🔨': ['hammer', 'tool', 'build', 'construction', 'nail'],
  '🪛': ['screwdriver', 'tool', 'screw', 'repair', 'fix'],
  '🔩': ['bolt', 'screw', 'hardware', 'fastener'],
  '⚙️': ['gear', 'settings', 'mechanical', 'engine'],
  '🛠️': ['tools', 'repair', 'fix', 'maintenance', 'workshop'],
  '⚒️': ['hammer', 'tools', 'construction', 'build'],
  '🪚': ['saw', 'cut', 'wood', 'tool', 'construction'],
  '🗜️': ['clamp', 'vise', 'tool', 'hold', 'grip'],
  '📏': ['ruler', 'measure', 'tool', 'length'],
  '📐': ['triangle', 'measure', 'angle', 'tool'],
  '✂️': ['scissors', 'cut', 'tool'],
  '⚡': ['power', 'electric', 'electricity', 'energy'],
  '🔌': ['plug', 'power', 'electric', 'outlet'],
  '💡': ['light', 'bulb', 'idea', 'electric'],
  '🔋': ['battery', 'power', 'energy', 'electric'],
  '🪫': ['battery', 'low', 'power', 'dead'],
  '🧲': ['magnet', 'magnetic', 'tool'],
  '⚠️': ['warning', 'caution', 'danger', 'alert'],
  '🔥': ['fire', 'hot', 'danger', 'flame'],
  '💥': ['explosion', 'bang', 'power', 'impact'],
  '🏭': ['factory', 'workshop', 'industrial', 'building'],
  '🏗️': ['construction', 'building', 'crane', 'site'],
  '🚗': ['car', 'vehicle', 'garage', 'automotive'],
  '🛞': ['tire', 'wheel', 'car', 'automotive'],
  '🛢️': ['oil', 'drum', 'barrel', 'fuel'],
  '⛽': ['gas', 'fuel', 'station', 'pump'],
  '🧯': ['fire', 'extinguisher', 'safety', 'emergency'],
  '🚨': ['alarm', 'emergency', 'warning', 'siren'],
  '🦺': ['vest', 'safety', 'construction', 'hi-vis'],
  '👷': ['worker', 'construction', 'hard hat', 'builder'],
  '📦': ['box', 'package', 'storage', 'container'],
  '🗃️': ['file', 'storage', 'archive', 'box'],
  '📋': ['clipboard', 'list', 'notes'],
  '📁': ['folder', 'file', 'storage', 'organize'],
  '🗂️': ['divider', 'file', 'organize', 'storage'],
  '📇': ['cards', 'index', 'organize', 'file'],
  '🗄️': ['cabinet', 'file', 'storage', 'office'],
  '📚': ['books', 'storage', 'shelf', 'library'],
  '🗳️': ['ballot', 'box', 'storage', 'container'],
  '🎁': ['gift', 'box', 'present', 'storage'],
  '💼': ['briefcase', 'case', 'storage', 'business'],
  '👜': ['bag', 'storage', 'carry', 'container'],
  '🎒': ['backpack', 'bag', 'storage', 'carry'],
  '🛄': ['luggage', 'bag', 'storage', 'travel'],
  '📱': ['phone', 'mobile', 'device', 'tech'],
  '💻': ['laptop', 'computer', 'tech', 'device'],
  '🖥️': ['computer', 'desktop', 'monitor', 'tech'],
  '⌨️': ['keyboard', 'computer', 'input', 'tech'],
  // Electronics & Chips
  '💾': ['floppy', 'disk', 'storage', 'memory', 'chip', 'data'],
  '💿': ['cd', 'disc', 'storage', 'optical', 'data'],
  '📀': ['dvd', 'disc', 'storage', 'optical', 'data'],
  '💽': ['minidisc', 'storage', 'disc', 'data'],
  '🧮': ['abacus', 'calculator', 'computing', 'math', 'chip'],
  '🖲️': ['trackball', 'mouse', 'input', 'computer'],
  '🕹️': ['joystick', 'controller', 'gaming', 'input'],
  '📟': ['pager', 'device', 'communication', 'electronic'],
  // Components & Parts
  '📡': ['antenna', 'satellite', 'communication', 'radio', 'signal'],
  '🛰️': ['satellite', 'communication', 'space', 'signal'],
  '📻': ['radio', 'communication', 'audio', 'device'],
  '📺': ['tv', 'television', 'monitor', 'display', 'screen'],
  '🎛️': ['control', 'panel', 'knobs', 'mixer', 'electronic'],
  '🎚️': ['slider', 'control', 'level', 'audio', 'adjustment'],
  '🔘': ['button', 'control', 'interface', 'input', 'round'],
  '⚪': ['white', 'circle', 'button', 'component', 'part'],
}

const EmojiPicker = ({ value, onChange, placeholder = 'Select emoji...' }: EmojiPickerProps) => {
  const [isOpen, setIsOpen] = useState(false)
  const [selectedCategory, setSelectedCategory] = useState<string>('Location Types')
  const [searchTerm, setSearchTerm] = useState('')
  const containerRef = useRef<HTMLDivElement>(null)

  // Close dropdown when clicking outside
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (containerRef.current && !containerRef.current.contains(event.target as Node)) {
        setIsOpen(false)
      }
    }

    document.addEventListener('mousedown', handleClickOutside)
    return () => {
      document.removeEventListener('mousedown', handleClickOutside)
    }
  }, [])

  const handleEmojiSelect = (emoji: string) => {
    // Only allow single emoji - replace any existing emoji
    onChange(emoji)
    setIsOpen(false)
  }

  const handleRemove = (e: React.MouseEvent) => {
    e.stopPropagation()
    onChange(null)
  }

  // Search functionality
  const searchEmojis = (searchTerm: string) => {
    if (!searchTerm.trim()) return []

    const query = searchTerm.toLowerCase().trim()
    const matchedEmojis: string[] = []

    // Search through all emojis and their keywords
    Object.entries(EMOJI_KEYWORDS).forEach(([emoji, keywords]) => {
      const matchesKeyword = keywords.some((keyword) => keyword.toLowerCase().includes(query))
      if (matchesKeyword && !matchedEmojis.includes(emoji)) {
        matchedEmojis.push(emoji)
      }
    })

    // Also search through category names and emoji unicode names
    Object.entries(EMOJI_CATEGORIES).forEach(([categoryName, emojis]) => {
      if (categoryName.toLowerCase().includes(query)) {
        emojis.forEach((emoji) => {
          if (!matchedEmojis.includes(emoji)) {
            matchedEmojis.push(emoji)
          }
        })
      }
    })

    return matchedEmojis
  }

  const handleSearchChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const newSearchTerm = e.target.value
    setSearchTerm(newSearchTerm)

    // If searching, switch to search results
    if (newSearchTerm.trim()) {
      setSelectedCategory('Search Results')
    } else {
      setSelectedCategory('Location Types')
    }
  }

  const clearSearch = () => {
    setSearchTerm('')
    setSelectedCategory('Location Types')
  }

  // Get emojis to display based on current category or search
  const getDisplayEmojis = () => {
    if (searchTerm.trim()) {
      return searchEmojis(searchTerm)
    }
    return EMOJI_CATEGORIES[selectedCategory as keyof typeof EMOJI_CATEGORIES] || []
  }

  return (
    <div className="relative" ref={containerRef}>
      <div
        className="input w-full cursor-pointer flex items-center justify-between hover:border-primary/50 transition-colors"
        onClick={() => setIsOpen(!isOpen)}
      >
        <div className="flex items-center gap-3">
          {value ? (
            <>
              <span className="text-2xl select-none">{value}</span>
              <span className="text-theme-secondary text-sm font-medium">Selected emoji</span>
            </>
          ) : (
            <span className="text-theme-muted">{placeholder}</span>
          )}
        </div>
        <div className="flex items-center gap-1">
          {value && (
            <button
              type="button"
              onClick={handleRemove}
              className="p-1 hover:bg-theme-secondary rounded transition-colors"
              title="Remove emoji"
            >
              <X className="w-4 h-4 text-theme-muted" />
            </button>
          )}
          <ChevronDown
            className={`w-4 h-4 text-theme-muted transition-transform ${isOpen ? 'rotate-180' : ''}`}
          />
        </div>
      </div>

      {isOpen && (
        <div className="absolute top-full left-0 right-0 mt-2 bg-theme-primary border border-theme-primary rounded-lg shadow-xl z-[100] max-h-96 overflow-hidden">
          {/* Search Bar */}
          <div className="p-3 border-b border-theme-primary bg-theme-secondary">
            <div className="relative">
              <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-theme-muted" />
              <input
                type="text"
                placeholder="Search emojis... (e.g., 'tool', 'box', 'storage')"
                value={searchTerm}
                onChange={handleSearchChange}
                className="w-full pl-10 pr-8 py-2 text-sm border border-theme-primary rounded-lg bg-theme-primary text-theme-primary placeholder-theme-muted focus:outline-none focus:ring-2 focus:ring-primary"
              />
              {searchTerm && (
                <button
                  type="button"
                  onClick={clearSearch}
                  className="absolute right-2 top-1/2 transform -translate-y-1/2 p-1 hover:bg-theme-tertiary rounded transition-colors"
                >
                  <X className="w-3 h-3 text-theme-muted" />
                </button>
              )}
            </div>
          </div>

          {/* Category Tabs (hidden when searching) */}
          {!searchTerm.trim() && (
            <div className="border-b border-theme-primary overflow-x-auto bg-theme-secondary">
              <div className="flex">
                {Object.keys(EMOJI_CATEGORIES).map((category) => (
                  <button
                    key={category}
                    type="button"
                    onClick={() => setSelectedCategory(category)}
                    className={`px-3 py-2 text-xs font-medium whitespace-nowrap border-b-2 transition-colors ${
                      selectedCategory === category
                        ? 'border-primary text-primary-accent bg-theme-primary'
                        : 'border-transparent text-theme-secondary hover:text-primary-accent hover:bg-theme-primary'
                    }`}
                  >
                    {category}
                  </button>
                ))}
              </div>
            </div>
          )}

          {/* Search Results Header */}
          {searchTerm.trim() && (
            <div className="px-4 py-2 bg-primary-10 border-b border-theme-primary">
              <p className="text-sm text-primary-accent font-medium">
                Search results for "{searchTerm}" ({getDisplayEmojis().length} found)
              </p>
            </div>
          )}

          {/* Emoji Grid */}
          <div className="p-4 max-h-64 overflow-y-auto bg-theme-primary">
            {getDisplayEmojis().length > 0 ? (
              <div className="grid grid-cols-6 gap-1">
                {getDisplayEmojis().map((emoji) => (
                  <button
                    key={emoji}
                    type="button"
                    onClick={() => handleEmojiSelect(emoji)}
                    className="p-3 text-2xl hover:bg-theme-secondary rounded-lg transition-colors border border-transparent hover:border-theme-primary focus:outline-none focus:ring-2 focus:ring-primary"
                    title={`Select ${emoji} - ${EMOJI_KEYWORDS[emoji]?.join(', ') || 'emoji'}`}
                  >
                    {emoji}
                  </button>
                ))}
              </div>
            ) : searchTerm.trim() ? (
              <div className="text-center py-8">
                <Search className="w-8 h-8 text-theme-muted mx-auto mb-2" />
                <p className="text-sm text-theme-secondary">No emojis found for "{searchTerm}"</p>
                <p className="text-xs text-theme-muted mt-1">
                  Try searching for 'tool', 'box', 'storage', 'power', etc.
                </p>
              </div>
            ) : (
              <div className="text-center py-4">
                <p className="text-sm text-theme-secondary">
                  Select a category or search for emojis
                </p>
              </div>
            )}
          </div>

          {/* Clear Option */}
          {value && (
            <div className="border-t border-theme-primary p-3 bg-theme-secondary">
              <button
                type="button"
                onClick={() => {
                  onChange(null)
                  setIsOpen(false)
                }}
                className="w-full text-left px-3 py-2 text-sm font-medium text-error hover:bg-theme-tertiary rounded-lg transition-colors flex items-center gap-2"
              >
                <X className="w-4 h-4" />
                Remove emoji
              </button>
            </div>
          )}
        </div>
      )}
    </div>
  )
}

export default EmojiPicker
