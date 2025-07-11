import React, { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { useNavigate } from 'react-router-dom';
import { partsService } from '../../services/parts.service';
import { locationsService } from '../../services/locations.service';
import { categoriesService } from '../../services/categories.service';
import { usePartsStore } from '../../store/partsStore';
import { apiClient } from '../../services/api';

interface CommandResult {
  message: string;
  data?: any;
  action?: 'navigate' | 'update-view' | 'show-results';
}

const QuakeConsole: React.FC = () => {
  const [isVisible, setIsVisible] = useState(false);
  const [isProcessing, setIsProcessing] = useState(false);
  const [input, setInput] = useState('');
  const [history, setHistory] = useState<Array<{type: 'input' | 'output' | 'error', content: string}>>([
    { type: 'output', content: 'Welcome to MakerMatrix Console v1.0' },
    { type: 'output', content: 'Available commands: find, go, stats, help' },
    { type: 'output', content: 'Use natural language: "find all parts in desk drawer"' }
  ]);
  const [historyIndex, setHistoryIndex] = useState(-1);
  const [commandHistory, setCommandHistory] = useState<string[]>([]);
  const navigate = useNavigate();
  const { setSearchQuery, setFilters } = usePartsStore();

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
      
      // Send command to real AI service using apiClient (handles auth automatically)
      const aiResult = await apiClient.post('/api/ai/chat', {
        message: input,
        conversation_history: []
      });
      
      if (aiResult.status !== 'success') {
        throw new Error(aiResult.message || 'AI request failed');
      }

      const aiResponse = aiResult.data.response;
      
      // Check if the AI response contains actionable results that should trigger navigation
      if (aiResponse.includes('Query Result') && aiResponse.includes('partmodel')) {
        // AI found parts data - offer to navigate to parts page
        const updatedResponse = aiResponse + '\n\n💡 Tip: Type "go parts" to view all parts on the main page.';
        return {
          message: updatedResponse,
          data: null
        };
      }
      
      return {
        message: aiResponse,
        data: null
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
    }
  };

  const executeCommand = async (command: string) => {
    const trimmedCommand = command.trim();
    if (!trimmedCommand) return;

    // Add command to history
    setHistory(prev => [...prev, { type: 'input', content: `makermatrix> ${trimmedCommand}` }]);
    setCommandHistory(prev => [...prev, trimmedCommand]);
    setInput('');
    setIsProcessing(true);

    try {
      // Check built-in commands first
      const [cmd, ...args] = trimmedCommand.split(' ');
      
      if (cmd === 'help') {
        setHistory(prev => [...prev, { 
          type: 'output', 
          content: `Available Commands:
- help: Show this help message
- clear: Clear the console
- find <query>: Search for parts (AI-powered)
- go <page>: Navigate to a page (parts, locations, categories, etc.)
- stats: Show inventory statistics

Natural Language Examples:
- "find all parts in desk drawer"
- "show me resistors in location A1"
- "list parts with low quantity"` 
        }]);
        return;
      }

      if (cmd === 'clear') {
        setHistory([
          { type: 'output', content: 'Welcome to MakerMatrix Console v1.0' },
          { type: 'output', content: 'Available commands: find, go, stats, help' },
          { type: 'output', content: 'Use natural language: "find all parts in desk drawer"' }
        ]);
        return;
      }

      if (commands[cmd as keyof typeof commands]) {
        const result = await commands[cmd as keyof typeof commands].fn(...args);
        setHistory(prev => [...prev, { type: 'output', content: result }]);
        return;
      }

      // Send to AI for natural language processing
      const result = await processAICommand(trimmedCommand);
      setHistory(prev => [...prev, { type: 'output', content: result.message }]);

    } catch (error) {
      console.error('Command execution error:', error);
      setHistory(prev => [...prev, { 
        type: 'error', 
        content: `Error: ${error instanceof Error ? error.message : 'Command failed'}` 
      }]);
    } finally {
      setIsProcessing(false);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter') {
      executeCommand(input);
    } else if (e.key === 'ArrowUp') {
      e.preventDefault();
      if (commandHistory.length > 0) {
        const newIndex = historyIndex === -1 ? commandHistory.length - 1 : Math.max(0, historyIndex - 1);
        setHistoryIndex(newIndex);
        setInput(commandHistory[newIndex]);
      }
    } else if (e.key === 'ArrowDown') {
      e.preventDefault();
      if (historyIndex !== -1) {
        const newIndex = historyIndex < commandHistory.length - 1 ? historyIndex + 1 : -1;
        setHistoryIndex(newIndex);
        setInput(newIndex === -1 ? '' : commandHistory[newIndex]);
      }
    }
  };

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
          className="fixed top-0 left-0 right-0 z-50 shadow-2xl bg-theme-primary/95 backdrop-blur-lg border-b-2 border-primary/50"
          style={{
            height: '300px'
          }}
          onClick={(e) => e.stopPropagation()}
        >
          <div className="h-full flex flex-col">
            <div className="flex items-center justify-between px-4 py-2 border-b border-theme-secondary">
              <span className="text-sm text-primary-accent font-mono">
                MakerMatrix Console {isProcessing && '(Processing...)'}
              </span>
              <button
                onClick={() => setIsVisible(false)}
                className="text-theme-secondary hover:text-theme-primary text-sm"
              >
                Press ~ or ESC to close
              </button>
            </div>
            
            <div className="flex-1 overflow-hidden bg-transparent flex flex-col">
              {/* Terminal history */}
              <div className="flex-1 overflow-y-auto p-4 font-mono text-sm custom-scrollbar">
                {history.map((entry, index) => (
                  <div key={index} className={`mb-1 whitespace-pre-wrap ${
                    entry.type === 'input' ? 'text-theme-primary' : 
                    entry.type === 'error' ? 'text-error' : 'text-success'
                  }`}>
                    {entry.content}
                  </div>
                ))}
                {isProcessing && (
                  <div className="text-warning mb-1">Processing...</div>
                )}
              </div>
              
              {/* Input line */}
              <div className="border-t border-theme-secondary p-4 flex items-center font-mono text-sm">
                <span className="text-primary-accent mr-2">makermatrix&gt;</span>
                <input 
                  type="text" 
                  value={input}
                  onChange={(e) => setInput(e.target.value)}
                  onKeyDown={handleKeyDown}
                  className="flex-1 bg-transparent border-none outline-none text-theme-primary"
                  placeholder="Type a command or ask in natural language..."
                  autoFocus={isVisible}
                  disabled={isProcessing}
                />
              </div>
            </div>
          </div>
        </motion.div>
      )}
    </AnimatePresence>
  );
};

export default QuakeConsole;