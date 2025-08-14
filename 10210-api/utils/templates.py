"""
Message Template Engine with Multiple Random Samples Support
Handles variable substitution and random sample selection
"""

import re
import random
import logging
from typing import List, Dict, Tuple, Optional, Any
from jinja2 import Template, Environment, BaseLoader, TemplateError

logger = logging.getLogger(__name__)

class MessageTemplateEngine:
    """Template engine for processing message samples with variable substitution"""
    
    def __init__(self):
        self.env = Environment(loader=BaseLoader())
        self.variable_pattern = re.compile(r'\{([^}]+)\}')
    
    def extract_variables(self, template: str) -> List[str]:
        """Extract variable names from template"""
        variables = self.variable_pattern.findall(template)
        return list(set(variables))  # Remove duplicates
    
    def validate_template(self, template: str, sample_data: Dict[str, Any] = None) -> Dict[str, Any]:
        """Validate template syntax and variables"""
        try:
            # Extract variables
            variables_found = self.extract_variables(template)
            
            # Test Jinja2 template compilation
            jinja_template = self.env.from_string(template)
            
            validation_result = {
                "is_valid": True,
                "variables_found": variables_found,
                "variables_missing": [],
                "error_message": None
            }
            
            # Test rendering if sample data provided
            if sample_data:
                missing_vars = [var for var in variables_found if var not in sample_data]
                validation_result["variables_missing"] = missing_vars
                
                if missing_vars:
                    validation_result["is_valid"] = False
                    validation_result["error_message"] = f"Missing variables: {', '.join(missing_vars)}"
                else:
                    try:
                        # Test render
                        rendered = jinja_template.render(**sample_data)
                        validation_result["test_render"] = rendered
                    except Exception as e:
                        validation_result["is_valid"] = False
                        validation_result["error_message"] = f"Render error: {str(e)}"
            
            return validation_result
            
        except TemplateError as e:
            return {
                "is_valid": False,
                "variables_found": [],
                "variables_missing": [],
                "error_message": f"Template syntax error: {str(e)}"
            }
        except Exception as e:
            return {
                "is_valid": False,
                "variables_found": [],
                "variables_missing": [],
                "error_message": f"Validation error: {str(e)}"
            }
    
    def render_template(self, template: str, variables: Dict[str, Any]) -> str:
        """Render template with variables"""
        try:
            jinja_template = self.env.from_string(template)
            rendered = jinja_template.render(**variables)
            return rendered.strip()
        except Exception as e:
            logger.error(f"Template rendering error: {str(e)}")
            raise ValueError(f"Template rendering failed: {str(e)}")
    
    def select_random_sample(self, samples: List[str]) -> Tuple[int, str]:
        """Select random sample from list and return index and text"""
        if not samples:
            raise ValueError("No samples provided")
        
        index = random.randint(0, len(samples) - 1)
        return index, samples[index]
    
    def process_message_with_samples(
        self,
        row_data: Dict[str, Any],
        campaign_samples: Optional[List[str]] = None,
        csv_samples_column: Optional[str] = None,
        csv_sample_separator: str = "|"
    ) -> Tuple[int, str, str]:
        """
        Process message with random sample selection and variable substitution
        
        Args:
            row_data: Dictionary containing row data from CSV
            campaign_samples: List of campaign-level message samples
            csv_samples_column: Name of CSV column containing samples
            csv_sample_separator: Separator for multiple samples in CSV
            
        Returns:
            Tuple of (sample_index, sample_text, final_message)
        """
        try:
            # Determine available samples
            available_samples = self._get_available_samples(
                row_data, campaign_samples, csv_samples_column, csv_sample_separator
            )
            
            if not available_samples:
                raise ValueError("No message samples available")
            
            # Select random sample
            sample_index, selected_sample = self.select_random_sample(available_samples)
            
            # Render template with variables
            final_message = self.render_template(selected_sample, row_data)
            
            logger.debug(f"Selected sample {sample_index}: {selected_sample[:50]}...")
            
            return sample_index, selected_sample, final_message
            
        except Exception as e:
            logger.error(f"Message processing error: {str(e)}")
            raise
    
    def _get_available_samples(
        self,
        row_data: Dict[str, Any],
        campaign_samples: Optional[List[str]],
        csv_samples_column: Optional[str],
        csv_sample_separator: str
    ) -> List[str]:
        """Get available samples based on priority: CSV samples > Campaign samples"""
        
        # Priority 1: CSV samples (per-row)
        if csv_samples_column and csv_samples_column in row_data:
            csv_samples_raw = row_data[csv_samples_column]
            if csv_samples_raw and isinstance(csv_samples_raw, str):
                csv_samples = [
                    sample.strip() 
                    for sample in csv_samples_raw.split(csv_sample_separator)
                    if sample.strip()
                ]
                if csv_samples:
                    return csv_samples
        
        # Priority 2: Campaign samples
        if campaign_samples:
            return campaign_samples
        
        # Fallback: Empty list (will cause error)
        return []
    
    def preview_message(
        self,
        template: str,
        sample_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Preview how a template will render with sample data"""
        try:
            validation = self.validate_template(template, sample_data)
            
            if validation["is_valid"]:
                rendered = self.render_template(template, sample_data)
                return {
                    "original_template": template,
                    "sample_data": sample_data,
                    "rendered_message": rendered,
                    "variables_used": validation["variables_found"],
                    "variables_missing": validation["variables_missing"],
                    "is_valid": True,
                    "character_count": len(rendered),
                    "word_count": len(rendered.split())
                }
            else:
                return {
                    "original_template": template,
                    "sample_data": sample_data,
                    "rendered_message": None,
                    "variables_used": validation["variables_found"],
                    "variables_missing": validation["variables_missing"],
                    "is_valid": False,
                    "error_message": validation["error_message"]
                }
                
        except Exception as e:
            return {
                "original_template": template,
                "sample_data": sample_data,
                "rendered_message": None,
                "variables_used": [],
                "variables_missing": [],
                "is_valid": False,
                "error_message": str(e)
            }
    
    def analyze_samples(self, samples: List[str]) -> Dict[str, Any]:
        """Analyze a list of message samples"""
        if not samples:
            return {"error": "No samples provided"}
        
        analysis = {
            "total_samples": len(samples),
            "samples_analysis": [],
            "common_variables": [],
            "all_variables": set(),
            "avg_length": 0,
            "min_length": float('inf'),
            "max_length": 0
        }
        
        total_length = 0
        all_variables = set()
        
        for i, sample in enumerate(samples):
            variables = self.extract_variables(sample)
            length = len(sample)
            
            analysis["samples_analysis"].append({
                "index": i,
                "text": sample,
                "length": length,
                "word_count": len(sample.split()),
                "variables": variables,
                "variable_count": len(variables)
            })
            
            all_variables.update(variables)
            total_length += length
            analysis["min_length"] = min(analysis["min_length"], length)
            analysis["max_length"] = max(analysis["max_length"], length)
        
        analysis["avg_length"] = total_length / len(samples)
        analysis["all_variables"] = list(all_variables)
        
        # Find common variables (present in all samples)
        if samples:
            common_vars = set(self.extract_variables(samples[0]))
            for sample in samples[1:]:
                common_vars &= set(self.extract_variables(sample))
            analysis["common_variables"] = list(common_vars)
        
        return analysis
    
    def generate_sample_variations(
        self,
        base_template: str,
        variations: Dict[str, List[str]],
        max_combinations: int = 50
    ) -> List[str]:
        """
        Generate template variations by substituting parts
        
        Args:
            base_template: Base template with variation markers
            variations: Dict of {marker: [options]} for substitution
            max_combinations: Maximum number of variations to generate
        """
        try:
            import itertools
            
            # Get all possible combinations
            keys = list(variations.keys())
            values = [variations[key] for key in keys]
            
            combinations = list(itertools.product(*values))
            
            # Limit combinations
            if len(combinations) > max_combinations:
                combinations = random.sample(combinations, max_combinations)
            
            generated_samples = []
            
            for combination in combinations:
                template = base_template
                for key, value in zip(keys, combination):
                    template = template.replace(f"{{{key}}}", value)
                
                generated_samples.append(template)
            
            return generated_samples
            
        except Exception as e:
            logger.error(f"Sample generation error: {str(e)}")
            return [base_template]  # Return original as fallback
