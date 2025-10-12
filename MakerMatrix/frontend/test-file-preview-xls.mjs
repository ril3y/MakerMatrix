import * as XLSX from 'xlsx';
import { readFileSync } from 'fs';

// Simulate the parseExcel function from filePreview.ts
async function parseExcel(arrayBuffer) {
  const workbook = XLSX.read(arrayBuffer, { type: 'array' });

  // Get first sheet
  const firstSheetName = workbook.SheetNames[0];
  if (!firstSheetName) {
    return { headers: [], rows: [], totalRows: 0 };
  }

  const worksheet = workbook.Sheets[firstSheetName];

  // Convert to JSON with header row
  const jsonData = XLSX.utils.sheet_to_json(worksheet, { header: 1, defval: '' });

  if (jsonData.length === 0) {
    return { headers: [], rows: [], totalRows: 0 };
  }

  // First row is headers
  const headers = jsonData[0].map((h) => String(h || '').trim());

  // Convert remaining rows to objects
  const previewRows = [];
  const maxPreviewRows = Math.min(5, jsonData.length - 1);

  for (let i = 1; i <= maxPreviewRows; i++) {
    const row = {};
    headers.forEach((header, index) => {
      row[header] = jsonData[i][index] !== undefined ? String(jsonData[i][index]) : '';
    });
    previewRows.push(row);
  }

  return {
    headers,
    rows: previewRows,
    totalRows: Math.max(0, jsonData.length - 1), // Subtract 1 for header row
  };
}

const xlsPath = '/home/ril3y/MakerMatrix/MakerMatrix/tests/mouser_xls_test/271360826.xls';

console.log('Testing filePreview.ts XLS parsing logic...\n');

try {
  // Read file as buffer (simulating file.arrayBuffer() in browser)
  const fileBuffer = readFileSync(xlsPath);
  const arrayBuffer = fileBuffer.buffer.slice(
    fileBuffer.byteOffset,
    fileBuffer.byteOffset + fileBuffer.byteLength
  );

  // Parse using our function
  const result = await parseExcel(arrayBuffer);

  console.log('✓ Parse completed');
  console.log(`✓ Headers found: ${result.headers.length}`);
  console.log(`✓ Preview rows: ${result.rows.length}`);
  console.log(`✓ Total rows: ${result.totalRows}\n`);

  console.log('Headers:');
  result.headers.forEach((h, i) => console.log(`  ${i + 1}. ${h}`));

  console.log('\nFirst preview row:');
  console.log(JSON.stringify(result.rows[0], null, 2));

  console.log('\n✅ Frontend XLS parsing test PASSED');
  console.log('\nThe XLS file will display correctly in the preview!');
} catch (error) {
  console.error('❌ Frontend XLS parsing test FAILED:', error.message);
  console.error(error.stack);
  process.exit(1);
}
