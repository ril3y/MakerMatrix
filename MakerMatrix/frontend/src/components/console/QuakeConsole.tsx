import React, { useState, useEffect, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import Terminal from 'react-console-emulator';
import { useNavigate } from 'react-router-dom';
import { partsService } from '../../services/parts.service';
import { locationsService } from '../../services/locations.service';
import { categoriesService } from '../../services/categories.service';
import { aiService } from '../../services/ai.service';
import { usePartsStore } from '../../store/partsStore';
import toast from 'react-hot-toast';

interface CommandResult {
  message: string;
  data?: any;
  action?: 'navigate' | 'update-view' | 'show-results';
}

const QuakeConsole: React.FC = () => {
  const [isVisible, setIsVisible] = useState(false);
  const [isProcessing, setIsProcessing] = useState(false);
  const navigate = useNavigate();
  const { setSearchQuery, setSelectedCategory, setSelectedLocation } = usePartsStore();

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      // Tilde key (` or ~) - only if not in an input field
      if ((e.key === '`' || e.key === '~') && !(e.target instanceof HTMLInputElement || e.target instanceof HTMLTextAreaElement)) {
        e.preventDefault();
        e.stopPropagation();
        setIsVisible(prev => !prev);
      }
      // ESC to close
      if (e.key === 'Escape' && isVisible) {
        e.preventDefault();
        e.stopPropagation();
        setIsVisible(false);
      }
    };

    document.addEventListener('keydown', handleKeyDown, true);
    return () => document.removeEventListener('keydown', handleKeyDown, true);
  }, [isVisible]);

  const processAICommand = async (input: string): Promise<CommandResult> => {
    try {
      setIsProcessing(true);
      
      // Send command to AI service
      const aiResponse = await aiService.processCommand(input);
      
      // Handle different types of AI responses
      if (aiResponse.action === 'search-parts') {
        // Navigate to parts page with search
        setSearchQuery(aiResponse.searchQuery || '');
        if (aiResponse.location) {
          const locations = await locationsService.getAll();
          const location = locations.find(l => 
            l.name.toLowerCase().includes(aiResponse.location.toLowerCase())
          );
          if (location) {
            setSelectedLocation(location.id);
          }
        }
        if (aiResponse.category) {
          const categories = await categoriesService.getAll();
          const category = categories.find(c => 
            c.name.toLowerCase().includes(aiResponse.category.toLowerCase())
          );
          if (category) {
            setSelectedCategory(category.id);
          }
        }
        navigate('/parts');
        return {
          message: `Searching for parts: ${aiResponse.description || input}`,
          action: 'navigate'
        };
      }
      
      if (aiResponse.action === 'navigate') {
        navigate(aiResponse.path);
        return {
          message: `Navigating to ${aiResponse.path}`,
          action: 'navigate'
        };
      }
      
      // Default response
      return {
        message: aiResponse.message || 'Command processed',
        data: aiResponse.data
      };
    } catch (error) {
      console.error('AI command error:', error);
      return {
        message: `Error: ${error instanceof Error ? error.message : 'Failed to process command'}`
      };
    } finally {
      setIsProcessing(false);
    }
  };

  const commands = {
    help: {
      description: 'Show available commands',
      fn: () => {
        return `
Available Commands:
- help: Show this help message
- clear: Clear the console
- find <query>: Search for parts (AI-powered)
- go <page>: Navigate to a page (parts, locations, categories, etc.)
- stats: Show inventory statistics

AI Natural Language Examples:
- "find all parts in desk drawer"
- "show me resistors in location A1"
- "list parts with low quantity"
- "go to settings page"
        `;
      }
    },
    
    find: {
      description: 'Search for parts using natural language',
      fn: async (...args: string[]) => {
        if (args.length === 0) {
          return 'Usage: find <search query>\nExample: find all parts in desk drawer';
        }
        const query = args.join(' ');
        const result = await processAICommand(`find ${query}`);
        return result.message;
      }
    },
    
    go: {
      description: 'Navigate to a page',
      fn: async (...args: string[]) => {
        if (args.length === 0) {
          return 'Usage: go <page>\nAvailable pages: parts, locations, categories, users, settings';
        }
        const page = args[0].toLowerCase();
        const routes: Record<string, string> = {
          'parts': '/parts',
          'locations': '/locations',
          'categories': '/categories',
          'users': '/users',
          'settings': '/settings',
          'home': '/',
          'dashboard': '/'
        };
        
        if (routes[page]) {
          navigate(routes[page]);
          return `Navigating to ${page}...`;
        }
        return `Unknown page: ${page}`;
      }
    },
    
    stats: {
      description: 'Show inventory statistics',
      fn: async () => {
        try {
          const parts = await partsService.getAll();
          const locations = await locationsService.getAll();
          const categories = await categoriesService.getAll();
          
          return `
Inventory Statistics:
- Total Parts: ${parts.length}
- Total Locations: ${locations.length}
- Total Categories: ${categories.length}
- Low Stock Items: ${parts.filter(p => p.quantity < (p.minimum_quantity || 0)).length}
          `;
        } catch (error) {
          return 'Error fetching statistics';
        }
      }
    },
    
    clear: {
      description: 'Clear the console',
      fn: () => {
        return false; // This tells react-console-emulator to clear
      }
    }
  };

  // Handle natural language input
  const handleCommand = useCallback(async (command: string) => {
    // Check if it's a built-in command
    const [cmd, ...args] = command.trim().split(' ');
    if (commands[cmd as keyof typeof commands]) {
      return; // Let the built-in command handler process it
    }
    
    // Otherwise, send to AI
    const result = await processAICommand(command);
    return result.message;
  }, []);

  return (
    <AnimatePresence mode="wait">
      {isVisible && (
        <motion.div
          initial={{ y: '-100%' }}
          animate={{ y: 0 }}
          exit={{ y: '-100%' }}
          transition={{ 
            type: 'spring', 
            damping: 25,
            stiffness: 300
          }}
          className="fixed top-0 left-0 right-0 h-1/2 z-[100] shadow-2xl pointer-events-auto"
          style={{
            background: 'rgba(17, 24, 39, 0.95)',
            backdropFilter: 'blur(8px)',
            borderBottom: '2px solid rgba(139, 92, 246, 0.5)',
            maxHeight: '50vh'
          }}
          onClick={(e) => e.stopPropagation()}
        >
          <div className="h-full flex flex-col">
            <div className="flex items-center justify-between px-4 py-2 border-b border-gray-700">
              <span className="text-sm text-purple-400 font-mono">
                MakerMatrix Console {isProcessing && '(Processing...)'}
              </span>
              <button
                onClick={() => setIsVisible(false)}
                className="text-gray-400 hover:text-white text-sm"
              >
                Press ~ or ESC to close
              </button>
            </div>
            
            <div className="flex-1 overflow-hidden bg-transparent">
              <Terminal
                commands={commands}
                welcomeMessage={`Welcome to MakerMatrix Console v1.0
Type 'help' for available commands or use natural language to interact.
Examples: "find all parts in desk drawer" or "show low stock items"`}
                promptLabel={'makermatrix>'}
                className="h-full w-full"
                style={{
                  backgroundColor: 'transparent',
                  fontSize: '14px',
                  fontFamily: 'Consolas, Monaco, monospace',
                  minHeight: '100%',
                  height: '100%'
                }}
                messageStyle={{ 
                  color: '#e5e7eb',
                  backgroundColor: 'transparent'
                }}
                promptLabelStyle={{ 
                  color: '#a78bfa',
                  backgroundColor: 'transparent'
                }}
                inputTextStyle={{ 
                  color: '#ffffff',
                  backgroundColor: 'transparent'
                }}
                contentStyle={{ 
                  padding: '10px',
                  backgroundColor: 'transparent',
                  minHeight: '100%'
                }}
                autoFocus={isVisible}
                dangerMode={false}
                noDefaults={false}
                commandCallback={handleCommand}
              />
            </div>
          </div>
        </motion.div>
      )}
    </AnimatePresence>
  );
};

export default QuakeConsole;