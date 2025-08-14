"""
Data validation utilities for campaign management
Phone number validation, data sanitization, and business rule checks
"""

import re
import logging
from typing import List, Dict, Any, Optional, Tuple
from phonenumbers import parse, is_valid_number, format_number, PhoneNumberFormat
import phonenumbers

logger = logging.getLogger(__name__)

class PhoneValidator:
    """Phone number validation and formatting"""
    
    def __init__(self, default_region: str = "NG"):  # Nigeria as default
        self.default_region = default_region
        self.phone_pattern = re.compile(r'^[\d\+\-\s\(\)]+$')
    
    def validate_phone(self, phone: str, region: Optional[str] = None) -> Dict[str, Any]:
        """Validate phone number and return detailed result"""
        if not phone:
            return {
                "valid": False,
                "error": "Phone number is empty",
                "formatted": None,
                "international": None
            }
        
        try:
            # Clean phone number
            cleaned_phone = self.clean_phone(phone)
            
            # Parse phone number
            region = region or self.default_region
            parsed = parse(cleaned_phone, region)
            
            # Validate
            is_valid = is_valid_number(parsed)
            
            if is_valid:
                # Format phone numbers
                national = format_number(parsed, PhoneNumberFormat.NATIONAL)
                international = format_number(parsed, PhoneNumberFormat.INTERNATIONAL)
                e164 = format_number(parsed, PhoneNumberFormat.E164)
                
                return {
                    "valid": True,
                    "error": None,
                    "formatted": e164.replace('+', ''),  # Remove + for WhatsApp format
                    "international": international,
                    "national": national,
                    "country_code": parsed.country_code,
                    "region": region
                }
            else:
                return {
                    "valid": False,
                    "error": "Invalid phone number format",
                    "formatted": None,
                    "international": None
                }
                
        except phonenumbers.NumberParseException as e:
            return {
                "valid": False,
                "error": f"Phone parsing error: {str(e)}",
                "formatted": None,
                "international": None
            }
        except Exception as e:
            logger.error(f"Phone validation error: {str(e)}")
            return {
                "valid": False,
                "error": f"Validation error: {str(e)}",
                "formatted": None,
                "international": None
            }
    
    def clean_phone(self, phone: str) -> str:
        """Clean phone number string"""
        if not phone:
            return ""
        
        # Convert to string and strip
        phone = str(phone).strip()
        
        # Remove common separators but keep + and digits
        phone = re.sub(r'[\s\-\(\)]+', '', phone)
        
        return phone
    
    def batch_validate_phones(self, phones: List[str], region: Optional[str] = None) -> List[Dict[str, Any]]:
        """Validate multiple phone numbers"""
        results = []
        
        for i, phone in enumerate(phones):
            result = self.validate_phone(phone, region)
            result['index'] = i
            result['original'] = phone
            results.append(result)
        
        return results

class DataValidator:
    """General data validation for campaign data"""
    
    def __init__(self):
        self.phone_validator = PhoneValidator()
        
        # Common required fields
        self.required_fields = ['phone_number']
        self.recommended_fields = ['name']
        
    def validate_campaign_data(self, data: List[Dict[str, Any]], column_mapping: Dict[str, str]) -> Dict[str, Any]:
        """Validate entire campaign dataset"""
        try:
            if not data:
                return {
                    "valid": False,
                    "error": "No data provided",
                    "validation_results": []
                }
            
            # Map columns
            mapped_data = self._map_columns(data, column_mapping)
            
            # Validate each row
            validation_results = []
            valid_count = 0
            
            for i, row in enumerate(mapped_data):
                row_result = self.validate_row(row, i + 1)
                validation_results.append(row_result)
                
                if row_result["valid"]:
                    valid_count += 1
            
            # Calculate statistics
            total_rows = len(validation_results)
            invalid_count = total_rows - valid_count
            
            # Overall validation result
            overall_valid = valid_count > 0 and invalid_count < (total_rows * 0.1)  # Allow up to 10% invalid
            
            return {
                "valid": overall_valid,
                "total_rows": total_rows,
                "valid_rows": valid_count,
                "invalid_rows": invalid_count,
                "success_rate": round((valid_count / total_rows) * 100, 2) if total_rows > 0 else 0,
                "validation_results": validation_results,
                "summary": self._generate_validation_summary(validation_results)
            }
            
        except Exception as e:
            logger.error(f"Campaign data validation error: {str(e)}")
            return {
                "valid": False,
                "error": f"Validation error: {str(e)}",
                "validation_results": []
            }
    
    def validate_row(self, row: Dict[str, Any], row_number: int) -> Dict[str, Any]:
        """Validate individual data row"""
        errors = []
        warnings = []
        processed_data = {}
        
        # Validate required fields
        for field in self.required_fields:
            if field not in row or not row[field]:
                errors.append(f"Missing required field: {field}")
            else:
                processed_data[field] = row[field]
        
        # Validate phone number if present
        if 'phone_number' in row and row['phone_number']:
            phone_value = str(row['phone_number'])
            
            # Check if it's a WhatsApp group ID (contains @g.us or has group ID pattern)
            is_group = '@g.us' in phone_value or (phone_value.count('-') >= 1 and len(phone_value) > 15)
            
            # Also check for is_group flag in the row
            if 'is_group' in row and str(row.get('is_group', '')).lower() in ['true', '1', 'yes']:
                is_group = True
            
            if is_group:
                # For groups, just pass through the group ID
                processed_data['phone_number'] = phone_value
                processed_data['is_group'] = True
            else:
                # For regular phone numbers, validate
                phone_validation = self.phone_validator.validate_phone(phone_value)
                
                if phone_validation["valid"]:
                    processed_data['phone_number'] = phone_validation["formatted"]
                    processed_data['phone_international'] = phone_validation["international"]
                else:
                    errors.append(f"Invalid phone number: {phone_validation['error']}")
        
        # Validate name if present
        if 'name' in row:
            name = str(row['name']).strip()
            if name:
                processed_data['name'] = name
            else:
                warnings.append("Name field is empty")
        else:
            warnings.append("Name field not provided")
        
        # Check for message samples
        if 'message_samples' in row and row['message_samples']:
            samples = self._parse_message_samples(row['message_samples'])
            if samples:
                processed_data['message_samples'] = samples
            else:
                warnings.append("Could not parse message samples")
        
        # Copy other fields
        for key, value in row.items():
            if key not in processed_data and key not in ['phone_number', 'name', 'message_samples']:
                processed_data[key] = value
        
        # Determine row validity
        is_valid = len(errors) == 0
        
        return {
            "row_number": row_number,
            "valid": is_valid,
            "errors": errors,
            "warnings": warnings,
            "processed_data": processed_data,
            "original_data": row
        }
    
    def _map_columns(self, data: List[Dict[str, Any]], column_mapping: Dict[str, str]) -> List[Dict[str, Any]]:
        """Map column names according to mapping"""
        mapped_data = []
        
        for row in data:
            mapped_row = {}
            
            # Apply column mapping
            for target_col, source_col in column_mapping.items():
                if source_col in row:
                    mapped_row[target_col] = row[source_col]
            
            # Include unmapped columns
            for key, value in row.items():
                if key not in column_mapping.values():
                    mapped_row[key] = value
            
            mapped_data.append(mapped_row)
        
        return mapped_data
    
    def _parse_message_samples(self, samples_text: str, separator: str = "|") -> List[str]:
        """Parse message samples from text"""
        if not samples_text:
            return []
        
        try:
            samples = [sample.strip() for sample in str(samples_text).split(separator) if sample.strip()]
            return samples
        except Exception:
            return []
    
    def _generate_validation_summary(self, validation_results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Generate validation summary"""
        if not validation_results:
            return {}
        
        # Count error types
        error_types = {}
        warning_types = {}
        
        for result in validation_results:
            for error in result.get("errors", []):
                error_types[error] = error_types.get(error, 0) + 1
            
            for warning in result.get("warnings", []):
                warning_types[warning] = warning_types.get(warning, 0) + 1
        
        return {
            "common_errors": sorted(error_types.items(), key=lambda x: x[1], reverse=True)[:5],
            "common_warnings": sorted(warning_types.items(), key=lambda x: x[1], reverse=True)[:5],
            "total_error_types": len(error_types),
            "total_warning_types": len(warning_types)
        }
    
    def validate_template_variables(self, template: str, sample_data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate that template variables exist in data"""
        from utils.templates import MessageTemplateEngine
        
        try:
            engine = MessageTemplateEngine()
            variables = engine.extract_variables(template)
            
            missing_variables = [var for var in variables if var not in sample_data]
            available_variables = [var for var in variables if var in sample_data]
            
            return {
                "valid": len(missing_variables) == 0,
                "variables_found": variables,
                "available_variables": available_variables,
                "missing_variables": missing_variables,
                "data_fields": list(sample_data.keys())
            }
            
        except Exception as e:
            logger.error(f"Template validation error: {str(e)}")
            return {
                "valid": False,
                "error": str(e),
                "variables_found": [],
                "available_variables": [],
                "missing_variables": []
            }

class BusinessRuleValidator:
    """Business rule validation for campaigns"""
    
    def __init__(self):
        self.max_daily_messages = 1000
        self.max_campaign_size = 10000
        self.min_delay_seconds = 1
        self.max_delay_seconds = 300
    
    def validate_campaign_settings(self, campaign_data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate campaign settings against business rules"""
        errors = []
        warnings = []
        
        # Validate message count
        total_rows = campaign_data.get("total_rows", 0)
        if total_rows > self.max_campaign_size:
            errors.append(f"Campaign too large. Maximum: {self.max_campaign_size} messages")
        
        # Validate delay settings
        delay_seconds = campaign_data.get("delay_seconds", 5)
        if delay_seconds < self.min_delay_seconds:
            errors.append(f"Delay too short. Minimum: {self.min_delay_seconds} seconds")
        elif delay_seconds > self.max_delay_seconds:
            warnings.append(f"Delay very long. Maximum recommended: {self.max_delay_seconds} seconds")
        
        # Validate daily message limit
        max_daily = campaign_data.get("max_daily_messages", 1000)
        if max_daily > self.max_daily_messages:
            warnings.append(f"High daily limit. Recommended maximum: {self.max_daily_messages}")
        
        # Validate session
        session_name = campaign_data.get("session_name")
        if not session_name:
            errors.append("Session name is required")
        
        # Estimate completion time
        if total_rows > 0 and delay_seconds > 0:
            estimated_hours = (total_rows * delay_seconds) / 3600
            if estimated_hours > 24:
                warnings.append(f"Campaign will take approximately {estimated_hours:.1f} hours to complete")
        
        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings,
            "estimated_duration_hours": estimated_hours if 'estimated_hours' in locals() else 0
        }
    
    def validate_session_capacity(self, session_name: str, new_campaign_size: int) -> Dict[str, Any]:
        """Validate if session can handle new campaign"""
        # TODO: Implement session capacity checking
        # This would check active campaigns on the session
        
        return {
            "valid": True,
            "current_load": 0,
            "capacity_available": True,
            "recommendation": "Session ready for new campaign"
        }
