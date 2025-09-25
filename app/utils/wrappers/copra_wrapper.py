#!/usr/bin/env python3
"""
CoPRA Wrapper
Protein-RNA Binding Affinity Prediction
"""

import os
import sys
import json
import tempfile
import subprocess
import logging
from pathlib import Path
from typing import Dict, Any, Optional

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class CoPRAWrapper:
    """CoPRA model wrapper for protein-RNA binding affinity prediction"""
    
    def __init__(self, model_path: str = None, environment_path: str = None):
        """
        Initialize CoPRA wrapper
        
        Args:
            model_path: Path to CoPRA model directory
            environment_path: Path to CoPRA virtual environment
        """
        # Set default paths
        self.model_path = model_path or "/home/zhangliqin/RNA-Factory/models/CoPRA"
        self.environment_path = environment_path or "/home/zhangliqin/RNA-Factory/.venv_copra"
        
        # Create temp directory in project root
        self.temp_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), "temp")
        os.makedirs(self.temp_dir, exist_ok=True)
        
        # Check if environment exists
        if not os.path.exists(self.environment_path):
            raise FileNotFoundError(f"CoPRA environment not found at {self.environment_path}")
        
        # Check if model directory exists
        if not os.path.exists(self.model_path):
            raise FileNotFoundError(f"CoPRA model directory not found at {self.model_path}")
        
    
    def predict_binding_affinity(self, 
                                protein_sequence: str, 
                                rna_sequence: str,
                                protein_structure: Optional[str] = None,
                                rna_structure: Optional[str] = None) -> Dict[str, Any]:
        """
        Predict protein-RNA binding affinity using CoPRA
        
        Args:
            protein_sequence: Protein sequence string
            rna_sequence: RNA sequence string
            protein_structure: Optional protein structure (not currently used)
            rna_structure: Optional RNA structure (not currently used)
            
        Returns:
            Dictionary containing prediction results
        """
        try:
            # Validate input sequences
            if not self._is_valid_protein_sequence(protein_sequence):
                return {
                    "success": False,
                    "error": "Invalid protein sequence. Only standard amino acid codes are allowed."
                }
            
            if not self._is_valid_rna_sequence(rna_sequence):
                return {
                    "success": False,
                    "error": "Invalid RNA sequence. Only A, U, G, C are allowed."
                }
            
            # Create temporary input file
            input_data = {
                "protein_sequence": protein_sequence,
                "rna_sequence": rna_sequence,
                "protein_structure": protein_structure,
                "rna_structure": rna_structure
            }
            
            input_file = os.path.join(self.temp_dir, f"copra_input_{os.getpid()}.json")
            with open(input_file, 'w') as f:
                json.dump(input_data, f)
            
            # Prepare command
            python_path = os.path.join(self.environment_path, "bin", "python")
            inference_script = os.path.join(self.model_path, "copra_inference.py")
            
            cmd = [
                python_path,
                inference_script,
                "--input_file", input_file,
                "--output_dir", self.temp_dir
            ]
            
            logger.info(f"Running CoPRA inference with command: {' '.join(cmd)}")
            
            # Run inference
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300,  # 5 minutes timeout
                cwd=self.model_path
            )
            
            # Clean up input file
            if os.path.exists(input_file):
                os.remove(input_file)
            
            if result.returncode != 0:
                logger.error(f"CoPRA inference failed with return code {result.returncode}")
                logger.error(f"STDERR: {result.stderr}")
                return {
                    "success": False,
                    "error": f"CoPRA inference failed: {result.stderr}"
                }
            
            # Parse output
            output_file = os.path.join(self.temp_dir, "copra_results.json")
            if os.path.exists(output_file):
                with open(output_file, 'r') as f:
                    output_data = json.load(f)
                
                # Clean up output file
                os.remove(output_file)
                
                return {
                    "success": True,
                    "binding_affinity": output_data.get("binding_affinity", 0.0),
                    "confidence": output_data.get("confidence", 0.0),
                    "method": "CoPRA",
                    "raw_output": output_data.get("raw_output", ""),
                    "error": None
                }
            else:
                return {
                    "success": False,
                    "error": "CoPRA inference completed but no output file was generated"
                }
                
        except subprocess.TimeoutExpired:
            logger.error("CoPRA inference timed out")
            return {
                "success": False,
                "error": "CoPRA inference timed out"
            }
        except Exception as e:
            logger.error(f"CoPRA inference error: {str(e)}")
            return {
                "success": False,
                "error": f"CoPRA inference error: {str(e)}"
            }
        finally:
            # Clean up any remaining temporary files
            self._cleanup_temp_files()
    
    def _is_valid_protein_sequence(self, sequence: str) -> bool:
        """Validate protein sequence"""
        valid_aa = set("ACDEFGHIKLMNPQRSTVWY")
        return all(aa.upper() in valid_aa for aa in sequence)
    
    def _is_valid_rna_sequence(self, sequence: str) -> bool:
        """Validate RNA sequence"""
        valid_bases = set("AUCG")
        return all(base.upper() in valid_bases for base in sequence)
    
    def _cleanup_temp_files(self):
        """Clean up temporary files"""
        try:
            # Remove any remaining temp files
            for file in os.listdir(self.temp_dir):
                if file.startswith("copra_"):
                    file_path = os.path.join(self.temp_dir, file)
                    if os.path.isfile(file_path):
                        os.remove(file_path)
        except Exception as e:
            logger.warning(f"Error cleaning up temp files: {e}")
    
    def get_model_info(self) -> Dict[str, Any]:
        """Get model information"""
        return {
            "name": "CoPRA",
            "description": "State-of-the-art predictor of protein-RNA binding affinity based on protein language model and RNA language model",
            "version": "1.0",
            "type": "Protein-RNA Binding Affinity Prediction",
            "input_types": ["protein_sequence", "rna_sequence"],
            "output_types": ["binding_affinity", "confidence"],
            "model_path": self.model_path,
            "environment_path": self.environment_path
        }
    
    def check_dependencies(self) -> Dict[str, Any]:
        """Check if all dependencies are available"""
        try:
            python_path = os.path.join(self.environment_path, "bin", "python")
            
            # Check Python environment
            result = subprocess.run(
                [python_path, "-c", "import torch; print(torch.__version__)"],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            pytorch_version = result.stdout.strip() if result.returncode == 0 else "Not available"
            
            # Check if weights are available
            weights_path = os.path.join(self.model_path, "weights")
            weights_available = os.path.exists(weights_path) and len(os.listdir(weights_path)) > 0
            
            return {
                "available": True,
                "pytorch_version": pytorch_version,
                "weights_available": weights_available,
                "model_path": self.model_path,
                "environment_path": self.environment_path
            }
        except Exception as e:
            return {
                "available": False,
                "error": str(e),
                "pytorch_version": "Not available",
                "weights_available": False
            }
