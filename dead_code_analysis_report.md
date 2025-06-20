
# Dead Code Analysis Report
Generated: 2025-06-20 08:43:01

## Python Dead Code Analysis (vulture)
Analysis failed

## TypeScript Dead Code Analysis (ts-unused-exports)  
24 modules with unused exports
/home/ril3y/MakerMatrix/MakerMatrix/frontend/src/components/import/index.ts: ImportSelector, ImportSettings, FileUpload, ImportProgress, FilePreview, LCSCImporter, DigiKeyImporter, MouserImporter, useOrderImport, FilePreviewData, ImportResult, OrderInfo, ImportProgressType, UseOrderImportProps
/home/ril3y/MakerMatrix/MakerMatrix/frontend/src/components/layouts/index.ts: MainLayout, AuthLayout
/home/ril3y/MakerMatrix/MakerMatrix/frontend/src/components/ui/Tooltip.tsx: default
/home/ril3y/MakerMatrix/MakerMatrix/frontend/src/hooks/useAuth.ts: useAuth, useRequireRole, useRequirePermission
/home/ril3y/MakerMatrix/MakerMatrix/frontend/src/lib/axios.ts: default, apiClient
/home/ril3y/MakerMatrix/MakerMatrix/frontend/src/pages/suppliers/GenericConfigForm.tsx: GenericConfigForm
/home/ril3y/MakerMatrix/MakerMatrix/frontend/src/pages/suppliers/index.ts: SupplierConfigPage, AddSupplierModal, EditSupplierModal, CredentialsModal, ImportExportModal
/home/ril3y/MakerMatrix/MakerMatrix/frontend/src/services/activity.service.ts: ActivityListResponse, ActivityStats, ActivityService
/home/ril3y/MakerMatrix/MakerMatrix/frontend/src/services/ai.service.ts: AICommandResponse, AIProcessRequest
/home/ril3y/MakerMatrix/MakerMatrix/frontend/src/services/analytics.service.ts: SpendingBySupplier, SpendingTrend, PartOrderFrequency, PriceTrend, LowStockPart, InventoryValue, CategorySpending, DashboardSummary, AnalyticsParams
/home/ril3y/MakerMatrix/MakerMatrix/frontend/src/services/api.ts: handleApiError
/home/ril3y/MakerMatrix/MakerMatrix/frontend/src/services/dashboard.service.ts: DashboardCounts, DashboardService
/home/ril3y/MakerMatrix/MakerMatrix/frontend/src/services/dynamic-supplier.service.ts: PartSearchResult, SupplierCredentialsConfig, TestConnectionResult
/home/ril3y/MakerMatrix/MakerMatrix/frontend/src/services/parts.service.ts: PartsService
/home/ril3y/MakerMatrix/MakerMatrix/frontend/src/services/rate-limit.service.ts: RateLimitUsage, RateLimitInfo, UsagePercentage, RateLimitStatus, SupplierUsageStats, RateLimitSummary
/home/ril3y/MakerMatrix/MakerMatrix/frontend/src/services/settings.service.ts: SettingsService
/home/ril3y/MakerMatrix/MakerMatrix/frontend/src/services/supplier.service.ts: SupplierCapability, CredentialFieldDefinition, SupplierService
/home/ril3y/MakerMatrix/MakerMatrix/frontend/src/services/tasks.service.ts: CreateTaskRequest, WorkerStatus, TaskStats, TaskType
/home/ril3y/MakerMatrix/MakerMatrix/frontend/src/services/users.service.ts: UsersService
/home/ril3y/MakerMatrix/MakerMatrix/frontend/src/services/utility.service.ts: ImageUploadResponse
/home/ril3y/MakerMatrix/MakerMatrix/frontend/src/store/settingsStore.ts: useSettingsStore
/home/ril3y/MakerMatrix/MakerMatrix/frontend/src/types/auth.ts: Role, Permission
/home/ril3y/MakerMatrix/MakerMatrix/frontend/src/types/parts.ts: UpdateLocationRequest, UpdateCategoryRequest
/home/ril3y/MakerMatrix/MakerMatrix/frontend/src/types/settings.ts: CSVImportConfig, CSVImportConfigUpdate, ImportProgress


## Recommendations
1. Review identified dead code carefully before removal
2. Check if code is used in tests or configuration files
3. Verify code isn't used dynamically (string imports, etc.)
4. Consider if code is part of public API that shouldn't be removed
5. Run all tests after removing dead code to ensure nothing breaks

## False Positives
Some results may be false positives:
- Test fixtures used by pytest
- Code used in decorators or middleware
- Dynamic imports or string-based imports
- Public API exports that are meant to be used externally
- Code used in configuration files
