/**
 * Tests for AddPartModal enrichment functionality
 *
 * Verifies that:
 * 1. URL pasting triggers auto-enrichment
 * 2. Enriched data properly populates form fields
 * 3. additional_properties are displayed as key-value pairs (not [object Object])
 * 4. LCSC, Adafruit, and McMaster-Carr enrichment all work correctly
 */

import { render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { vi, describe, it, expect, beforeEach } from 'vitest'
import AddPartModal from '../AddPartModal'
import * as partsService from '@/services/parts.service'

// Mock the parts service
vi.mock('@/services/parts.service')

describe('AddPartModal - Auto-Enrichment', () => {
  const mockOnClose = vi.fn()
  const mockOnPartAdded = vi.fn()

  beforeEach(() => {
    vi.clearAllMocks()
  })

  describe('LCSC Auto-Enrichment', () => {
    it('should auto-enrich when LCSC URL is pasted', async () => {
      const user = userEvent.setup()

      // Mock enrichment response
      vi.mocked(partsService.enrichFromSupplier).mockResolvedValue({
        success: true,
        supplier: 'lcsc',
        part_identifier: 'C25804',
        enrichment_method: 'api',
        data: {
          supplier_part_number: 'C25804',
          part_name: '10K Resistor',
          manufacturer: 'Test Manufacturer',
          description: '10K Ohm 0805 Resistor',
          image_url: 'https://example.com/image.jpg',
          additional_properties: {
            Resistance: '10K',
            Package: '0805',
            Tolerance: '1%',
            'Power Rating': '0.125W',
            'Is Smt': 'True',
          },
        },
      })

      render(<AddPartModal isOpen={true} onClose={mockOnClose} onPartAdded={mockOnPartAdded} />)

      // Find and paste LCSC URL
      const urlInput = screen.getByLabelText(/Product URL/i)
      await user.clear(urlInput)
      await user.type(urlInput, 'https://www.lcsc.com/product-detail/C25804.html')

      // Wait for enrichment to complete
      await waitFor(() => {
        expect(partsService.enrichFromSupplier).toHaveBeenCalledWith(
          'lcsc',
          'C25804',
          expect.any(Boolean)
        )
      })

      // Verify form fields are populated
      await waitFor(() => {
        expect(screen.getByDisplayValue('10K Resistor')).toBeInTheDocument()
        expect(screen.getByDisplayValue('Test Manufacturer')).toBeInTheDocument()
      })

      // Verify additional_properties are shown as key-value pairs
      // They should be visible in the custom properties section
      await waitFor(() => {
        expect(screen.getByText(/Resistance/i)).toBeInTheDocument()
        expect(screen.getByText(/10K/i)).toBeInTheDocument()
        expect(screen.getByText(/Package/i)).toBeInTheDocument()
        expect(screen.getByText(/0805/i)).toBeInTheDocument()
      })

      // Verify NO [object Object] text appears
      expect(screen.queryByText(/\[object Object\]/i)).not.toBeInTheDocument()
    })

    it('should handle LCSC enrichment failure gracefully', async () => {
      const user = userEvent.setup()

      // Mock enrichment failure
      vi.mocked(partsService.enrichFromSupplier).mockRejectedValue(
        new Error('Request failed with status code 500')
      )

      render(<AddPartModal isOpen={true} onClose={mockOnClose} onPartAdded={mockOnPartAdded} />)

      const urlInput = screen.getByLabelText(/Product URL/i)
      await user.clear(urlInput)
      await user.type(urlInput, 'https://www.lcsc.com/product-detail/C25804.html')

      // Should show error message
      await waitFor(() => {
        // The error should be logged to console or shown in UI
        expect(partsService.enrichFromSupplier).toHaveBeenCalled()
      })

      // Form should still be usable
      expect(urlInput).toBeInTheDocument()
    })
  })

  describe('Adafruit Auto-Enrichment', () => {
    it('should auto-enrich when Adafruit URL is pasted', async () => {
      const user = userEvent.setup()

      vi.mocked(partsService.enrichFromSupplier).mockResolvedValue({
        success: true,
        supplier: 'adafruit',
        part_identifier: '3571',
        enrichment_method: 'scraping',
        data: {
          supplier_part_number: '3571',
          part_name: 'LED Strip',
          manufacturer: 'Adafruit Industries',
          description: 'NeoPixel Digital RGB LED Strip',
          image_url: 'https://adafruit.com/image.jpg',
          additional_properties: {
            Length: '1m',
            'LED Count': '60',
            Voltage: '5V',
            Type: 'WS2812B',
          },
        },
      })

      render(<AddPartModal isOpen={true} onClose={mockOnClose} onPartAdded={mockOnPartAdded} />)

      const urlInput = screen.getByLabelText(/Product URL/i)
      await user.clear(urlInput)
      await user.type(urlInput, 'https://www.adafruit.com/product/3571')

      await waitFor(() => {
        expect(partsService.enrichFromSupplier).toHaveBeenCalledWith(
          'adafruit',
          '3571',
          expect.any(Boolean)
        )
      })

      // Verify enriched data is displayed correctly
      await waitFor(() => {
        expect(screen.getByText(/Length/i)).toBeInTheDocument()
        expect(screen.getByText(/1m/i)).toBeInTheDocument()
        expect(screen.getByText(/LED Count/i)).toBeInTheDocument()
        expect(screen.getByText(/60/i)).toBeInTheDocument()
      })

      // Verify NO [object Object]
      expect(screen.queryByText(/\[object Object\]/i)).not.toBeInTheDocument()
    })
  })

  describe('McMaster-Carr Auto-Enrichment', () => {
    it('should auto-enrich when McMaster URL is pasted', async () => {
      const user = userEvent.setup()

      vi.mocked(partsService.enrichFromSupplier).mockResolvedValue({
        success: true,
        supplier: 'mcmaster-carr',
        part_identifier: '91253A192',
        enrichment_method: 'scraping',
        data: {
          supplier_part_number: '91253A192',
          part_name: 'Socket Head Screw',
          manufacturer: 'McMaster-Carr',
          description: 'Black-Oxide Alloy Steel Socket Head Screw',
          image_url: 'https://mcmaster.com/image.jpg',
          additional_properties: {
            Material: 'Black-Oxide Alloy Steel',
            'Thread Size': 'M3 x 0.5mm',
            Length: '15mm',
            'Head Type': 'Socket Head',
            'Drive Style': 'Hex',
          },
        },
      })

      render(<AddPartModal isOpen={true} onClose={mockOnClose} onPartAdded={mockOnPartAdded} />)

      const urlInput = screen.getByLabelText(/Product URL/i)
      await user.clear(urlInput)
      await user.type(urlInput, 'https://www.mcmaster.com/91253A192/')

      await waitFor(() => {
        expect(partsService.enrichFromSupplier).toHaveBeenCalledWith(
          'mcmaster-carr',
          '91253A192',
          expect.any(Boolean)
        )
      })

      // Verify specifications are displayed
      await waitFor(() => {
        expect(screen.getByText(/Material/i)).toBeInTheDocument()
        expect(screen.getByText(/Black-Oxide Alloy Steel/i)).toBeInTheDocument()
        expect(screen.getByText(/Thread Size/i)).toBeInTheDocument()
        expect(screen.getByText(/M3 x 0.5mm/i)).toBeInTheDocument()
      })

      // Verify NO nested objects
      expect(screen.queryByText(/\[object Object\]/i)).not.toBeInTheDocument()
    })
  })

  describe('Additional Properties Display', () => {
    it('should display additional_properties as flat key-value pairs', async () => {
      const user = userEvent.setup()

      vi.mocked(partsService.enrichFromSupplier).mockResolvedValue({
        success: true,
        supplier: 'test-supplier',
        part_identifier: 'TEST-123',
        enrichment_method: 'api',
        data: {
          supplier_part_number: 'TEST-123',
          part_name: 'Test Part',
          additional_properties: {
            'Property 1': 'Value 1',
            'Property 2': 'Value 2',
            'Property 3': 'Value 3',
            // No nested objects should appear
          },
        },
      })

      render(<AddPartModal isOpen={true} onClose={mockOnClose} onPartAdded={mockOnPartAdded} />)

      const urlInput = screen.getByLabelText(/Product URL/i)
      await user.clear(urlInput)
      await user.type(urlInput, 'https://example.com/TEST-123')

      await waitFor(() => {
        expect(screen.getByText(/Property 1/i)).toBeInTheDocument()
        expect(screen.getByText(/Value 1/i)).toBeInTheDocument()
      })

      // Ensure all properties are strings, not objects
      const customPropsSection = screen.getByText(/Additional Properties/i).closest('div')
      if (customPropsSection) {
        const objectTexts = within(customPropsSection).queryAllByText(/\[object/i)
        expect(objectTexts).toHaveLength(0)
      }
    })

    it('should not display internal tracking fields', async () => {
      const user = userEvent.setup()

      vi.mocked(partsService.enrichFromSupplier).mockResolvedValue({
        success: true,
        supplier: 'lcsc',
        part_identifier: 'C25804',
        enrichment_method: 'api',
        data: {
          supplier_part_number: 'C25804',
          part_name: 'Resistor',
          additional_properties: {
            Resistance: '10K',
            last_enrichment_date: '2025-01-01T00:00:00', // Should be filtered
            enrichment_source: 'lcsc', // Should be filtered
            Package: '0805',
          },
        },
      })

      render(<AddPartModal isOpen={true} onClose={mockOnClose} onPartAdded={mockOnPartAdded} />)

      const urlInput = screen.getByLabelText(/Product URL/i)
      await user.clear(urlInput)
      await user.type(urlInput, 'https://www.lcsc.com/product-detail/C25804.html')

      await waitFor(() => {
        expect(screen.getByText(/Resistance/i)).toBeInTheDocument()
        expect(screen.getByText(/Package/i)).toBeInTheDocument()
      })

      // Internal fields should be filtered out
      expect(screen.queryByText(/last_enrichment_date/i)).not.toBeInTheDocument()
      expect(screen.queryByText(/enrichment_source/i)).not.toBeInTheDocument()
    })
  })
})
