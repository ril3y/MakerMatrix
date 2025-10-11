import * as XLSX from 'xlsx';
import { readFileSync } from 'fs';

const xlsPath = '/home/ril3y/MakerMatrix/MakerMatrix/tests/mouser_xls_test/271360826.xls';

console.log('Testing XLS parsing with xlsx library...\n');

try {
  // Read the XLS file
  const fileBuffer = readFileSync(xlsPath);
  const workbook = XLSX.read(fileBuffer, { type: 'buffer' });

  console.log('✓ Successfully read XLS file');
  console.log(`✓ Found ${workbook.SheetNames.length} sheet(s): ${workbook.SheetNames.join(', ')}\n`);

  // Get first sheet
  const firstSheetName = workbook.SheetNames[0];
  const worksheet = workbook.Sheets[firstSheetName];

  // Convert to JSON
  const jsonData = XLSX.utils.sheet_to_json(worksheet, { header: 1, defval: '' });

  console.log(`✓ Total rows: ${jsonData.length}`);

  if (jsonData.length > 0) {
    const headers = jsonData[0];
    console.log(`✓ Headers (${headers.length} columns):`);
    headers.forEach((h, i) => console.log(`  ${i + 1}. ${h}`));

    if (jsonData.length > 1) {
      console.log(`\n✓ Sample data (first row):`);
      const firstDataRow = jsonData[1];
      headers.forEach((header, i) => {
        console.log(`  ${header}: ${firstDataRow[i]}`);
      });
    }
  }

  console.log('\n✅ XLS parsing test PASSED');
} catch (error) {
  console.error('❌ XLS parsing test FAILED:', error.message);
  process.exit(1);
}
