#!/usr/bin/env python3
"""
RNAMPNN Wrapper
RNA Sequence Prediction from 3D Structure
"""

import os
import sys
import json
import tempfile
import subprocess
import logging
import numpy as np
import torch
from pathlib import Path
from typing import Dict, Any, Optional, List, Tuple

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class RNAMPNNWrapper:
    """RNAMPNN model wrapper for RNA sequence prediction from 3D structure"""
    
    def __init__(self, model_path: str = None, environment_path: str = None):
        """
        Initialize RNAMPNN wrapper
        
        Args:
            model_path: Path to RNAMPNN model directory
            environment_path: Path to RNAMPNN virtual environment
        """
        # Set default paths
        self.model_path = model_path or str(Path(__file__).parent.parent.parent.parent / "models" / "RNA-MPNN")
        self.environment_path = environment_path or str(Path(__file__).parent.parent.parent.parent / ".venv_rnampnn")
        
        # Create temp directory in project root
        self.temp_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), "temp")
        os.makedirs(self.temp_dir, exist_ok=True)
        
        # Check if environment exists
        if not os.path.exists(self.environment_path):
            raise FileNotFoundError(f"RNAMPNN environment not found at {self.environment_path}")
        
        # Check if model directory exists
        if not os.path.exists(self.model_path):
            raise FileNotFoundError(f"RNAMPNN model directory not found at {self.model_path}")
        
        # Check if model checkpoint exists
        self.checkpoint_path = os.path.join(self.model_path, "out", "checkpoints", "RNAMPNN-X", "Final-V0.ckpt")
        if not os.path.exists(self.checkpoint_path):
            raise FileNotFoundError(f"Model checkpoint not found at {self.checkpoint_path}")
        
        logger.info(f"RNAMPNN wrapper initialized with model_path: {self.model_path}")
        logger.info(f"RNAMPNN wrapper initialized with environment_path: {self.environment_path}")
        logger.info(f"RNAMPNN wrapper using temp_dir: {self.temp_dir}")
        logger.info(f"RNAMPNN wrapper using checkpoint: {self.checkpoint_path}")
    
    def _run_inference_script(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Run RNAMPNN inference script in virtual environment
        
        Args:
            input_data: Input data for inference
            
        Returns:
            Dictionary containing the result
        """
        try:
            # Create temporary input file
            input_file = os.path.join(self.temp_dir, f"rnampnn_input_{os.getpid()}.json")
            with open(input_file, 'w') as f:
                json.dump(input_data, f)
            
            # Create temporary output file
            output_file = os.path.join(self.temp_dir, f"rnampnn_output_{os.getpid()}.json")
            
            # Prepare command
            python_path = os.path.join(self.environment_path, "bin", "python")
            inference_script = os.path.join(self.model_path, "rnampnn_inference.py")
            
            cmd = [
                python_path,
                inference_script,
                "--input_file", input_file,
                "--output_file", output_file,
                "--checkpoint", self.checkpoint_path
            ]
            
            logger.info(f"Running RNAMPNN inference with command: {' '.join(cmd)}")
            
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
                logger.error(f"RNAMPNN inference failed with return code {result.returncode}")
                logger.error(f"STDERR: {result.stderr}")
                return {
                    "success": False,
                    "error": f"RNAMPNN inference failed: {result.stderr}"
                }
            
            # Parse output
            if os.path.exists(output_file):
                with open(output_file, 'r') as f:
                    output_data = json.load(f)
                
                # Clean up output file
                os.remove(output_file)
                
                return output_data
            else:
                return {
                    "success": False,
                    "error": "No output file generated"
                }
                
        except subprocess.TimeoutExpired:
            logger.error("RNAMPNN inference timed out")
            return {
                "success": False,
                "error": "RNAMPNN inference timed out"
            }
        except Exception as e:
            logger.error(f"Failed to run RNAMPNN inference: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def _extract_coordinates_from_pdb(self, pdb_file_path: str) -> np.ndarray:
        """
        Extract coordinates of specific atoms from RNA PDB file
        
        Args:
            pdb_file_path: Path to PDB file
            
        Returns:
            numpy array of coordinates with shape (seq_len, num_atoms, 3)
        """
        try:
            # Create temporary PDB file in model directory
            temp_pdb = os.path.join(self.temp_dir, f"temp_{os.getpid()}.pdb")
            with open(pdb_file_path, 'r') as src, open(temp_pdb, 'w') as dst:
                dst.write(src.read())
            
            # Prepare input data for coordinate extraction
            input_data = {
                "action": "extract_coordinates",
                "pdb_file": temp_pdb
            }
            
            result = self._run_inference_script(input_data)
            
            # Clean up temporary PDB file
            if os.path.exists(temp_pdb):
                os.remove(temp_pdb)
            
            if result.get("success", False):
                coords = np.array(result["coordinates"], dtype=np.float32)
                logger.info(f"Extracted coordinates with shape: {coords.shape}")
                return coords
            else:
                raise Exception(result.get("error", "Failed to extract coordinates"))
                
        except Exception as e:
            logger.error(f"Failed to extract coordinates from PDB: {e}")
            raise
    
    def _preprocess_coordinates(self, coords: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        """
        Preprocess coordinates for model input
        
        Args:
            coords: numpy array of coordinates
            
        Returns:
            Tuple of (coordinates_array, mask_array)
        """
        # Convert to torch tensor for processing
        import torch
        
        coords_tensor = torch.tensor(coords, dtype=torch.float32)
        
        # Add batch dimension
        if coords_tensor.dim() == 3:
            coords_tensor = coords_tensor.unsqueeze(0)
        
        # Create mask for valid coordinates (non-NaN)
        mask = ~torch.isnan(coords_tensor).any(dim=-1)
        mask = mask.all(dim=-1)  # All atoms must be valid for the residue to be valid
        
        # Convert back to numpy for JSON serialization
        coords_array = coords_tensor.numpy()
        mask_array = mask.numpy()
        
        logger.info(f"Preprocessed coordinates shape: {coords_array.shape}")
        logger.info(f"Preprocessed mask shape: {mask_array.shape}")
        
        return coords_array, mask_array
    
    def predict_sequence(self, pdb_file_path: str) -> Dict[str, Any]:
        """
        Predict RNA sequence from PDB file
        
        Args:
            pdb_file_path: Path to PDB file
            
        Returns:
            Dictionary containing prediction results
        """
        try:
            # Extract coordinates from PDB file
            coords = self._extract_coordinates_from_pdb(pdb_file_path)
            
            # Preprocess coordinates
            coords_array, mask_array = self._preprocess_coordinates(coords)
            
            # Prepare input data for prediction
            input_data = {
                "action": "predict_sequence",
                "coordinates": coords_array.tolist(),
                "mask": mask_array.tolist()
            }
            
            result = self._run_inference_script(input_data)
            
            if result.get("success", False):
                result.update({
                    "input_file": os.path.basename(pdb_file_path),
                    "model_info": {
                        "model_name": "RNAMPNN-X",
                        "model_type": "RNA sequence prediction from 3D structure",
                        "device": "cuda" if torch.cuda.is_available() else "cpu"
                    }
                })
                
                logger.info(f"Prediction completed for {pdb_file_path}")
                logger.info(f"Predicted sequence length: {result.get('sequence_length', 0)}")
                
                return result
            else:
                return {
                    "success": False,
                    "error": result.get("error", "Prediction failed"),
                    "input_file": os.path.basename(pdb_file_path)
                }
                
        except Exception as e:
            logger.error(f"Prediction failed for {pdb_file_path}: {e}")
            return {
                "success": False,
                "error": str(e),
                "input_file": os.path.basename(pdb_file_path) if pdb_file_path else "unknown"
            }
    
    def predict_sequence_from_coords(self, coordinates: np.ndarray) -> Dict[str, Any]:
        """
        Predict RNA sequence from coordinate array
        
        Args:
            coordinates: numpy array of coordinates with shape (seq_len, num_atoms, 3)
            
        Returns:
            Dictionary containing prediction results
        """
        try:
            # Preprocess coordinates
            coords_array, mask_array = self._preprocess_coordinates(coordinates)
            
            # Prepare input data for prediction
            input_data = {
                "action": "predict_sequence",
                "coordinates": coords_array.tolist(),
                "mask": mask_array.tolist()
            }
            
            result = self._run_inference_script(input_data)
            
            if result.get("success", False):
                result.update({
                    "model_info": {
                        "model_name": "RNAMPNN-X",
                        "model_type": "RNA sequence prediction from 3D structure",
                        "device": "cuda" if torch.cuda.is_available() else "cpu"
                    }
                })
                
                logger.info(f"Prediction completed from coordinates")
                logger.info(f"Predicted sequence length: {result.get('sequence_length', 0)}")
                
                return result
            else:
                return {
                    "success": False,
                    "error": result.get("error", "Prediction failed")
                }
                
        except Exception as e:
            logger.error(f"Prediction failed from coordinates: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def get_model_info(self) -> Dict[str, Any]:
        """Get model information"""
        try:
            # Prepare input data for model info
            input_data = {
                "action": "get_model_info"
            }
            
            result = self._run_inference_script(input_data)
            
            if result.get("success", False):
                result.update({
                    "model_path": self.model_path,
                    "environment_path": self.environment_path
                })
                return result
            else:
                return {
                    "model_name": "RNAMPNN-X",
                    "error": result.get("error", "Failed to get model info"),
                    "model_loaded": False
                }
                
        except Exception as e:
            logger.error(f"Failed to get model info: {e}")
            return {
                "model_name": "RNAMPNN-X",
                "error": str(e),
                "model_loaded": False
            }
    
    def validate_pdb_file(self, pdb_file_path: str) -> Dict[str, Any]:
        """
        Validate PDB file for RNAMPNN processing
        
        Args:
            pdb_file_path: Path to PDB file
            
        Returns:
            Dictionary containing validation results
        """
        try:
            if not os.path.exists(pdb_file_path):
                return {
                    "valid": False,
                    "error": "File does not exist"
                }
            
            if not pdb_file_path.lower().endswith('.pdb'):
                return {
                    "valid": False,
                    "error": "File must be a PDB file (.pdb extension)"
                }
            
            # Prepare input data for validation
            input_data = {
                "action": "validate_pdb",
                "pdb_file": pdb_file_path
            }
            
            result = self._run_inference_script(input_data)
            return result
            
        except Exception as e:
            return {
                "valid": False,
                "error": f"Failed to validate PDB file: {str(e)}"
            }

# Factory function
def create_rnampnn_wrapper(model_path: str = None, environment_path: str = None) -> RNAMPNNWrapper:
    """
    Factory function to create RNAMPNN wrapper
    
    Args:
        model_path: Path to RNAMPNN model directory
        environment_path: Path to RNAMPNN virtual environment
        
    Returns:
        RNAMPNNWrapper instance
    """
    return RNAMPNNWrapper(model_path=model_path, environment_path=environment_path)