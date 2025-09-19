"""
RNAformer Model Wrapper
RNA secondary structure prediction using deep learning
"""

import os
import sys
import subprocess
import tempfile
import logging
from typing import Dict, Any, List, Optional
import shutil
import json

logger = logging.getLogger(__name__)


class RNAformerWrapper:
    """Wrapper for RNAformer RNA secondary structure prediction model"""
    
    def __init__(self, model_path: str = None, environment_path: str = None):
        """
        Initialize RNAformer wrapper
        
        Args:
            model_path: Path to RNAformer model directory
            environment_path: Path to uv virtual environment for RNAformer
        """
        self.model_path = model_path or "/home/huaizhi/Software/models/RNAformer"
        self.environment_path = environment_path or "/home/huaizhi/Software/.venv_rnaformer"
        self.model_state_dict = os.path.join(self.model_path, "models", "RNAformer_32M_state_dict_biophysical.pth")
        self.model_config = os.path.join(self.model_path, "models", "RNAformer_32M_config_biophysical.yml")
        
        # Validate model files exist
        if not os.path.exists(self.model_state_dict):
            raise FileNotFoundError(f"Model state dict not found: {self.model_state_dict}")
        if not os.path.exists(self.model_config):
            raise FileNotFoundError(f"Model config not found: {self.model_config}")
    
    def predict(self, sequences: List[str]) -> Dict[str, Any]:
        """
        Predict RNA secondary structure for given sequences
        
        Args:
            sequences: List of RNA sequences
            
        Returns:
            Dictionary containing prediction results
        """
        try:
            results = []
            
            for i, sequence in enumerate(sequences):
                logger.info(f"Processing sequence {i+1}/{len(sequences)}: {sequence[:50]}...")
                
                # Create temporary input file
                with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as temp_file:
                    temp_file.write(sequence)
                    temp_input = temp_file.name
                
                # Create temporary output file
                with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as temp_file:
                    temp_output = temp_file.name
                
                try:
                    # Run RNAformer inference
                    cmd = [
                        "python", "infer_RNAformer.py",
                        "-c", "6",  # Number of cycles
                        "-s", sequence,
                        "--state_dict", self.model_state_dict,
                        "--config", self.model_config
                    ]
                    
                    # Set up environment
                    env = os.environ.copy()
                    env["PYTHONPATH"] = self.model_path
                    
                    # Use the virtual environment Python
                    python_path = os.path.join(self.environment_path, "bin", "python")
                    cmd[0] = python_path
                    
                    # Run command in model directory
                    result = subprocess.run(
                        cmd,
                        cwd=self.model_path,
                        capture_output=True,
                        text=True,
                        env=env,
                        timeout=300  # 5 minute timeout
                    )
                    
                    if result.returncode != 0:
                        logger.error(f"RNAformer inference failed: {result.stderr}")
                        raise RuntimeError(f"RNAformer inference failed: {result.stderr}")
                    
                    # Parse output to extract pairing information
                    output_lines = result.stdout.strip().split('\n')
                    pairing_indices_1 = []
                    pairing_indices_2 = []
                    
                    for line in output_lines:
                        if "Pairing index 1:" in line:
                            # Extract indices from line like "Pairing index 1: [0, 1, 2, ...]"
                            indices_str = line.split("Pairing index 1:")[1].strip()
                            if indices_str != "[]":
                                try:
                                    indices = eval(indices_str)
                                    pairing_indices_1 = indices
                                except:
                                    pairing_indices_1 = []
                        elif "Pairing index 2:" in line:
                            # Extract indices from line like "Pairing index 2: [10, 11, 12, ...]"
                            indices_str = line.split("Pairing index 2:")[1].strip()
                            if indices_str != "[]":
                                try:
                                    indices = eval(indices_str)
                                    pairing_indices_2 = indices
                                except:
                                    pairing_indices_2 = []
                    
                    # Combine pairing indices
                    pairing_indices = []
                    for i in range(min(len(pairing_indices_1), len(pairing_indices_2))):
                        pairing_indices.extend([pairing_indices_1[i], pairing_indices_2[i]])
                    
                    # Convert pairing indices to dot-bracket notation
                    dot_bracket = self._indices_to_dot_bracket(sequence, pairing_indices)
                    
                    # Generate CT format
                    ct_content = self._generate_ct_format(sequence, pairing_indices)
                    
                    results.append({
                        "sequence": sequence,
                        "length": len(sequence),
                        "dot_bracket": dot_bracket,
                        "ct_content": ct_content,
                        "pairing_indices": pairing_indices
                    })
                    
                finally:
                    # Clean up temporary files
                    if os.path.exists(temp_input):
                        os.unlink(temp_input)
                    if os.path.exists(temp_output):
                        os.unlink(temp_output)
            
            return {
                "success": True,
                "results": results,
                "model": "RNAformer",
                "total_sequences": len(sequences)
            }
            
        except Exception as e:
            logger.error(f"RNAformer prediction failed: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "model": "RNAformer"
            }
    
    def _indices_to_dot_bracket(self, sequence: str, pairing_indices: List[int]) -> str:
        """Convert pairing indices to dot-bracket notation"""
        length = len(sequence)
        dot_bracket = ['.'] * length
        
        # Group indices into pairs
        for i in range(0, len(pairing_indices), 2):
            if i + 1 < len(pairing_indices):
                pos1 = pairing_indices[i]
                pos2 = pairing_indices[i + 1]
                if 0 <= pos1 < length and 0 <= pos2 < length:
                    dot_bracket[pos1] = '('
                    dot_bracket[pos2] = ')'
        
        return ''.join(dot_bracket)
    
    def _generate_ct_format(self, sequence: str, pairing_indices: List[int]) -> str:
        """Generate CT format content"""
        length = len(sequence)
        ct_lines = [str(length)]  # Header line
        
        # Group indices into pairs
        pairs = {}
        for i in range(0, len(pairing_indices), 2):
            if i + 1 < len(pairing_indices):
                pos1 = pairing_indices[i]
                pos2 = pairing_indices[i + 1]
                if 0 <= pos1 < length and 0 <= pos2 < length:
                    pairs[pos1] = pos2
                    pairs[pos2] = pos1
        
        # Generate CT lines
        for i in range(length):
            base = sequence[i]
            paired_base = pairs.get(i, 0)
            ct_line = f"{i+1:4d} {base} {i:4d} {i+2:4d} {paired_base:4d} {i+1:4d}"
            ct_lines.append(ct_line)
        
        return '\n'.join(ct_lines)
    
    def test_model(self) -> bool:
        """Test if the model is working correctly"""
        try:
            test_sequence = "GCCCGCAUGGUGAAAUCGGUAAACACAUCGCACUAAUGCGCCGCCUCUGGCUUGCCGGUUCAAGUCCGGCUGCGGGCACCA"
            result = self.predict([test_sequence])
            return result["success"]
        except Exception as e:
            logger.error(f"RNAformer model test failed: {str(e)}")
            return False
