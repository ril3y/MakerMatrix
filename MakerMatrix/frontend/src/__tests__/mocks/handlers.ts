import { http, HttpResponse } from 'msw'
import { 
  createMockPart, 
  createMockLocation, 
  createMockCategory, 
  createMockUser, 
  createMockSupplier,
  createMockTask 
} from '../utils/test-utils'

const API_BASE = 'http://localhost:57891'

export const handlers = [
  // Authentication handlers
  http.post(`${API_BASE}/auth/login`, () => {
    return HttpResponse.json({
      access_token: 'mock-jwt-token',
      token_type: 'bearer',
      status: 'success',
      message: 'Login successful'
    })
  }),

  http.post(`${API_BASE}/auth/logout`, () => {
    return HttpResponse.json({
      status: 'success',
      message: 'Logout successful'
    })
  }),

  // Parts handlers
  http.get(`${API_BASE}/parts/get_all_parts`, ({ request }) => {
    const url = new URL(request.url)
    const page = parseInt(url.searchParams.get('page') || '1')
    const pageSize = parseInt(url.searchParams.get('page_size') || '10')
    
    const mockParts = Array.from({ length: 25 }, (_, i) => 
      createMockPart({
        id: `part-${i + 1}`,
        part_name: `Test Part ${i + 1}`,
        part_number: `P${String(i + 1).padStart(3, '0')}`,
      })
    )
    
    const startIdx = (page - 1) * pageSize
    const endIdx = startIdx + pageSize
    const paginatedParts = mockParts.slice(startIdx, endIdx)
    
    return HttpResponse.json({
      status: 'success',
      message: `Retrieved ${paginatedParts.length} parts`,
      data: paginatedParts,
      page,
      page_size: pageSize,
      total_parts: mockParts.length
    })
  }),

  http.post(`${API_BASE}/parts/add_part`, async ({ request }) => {
    const body = await request.json()
    const newPart = createMockPart(body)
    
    return HttpResponse.json({
      status: 'success',
      message: 'Part created successfully',
      data: newPart
    })
  }),

  http.get(`${API_BASE}/parts/get_part`, ({ request }) => {
    const url = new URL(request.url)
    const partId = url.searchParams.get('part_id')
    const partName = url.searchParams.get('part_name')
    const partNumber = url.searchParams.get('part_number')
    
    if (partId || partName || partNumber) {
      return HttpResponse.json({
        status: 'success',
        message: 'Part retrieved successfully',
        data: createMockPart({ id: partId })
      })
    }
    
    return HttpResponse.json({
      status: 'error',
      message: 'Part not found'
    }, { status: 404 })
  }),

  http.put(`${API_BASE}/parts/update_part/:id`, async ({ params, request }) => {
    const { id } = params
    const body = await request.json()
    const updatedPart = createMockPart({ id, ...body })
    
    return HttpResponse.json({
      status: 'success',
      message: 'Part updated successfully',
      data: updatedPart
    })
  }),

  http.delete(`${API_BASE}/parts/delete_part`, ({ request }) => {
    const url = new URL(request.url)
    const partId = url.searchParams.get('part_id')
    
    return HttpResponse.json({
      status: 'success',
      message: 'Part deleted successfully',
      data: { deleted: true, part_id: partId }
    })
  }),

  // Categories handlers
  http.get(`${API_BASE}/categories/get_all_categories`, () => {
    const mockCategories = [
      createMockCategory({ id: 'cat-1', name: 'Resistors' }),
      createMockCategory({ id: 'cat-2', name: 'Capacitors' }),
      createMockCategory({ id: 'cat-3', name: 'ICs' }),
    ]
    
    return HttpResponse.json({
      status: 'success',
      message: 'Categories retrieved successfully',
      data: { categories: mockCategories }
    })
  }),

  http.post(`${API_BASE}/categories/add_category`, async ({ request }) => {
    const body = await request.json()
    const newCategory = createMockCategory(body)
    
    return HttpResponse.json({
      status: 'success',
      message: 'Category created successfully',
      data: newCategory
    })
  }),

  // Locations handlers
  http.get(`${API_BASE}/locations/get_all_locations`, () => {
    const mockLocations = [
      createMockLocation({ id: 'loc-1', name: 'Storage Room A' }),
      createMockLocation({ id: 'loc-2', name: 'Workbench 1' }),
      createMockLocation({ id: 'loc-3', name: 'Drawer 1', parent_id: 'loc-1' }),
    ]
    
    return HttpResponse.json({
      status: 'success',
      message: 'Locations retrieved successfully',
      data: mockLocations
    })
  }),

  http.post(`${API_BASE}/locations/add_location`, async ({ request }) => {
    const body = await request.json()
    const newLocation = createMockLocation(body)
    
    return HttpResponse.json({
      status: 'success',
      message: 'Location created successfully',
      data: newLocation
    })
  }),

  // Suppliers handlers
  http.get(`${API_BASE}/api/config/suppliers`, () => {
    const mockSuppliers = [
      createMockSupplier({ supplier_name: 'LCSC', display_name: 'LCSC Electronics' }),
      createMockSupplier({ supplier_name: 'DIGIKEY', display_name: 'DigiKey Electronics' }),
      createMockSupplier({ supplier_name: 'MOUSER', display_name: 'Mouser Electronics' }),
    ]
    
    return HttpResponse.json({
      status: 'success',
      message: `Retrieved ${mockSuppliers.length} supplier configurations`,
      data: mockSuppliers
    })
  }),

  http.post(`${API_BASE}/api/config/suppliers`, async ({ request }) => {
    const body = await request.json()
    const newSupplier = createMockSupplier(body)
    
    return HttpResponse.json({
      status: 'success',
      message: `Created supplier configuration: ${newSupplier.supplier_name}`,
      data: newSupplier
    })
  }),

  http.delete(`${API_BASE}/api/config/suppliers/:name`, ({ params }) => {
    const { name } = params
    
    return HttpResponse.json({
      status: 'success',
      message: `Deleted supplier configuration: ${name}`,
      data: { supplier_name: name, deleted: 'true' }
    })
  }),

  // Tasks handlers
  http.get(`${API_BASE}/api/tasks/`, ({ request }) => {
    const url = new URL(request.url)
    const limit = parseInt(url.searchParams.get('limit') || '50')
    
    const mockTasks = Array.from({ length: 10 }, (_, i) =>
      createMockTask({
        id: `task-${i + 1}`,
        name: `Task ${i + 1}`,
        status: i % 3 === 0 ? 'COMPLETED' : i % 2 === 0 ? 'RUNNING' : 'PENDING'
      })
    )
    
    return HttpResponse.json({
      status: 'success',
      message: 'Tasks retrieved successfully',
      data: mockTasks.slice(0, limit)
    })
  }),

  http.post(`${API_BASE}/api/tasks/`, async ({ request }) => {
    const body = await request.json()
    const newTask = createMockTask(body)
    
    return HttpResponse.json({
      status: 'success',
      message: 'Task created successfully',
      data: newTask
    })
  }),

  // Utility handlers
  http.get(`${API_BASE}/utility/get_counts`, () => {
    return HttpResponse.json({
      status: 'success',
      message: 'Counts retrieved successfully',
      data: {
        parts: 150,
        locations: 25,
        categories: 12
      }
    })
  }),

  // CSV Import handlers
  http.post(`${API_BASE}/csv/preview`, async ({ request }) => {
    const body = await request.json()
    
    return HttpResponse.json({
      status: 'success',
      message: 'CSV preview generated',
      data: {
        parser_type: 'lcsc',
        total_rows: 5,
        preview_data: [
          { 'LCSC Part': 'C123456', 'MFR.Part': 'ABC123', 'Package': '0603', 'Description': 'Test Resistor' },
          { 'LCSC Part': 'C123457', 'MFR.Part': 'ABC124', 'Package': '0805', 'Description': 'Test Capacitor' }
        ],
        detected_fields: ['LCSC Part', 'MFR.Part', 'Package', 'Description']
      }
    })
  }),

  http.post(`${API_BASE}/csv/import`, async ({ request }) => {
    const body = await request.json()
    
    return HttpResponse.json({
      status: 'success',
      message: 'CSV import completed successfully',
      data: {
        total_rows: 5,
        successful_imports: 4,
        failed_imports: 1,
        import_summary: {
          new_parts: 3,
          updated_parts: 1,
          errors: []
        }
      }
    })
  }),

  // Error handlers for testing error states
  http.get(`${API_BASE}/test/error/500`, () => {
    return HttpResponse.json({
      status: 'error',
      message: 'Internal server error'
    }, { status: 500 })
  }),

  http.get(`${API_BASE}/test/error/404`, () => {
    return HttpResponse.json({
      status: 'error',
      message: 'Not found'
    }, { status: 404 })
  }),

  http.get(`${API_BASE}/test/error/unauthorized`, () => {
    return HttpResponse.json({
      status: 'error',
      message: 'Unauthorized'
    }, { status: 401 })
  }),
]