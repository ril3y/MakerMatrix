import React, { useState } from 'react'
import { motion } from 'framer-motion'
import { FileText, ChevronDown } from 'lucide-react'
import CSVImportLCSC from './CSVImportLCSC'
import CSVImportDigiKey from './CSVImportDigiKey'
import { ImportResult } from './BaseCSVImport'

interface CSVImportSelectorProps {
  onImportComplete?: (result: ImportResult) => void
}

const CSVImportSelector: React.FC<CSVImportSelectorProps> = ({ onImportComplete }) => {
  const [selectedParser, setSelectedParser] = useState<string>('lcsc')

  const parsers = [
    { 
      id: 'lcsc', 
      name: 'LCSC Electronics', 
      description: 'Chinese electronics distributor',
      color: 'bg-blue-500',
      component: CSVImportLCSC
    },
    { 
      id: 'digikey', 
      name: 'DigiKey', 
      description: 'Major electronics distributor',
      color: 'bg-red-500',
      component: CSVImportDigiKey
    },
    { 
      id: 'mouser', 
      name: 'Mouser Electronics', 
      description: 'Global electronics distributor',
      color: 'bg-green-500',
      component: null // Not implemented yet
    }
  ]

  const selectedParserInfo = parsers.find(p => p.id === selectedParser)
  const SelectedComponent = selectedParserInfo?.component

  return (
    <div className="space-y-6">
      <div className="text-center">
        <h3 className="text-lg font-semibold text-primary mb-2 flex items-center justify-center gap-2">
          <FileText className="w-5 h-5" />
          Import Parts from CSV Orders
        </h3>
        <p className="text-secondary">
          Select your supplier and upload order CSV files to automatically add parts to your inventory
        </p>
      </div>

      {/* Parser Selection */}
      <div className="card p-4">
        <h4 className="font-medium text-primary mb-4">Select Supplier</h4>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {parsers.map((parser) => (
            <motion.button
              key={parser.id}
              onClick={() => setSelectedParser(parser.id)}
              disabled={!parser.component}
              whileHover={{ scale: parser.component ? 1.02 : 1 }}
              whileTap={{ scale: parser.component ? 0.98 : 1 }}
              className={`relative p-4 rounded-lg border-2 transition-all text-left ${
                selectedParser === parser.id
                  ? 'border-primary bg-primary/5'
                  : parser.component
                  ? 'border-border-primary hover:border-primary/50'
                  : 'border-border-primary opacity-50 cursor-not-allowed'
              }`}
            >
              <div className="flex items-start gap-3">
                <div className={`w-3 h-3 rounded-full ${parser.color} mt-1 ${!parser.component ? 'opacity-50' : ''}`} />
                <div className="flex-1">
                  <h5 className="font-medium text-primary">{parser.name}</h5>
                  <p className="text-sm text-secondary mt-1">{parser.description}</p>
                  {!parser.component && (
                    <p className="text-xs text-muted mt-2 italic">Coming soon</p>
                  )}
                </div>
              </div>
              
              {selectedParser === parser.id && parser.component && (
                <motion.div
                  initial={{ scale: 0 }}
                  animate={{ scale: 1 }}
                  className="absolute -top-2 -right-2 w-6 h-6 bg-primary rounded-full flex items-center justify-center"
                >
                  <div className="w-2 h-2 bg-white rounded-full" />
                </motion.div>
              )}
            </motion.button>
          ))}
        </div>
      </div>

      {/* Selected Parser Component */}
      <motion.div
        key={selectedParser}
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.3 }}
      >
        {SelectedComponent ? (
          <SelectedComponent 
            onImportComplete={onImportComplete}
            parserType={selectedParser}
            parserName={selectedParserInfo?.name || selectedParser}
            description={selectedParserInfo?.description || ''}
          />
        ) : (
          <div className="card p-8 text-center">
            <div className="w-16 h-16 bg-text-muted/10 rounded-full flex items-center justify-center mx-auto mb-4">
              <FileText className="w-8 h-8 text-muted" />
            </div>
            <h4 className="text-lg font-medium text-primary mb-2">
              {selectedParserInfo?.name} Import Coming Soon
            </h4>
            <p className="text-secondary">
              We're working on adding support for {selectedParserInfo?.name} CSV imports.
              <br />
              For now, try LCSC or DigiKey imports.
            </p>
          </div>
        )}
      </motion.div>
    </div>
  )
}

export default CSVImportSelector