import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { toast } from 'react-hot-toast';
import UnifiedFileImporter from '../UnifiedFileImporter';
import { apiClient } from '@/services/api';

// Mock dependencies
vi.mock('react-hot-toast');
vi.mock('@/services/api');
vi.mock('@/utils/filenameExtractor', () => ({
  extractOrderInfoFromFilename: vi.fn().mockResolvedValue({}),
}));

const mockApiClient = vi.mocked(apiClient);

describe('UnifiedFileImporter', () => {
  const mockFile = new File(['part_number,quantity\nTP-001,100'], 'test.csv', { type: 'text/csv' });

  const mockProps = {
    parserType: 'lcsc',
    parserName: 'LCSC',
    description: 'Import from LCSC',
    onImportComplete: vi.fn(),
    uploadedFile: mockFile,
    filePreview: {
      headers: ['part_number', 'quantity'],
      preview_rows: [{ part_number: 'TP-001', quantity: '100' }],
      total_rows: 1,
      is_supported: true,
      validation_errors: [],
    },
  };

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders correctly with a file', () => {
    render(<UnifiedFileImporter {...mockProps} />);
    expect(screen.getByText(/Import LCSC Parts/i)).toBeInTheDocument();
    expect(screen.getByText(/test.csv/i)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Import Parts/i })).toBeInTheDocument();
  });

  it('calls the import API on button click', async () => {
    const user = userEvent.setup();
    mockApiClient.post.mockResolvedValue({ status: 'success', data: { part_ids: ['123'] } });

    render(<UnifiedFileImporter {...mockProps} />);

    const importButton = screen.getByRole('button', { name: /Import Parts/i });
    await user.click(importButton);

    await waitFor(() => {
      expect(apiClient.post).toHaveBeenCalledWith(
        '/api/import/file',
        expect.any(FormData),
        expect.any(Object)
      );
    });
  });

  it('shows success toast on successful import', async () => {
    const user = userEvent.setup();
    mockApiClient.post.mockResolvedValue({ status: 'success', data: { imported_count: 1 } });

    render(<UnifiedFileImporter {...mockProps} />);

    const importButton = screen.getByRole('button', { name: /Import Parts/i });
    await user.click(importButton);

    await waitFor(() => {
      expect(toast.success).toHaveBeenCalledWith(expect.stringContaining('Processed 1 parts'));
    });
  });

  it('shows error toast on failed import', async () => {
    const user = userEvent.setup();
    mockApiClient.post.mockRejectedValue(new Error('Import failed'));

    render(<UnifiedFileImporter {...mockProps} />);

    const importButton = screen.getByRole('button', { name: /Import Parts/i });
    await user.click(importButton);

    await waitFor(() => {
      expect(toast.error).toHaveBeenCalledWith('Import failed');
    });
  });
});
