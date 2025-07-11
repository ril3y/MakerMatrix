"""
Supplier Compliance Validator

Framework-wide validation for supplier data consistency across all suppliers.
Ensures adherence to standardization patterns and data quality requirements.
"""

import logging
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime
import inspect

from MakerMatrix.services.data.unified_column_mapper import UnifiedColumnMapper
from MakerMatrix.services.data.supplier_data_mapper import SupplierDataMapper
from MakerMatrix.suppliers.lcsc import LCSCSupplier
from MakerMatrix.suppliers.mouser import MouserSupplier
from MakerMatrix.suppliers.digikey import DigiKeySupplier
from MakerMatrix.suppliers.base import BaseSupplier

logger = logging.getLogger(__name__)


@dataclass
class ValidationResult:
    """Result of a single validation check"""
    check_name: str
    passed: bool
    score: float  # 0.0 to 1.0
    message: str
    details: Dict[str, Any] = None


@dataclass  
class ValidationReport:
    """Comprehensive validation report for supplier compliance"""
    supplier_name: str
    overall_score: float  # 0.0 to 1.0
    total_checks: int
    passed_checks: int
    failed_checks: int
    results: List[ValidationResult]
    timestamp: datetime
    summary: str


@dataclass
class FrameworkComplianceReport:
    """Framework-wide compliance report for all suppliers"""
    overall_score: float
    supplier_reports: Dict[str, ValidationReport]
    framework_issues: List[str]
    recommendations: List[str]
    timestamp: datetime


class SupplierComplianceValidator:
    """Framework-wide validation for supplier data consistency"""
    
    def __init__(self):
        self.column_mapper = UnifiedColumnMapper()
        self.data_mapper = SupplierDataMapper()
        self.suppliers = {
            'lcsc': LCSCSupplier(),
            'mouser': MouserSupplier(),  
            'digikey': DigiKeySupplier()
        }
    
    def validate_supplier_implementation(self, supplier_name: str) -> ValidationReport:
        """Comprehensive supplier compliance check"""
        supplier_name_lower = supplier_name.lower()
        
        if supplier_name_lower not in self.suppliers:
            return ValidationReport(
                supplier_name=supplier_name,
                overall_score=0.0,
                total_checks=0,
                passed_checks=0,
                failed_checks=1,
                results=[ValidationResult(
                    check_name="supplier_exists",
                    passed=False,
                    score=0.0,
                    message=f"Supplier '{supplier_name}' not found in registry"
                )],
                timestamp=datetime.now(),
                summary="Supplier not found"
            )
        
        supplier = self.suppliers[supplier_name_lower]
        results = []
        
        # Run all validation checks
        results.append(self._check_uses_unified_column_mapper(supplier, supplier_name))
        results.append(self._check_uses_supplier_data_mapper(supplier, supplier_name))
        results.append(self._check_import_order_file_implementation(supplier, supplier_name))
        results.append(self._check_additional_properties_builder(supplier, supplier_name))
        results.append(self._check_column_mapping_configuration(supplier_name_lower))
        results.append(self._check_standardized_error_handling(supplier, supplier_name))
        results.append(self._check_defensive_programming_patterns(supplier, supplier_name))
        
        # Calculate overall score
        total_score = sum(result.score for result in results)
        overall_score = total_score / len(results) if results else 0.0
        
        passed_checks = sum(1 for result in results if result.passed)
        failed_checks = len(results) - passed_checks
        
        # Generate summary
        if overall_score >= 0.9:
            summary = "Excellent compliance - fully standardized"
        elif overall_score >= 0.7:
            summary = "Good compliance - minor issues found"
        elif overall_score >= 0.5:
            summary = "Moderate compliance - significant improvements needed"
        else:
            summary = "Poor compliance - major standardization issues"
        
        return ValidationReport(
            supplier_name=supplier_name,
            overall_score=overall_score,
            total_checks=len(results),
            passed_checks=passed_checks,
            failed_checks=failed_checks,
            results=results,
            timestamp=datetime.now(),
            summary=summary
        )
    
    def _check_uses_unified_column_mapper(self, supplier: BaseSupplier, supplier_name: str) -> ValidationResult:
        """Check if supplier uses UnifiedColumnMapper"""
        try:
            # Check if import_order_file method contains UnifiedColumnMapper usage
            if hasattr(supplier, 'import_order_file'):
                source = inspect.getsource(supplier.import_order_file)
                if 'UnifiedColumnMapper' in source and 'map_columns' in source:
                    return ValidationResult(
                        check_name="uses_unified_column_mapper",
                        passed=True,
                        score=1.0,
                        message=f"{supplier_name} correctly uses UnifiedColumnMapper",
                        details={"pattern_found": True}
                    )
            
            return ValidationResult(
                check_name="uses_unified_column_mapper",
                passed=False,
                score=0.0,
                message=f"{supplier_name} does not use UnifiedColumnMapper",
                details={"pattern_found": False}
            )
        except Exception as e:
            return ValidationResult(
                check_name="uses_unified_column_mapper",
                passed=False,
                score=0.0,
                message=f"Error checking UnifiedColumnMapper usage: {e}",
                details={"error": str(e)}
            )
    
    def _check_uses_supplier_data_mapper(self, supplier: BaseSupplier, supplier_name: str) -> ValidationResult:
        """Check if supplier uses SupplierDataMapper for standardization"""
        try:
            if hasattr(supplier, 'import_order_file'):
                source = inspect.getsource(supplier.import_order_file)
                if 'SupplierDataMapper' in source and 'map_supplier_result_to_part_data' in source:
                    return ValidationResult(
                        check_name="uses_supplier_data_mapper",
                        passed=True,
                        score=1.0,
                        message=f"{supplier_name} correctly uses SupplierDataMapper",
                        details={"standardization_found": True}
                    )
            
            return ValidationResult(
                check_name="uses_supplier_data_mapper",
                passed=False,
                score=0.0,
                message=f"{supplier_name} does not use SupplierDataMapper",
                details={"standardization_found": False}
            )
        except Exception as e:
            return ValidationResult(
                check_name="uses_supplier_data_mapper",
                passed=False,
                score=0.0,
                message=f"Error checking SupplierDataMapper usage: {e}",
                details={"error": str(e)}
            )
    
    def _check_import_order_file_implementation(self, supplier: BaseSupplier, supplier_name: str) -> ValidationResult:
        """Check import_order_file method implementation quality"""
        try:
            if not hasattr(supplier, 'import_order_file'):
                return ValidationResult(
                    check_name="import_order_file_implementation",
                    passed=False,
                    score=0.0,
                    message=f"{supplier_name} missing import_order_file method"
                )
            
            source = inspect.getsource(supplier.import_order_file)
            
            # Check for key implementation patterns
            patterns = {
                'pandas_usage': 'pd.read_csv' in source or 'pd.read_excel' in source,
                'error_handling': 'try:' in source and 'except' in source,
                'return_import_result': 'ImportResult' in source,
                'defensive_programming': 'strip()' in source or '.get(' in source,
                'data_validation': 'validate_required_columns' in source or 'required_fields' in source
            }
            
            passed_patterns = sum(patterns.values())
            total_patterns = len(patterns)
            score = passed_patterns / total_patterns
            
            return ValidationResult(
                check_name="import_order_file_implementation",
                passed=score >= 0.8,
                score=score,
                message=f"{supplier_name} import implementation score: {passed_patterns}/{total_patterns}",
                details=patterns
            )
        except Exception as e:
            return ValidationResult(
                check_name="import_order_file_implementation",
                passed=False,
                score=0.0,
                message=f"Error checking import implementation: {e}",
                details={"error": str(e)}
            )
    
    def _check_additional_properties_builder(self, supplier: BaseSupplier, supplier_name: str) -> ValidationResult:
        """Check if supplier has additional_properties builder method"""
        try:
            supplier_lower = supplier_name.lower()
            expected_method = f"_build_{supplier_lower}_additional_properties"
            
            if hasattr(supplier, expected_method):
                method = getattr(supplier, expected_method)
                source = inspect.getsource(method)
                
                # Check for required structure elements
                required_elements = {
                    'supplier_data': "'supplier_data'" in source,
                    'order_info': "'order_info'" in source,
                    'technical_specs': "'technical_specs'" in source or "'compliance'" in source,
                    'proper_supplier_name': f"'{supplier_name}'" in source or f"'{supplier_lower.upper()}'" in source
                }
                
                passed_elements = sum(required_elements.values())
                total_elements = len(required_elements)
                score = passed_elements / total_elements
                
                return ValidationResult(
                    check_name="additional_properties_builder",
                    passed=score >= 0.75,
                    score=score,
                    message=f"{supplier_name} additional_properties builder score: {passed_elements}/{total_elements}",
                    details=required_elements
                )
            else:
                return ValidationResult(
                    check_name="additional_properties_builder",
                    passed=False,
                    score=0.0,
                    message=f"{supplier_name} missing {expected_method} method"
                )
        except Exception as e:
            return ValidationResult(
                check_name="additional_properties_builder",
                passed=False,
                score=0.0,
                message=f"Error checking additional_properties builder: {e}",
                details={"error": str(e)}
            )
    
    def _check_column_mapping_configuration(self, supplier_name: str) -> ValidationResult:
        """Check if supplier has proper column mapping configuration"""
        try:
            mappings = self.column_mapper.get_supplier_specific_mappings(supplier_name)
            
            if not mappings:
                return ValidationResult(
                    check_name="column_mapping_configuration",
                    passed=False,
                    score=0.0,
                    message=f"{supplier_name} has no specific column mappings configured"
                )
            
            # Check for essential field mappings
            essential_fields = ['part_number', 'manufacturer_part_number', 'description', 'quantity']
            configured_fields = [field for field in essential_fields if field in mappings]
            
            score = len(configured_fields) / len(essential_fields)
            
            return ValidationResult(
                check_name="column_mapping_configuration",
                passed=score >= 0.75,
                score=score,
                message=f"{supplier_name} column mapping coverage: {len(configured_fields)}/{len(essential_fields)}",
                details={
                    "configured_fields": configured_fields,
                    "missing_fields": [f for f in essential_fields if f not in configured_fields],
                    "total_mappings": len(mappings)
                }
            )
        except Exception as e:
            return ValidationResult(
                check_name="column_mapping_configuration",
                passed=False,
                score=0.0,
                message=f"Error checking column mapping configuration: {e}",
                details={"error": str(e)}
            )
    
    def _check_standardized_error_handling(self, supplier: BaseSupplier, supplier_name: str) -> ValidationResult:
        """Check for standardized error handling patterns"""
        try:
            if not hasattr(supplier, 'import_order_file'):
                return ValidationResult(
                    check_name="standardized_error_handling",
                    passed=False,
                    score=0.0,
                    message=f"{supplier_name} missing import_order_file method"
                )
            
            source = inspect.getsource(supplier.import_order_file)
            
            # Check for error handling patterns
            patterns = {
                'try_except_blocks': source.count('try:') >= 1 and source.count('except') >= 1,
                'import_result_error': 'ImportResult(' in source and 'success=False' in source,
                'logging_errors': 'logger.' in source,
                'defensive_encoding': 'decode(' in source and 'utf-8' in source,
                'graceful_degradation': 'continue' in source or 'pass' in source
            }
            
            passed_patterns = sum(patterns.values())
            total_patterns = len(patterns)
            score = passed_patterns / total_patterns
            
            return ValidationResult(
                check_name="standardized_error_handling",
                passed=score >= 0.6,
                score=score,
                message=f"{supplier_name} error handling score: {passed_patterns}/{total_patterns}",
                details=patterns
            )
        except Exception as e:
            return ValidationResult(
                check_name="standardized_error_handling",
                passed=False,
                score=0.0,
                message=f"Error checking error handling: {e}",
                details={"error": str(e)}
            )
    
    def _check_defensive_programming_patterns(self, supplier: BaseSupplier, supplier_name: str) -> ValidationResult:
        """Check for defensive programming patterns"""
        try:
            if not hasattr(supplier, 'import_order_file'):
                return ValidationResult(
                    check_name="defensive_programming_patterns",
                    passed=False,
                    score=0.0,
                    message=f"{supplier_name} missing import_order_file method"
                )
            
            source = inspect.getsource(supplier.import_order_file)
            
            # Check for defensive patterns
            patterns = {
                'null_safety': '.get(' in source,
                'data_cleaning': '.strip()' in source,
                'type_conversion_safety': 'try:' in source and ('int(' in source or 'float(' in source),
                'empty_check': 'if not' in source or 'is None' in source,
                'pandas_na_handling': 'pd.isna' in source or '.dropna' in source or '.fillna' in source
            }
            
            passed_patterns = sum(patterns.values())
            total_patterns = len(patterns)
            score = passed_patterns / total_patterns
            
            return ValidationResult(
                check_name="defensive_programming_patterns",
                passed=score >= 0.6,
                score=score,
                message=f"{supplier_name} defensive programming score: {passed_patterns}/{total_patterns}",
                details=patterns
            )
        except Exception as e:
            return ValidationResult(
                check_name="defensive_programming_patterns",
                passed=False,
                score=0.0,
                message=f"Error checking defensive patterns: {e}",
                details={"error": str(e)}
            )
    
    def validate_data_consistency(self, import_data: List[Dict], enrichment_data: List[Dict]) -> bool:
        """Ensure import and enrichment produce consistent structures"""
        if not import_data or not enrichment_data:
            return False
        
        try:
            # Check structure consistency
            import_sample = import_data[0]
            enrichment_sample = enrichment_data[0]
            
            # Both should have additional_properties with consistent structure
            import_props = import_sample.get('additional_properties', {})
            enrichment_props = enrichment_sample.get('additional_properties', {})
            
            # Check for consistent top-level structure
            expected_sections = ['supplier_data']
            
            for section in expected_sections:
                if section not in import_props or section not in enrichment_props:
                    return False
            
            return True
        except Exception as e:
            logger.error(f"Error validating data consistency: {e}")
            return False
    
    def generate_compliance_report(self) -> FrameworkComplianceReport:
        """Generate framework-wide compliance report"""
        supplier_reports = {}
        
        # Validate each supplier
        for supplier_name in self.suppliers.keys():
            supplier_reports[supplier_name] = self.validate_supplier_implementation(supplier_name)
        
        # Calculate overall framework score
        scores = [report.overall_score for report in supplier_reports.values()]
        overall_score = sum(scores) / len(scores) if scores else 0.0
        
        # Identify framework-wide issues
        framework_issues = []
        all_failed_checks = []
        
        for report in supplier_reports.values():
            failed_results = [r for r in report.results if not r.passed]
            all_failed_checks.extend([r.check_name for r in failed_results])
        
        # Find common issues across suppliers
        from collections import Counter
        check_failures = Counter(all_failed_checks)
        for check_name, failure_count in check_failures.items():
            if failure_count >= 2:  # Issue in multiple suppliers
                framework_issues.append(f"Common issue: {check_name} failed in {failure_count} suppliers")
        
        # Generate recommendations
        recommendations = []
        if overall_score < 0.7:
            recommendations.append("Review and update supplier implementations to follow standardized patterns")
        if 'uses_unified_column_mapper' in check_failures:
            recommendations.append("Ensure all suppliers use UnifiedColumnMapper for column detection")
        if 'uses_supplier_data_mapper' in check_failures:
            recommendations.append("Ensure all suppliers use SupplierDataMapper for data standardization")
        if 'additional_properties_builder' in check_failures:
            recommendations.append("Implement consistent additional_properties structure across all suppliers")
        
        return FrameworkComplianceReport(
            overall_score=overall_score,
            supplier_reports=supplier_reports,
            framework_issues=framework_issues,
            recommendations=recommendations,
            timestamp=datetime.now()
        )