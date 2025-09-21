"""
MXFold2 Model Wrapper
RNA secondary structure prediction using deep learning with thermodynamic integration
使用外部软件包mxfold2进行预测
"""

import os
import subprocess
import tempfile
import logging
from typing import Dict, Any, List
import shutil
import re
from ..path_manager import get_model_path, get_venv_path

logger = logging.getLogger(__name__)


class MXFold2Wrapper:
    """Wrapper for MXFold2 RNA secondary structure prediction model"""
    
    def __init__(self, model_path: str = None, environment_path: str = None):
        """
        Initialize MXFold2 wrapper
        
        Args:
            model_path: Path to MXFold2 model directory (not used for MXFold2 as it's a pip package)
            environment_path: Path to uv virtual environment for MXFold2
        """
        self.model_path = model_path or get_model_path("mxfold2")
        self.environment_path = environment_path or get_venv_path(".venv_mxfold2")
        self.temp_dir = None
        
    def setup_environment(self) -> bool:
        """Setup MXFold2 environment using uv"""
        try:
            # Check if uv virtual environment exists
            if not os.path.exists(self.environment_path):
                logger.info(f"Creating MXFold2 uv virtual environment: {self.environment_path}")
                
                # Create virtual environment
                subprocess.run(
                    ["uv", "venv", self.environment_path, "--python", "3.10"],
                    check=True
                )
                
                # Install MXFold2 from whl file
                whl_path = os.path.join(self.model_path, "mxfold2", "mxfold2-0.1.2-cp310-cp310-manylinux_2_17_x86_64.whl")
                if os.path.exists(whl_path):
                    subprocess.run([
                        "uv", "pip", "install", 
                        "--python", f"{self.environment_path}/bin/python",
                        whl_path
                    ], check=True)
                    logger.info("MXFold2 installed from whl file")
                else:
                    # Fallback to pip install
                    subprocess.run([
                        "uv", "pip", "install", 
                        "--python", f"{self.environment_path}/bin/python",
                        "mxfold2"
                    ], check=True)
                    logger.info("MXFold2 installed from PyPI")
                
                logger.info("MXFold2 environment created successfully")
            else:
                logger.info("MXFold2 environment already exists")
            
            return True
            
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to setup MXFold2 environment: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error setting up MXFold2 environment: {e}")
            return False
    
    def predict(self, rna_sequences: List[str], output_format: str = "ct", 
                model: str = "MixC", gpu: int = -1, **kwargs) -> Dict[str, Any]:
        """
        Predict RNA secondary structures using MXFold2
        
        Args:
            rna_sequences: List of RNA sequences
            output_format: Output format (ct, dotbracket, bpseq)
            model: Model type (Turner, Zuker, ZukerS, ZukerL, ZukerC, Mix, MixC)
            gpu: GPU ID to use (-1 for CPU)
            **kwargs: Additional parameters for MXFold2
            
        Returns:
            Dictionary containing prediction results
        """
        if not self.setup_environment():
            return {
                "success": False,
                "error": "Failed to setup MXFold2 environment"
            }
        
        try:
            # Create temporary directory for input/output
            self.temp_dir = tempfile.mkdtemp(prefix="mxfold2_")
            input_file = os.path.join(self.temp_dir, "input.fa")
            output_file = os.path.join(self.temp_dir, "output.txt")
            
            # Write sequences to FASTA file
            with open(input_file, 'w') as f:
                for i, seq in enumerate(rna_sequences):
                    f.write(f">sequence_{i+1}\n{seq}\n")
            
            # Prepare MXFold2 command using uv virtual environment
            python_path = f"{self.environment_path}/bin/python"
            cmd = [
                python_path, "-m", "mxfold2", "predict",
                "--model", model,
                "--gpu", str(gpu),
                input_file
            ]
            
            # Add additional parameters if provided
            if "max_helix_length" in kwargs:
                cmd.extend(["--max-helix-length", str(kwargs["max_helix_length"])])
            if "use_constraint" in kwargs and kwargs["use_constraint"]:
                cmd.append("--use-constraint")
            
            # Run MXFold2
            logger.info(f"Running MXFold2 command: {' '.join(cmd)}")
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                cwd=self.temp_dir,
                timeout=300  # 5 minute timeout
            )
            
            if result.returncode != 0:
                logger.error(f"MXFold2 failed: {result.stderr}")
                return {
                    "success": False,
                    "error": f"MXFold2 execution failed: {result.stderr}"
                }
            
            # Parse results from stdout
            results = self._parse_results(result.stdout, rna_sequences, output_format)
            
            return {
                "success": True,
                "results": results,
                "stdout": result.stdout,
                "stderr": result.stderr
            }
            
        except Exception as e:
            logger.error(f"MXFold2 prediction failed: {e}")
            return {
                "success": False,
                "error": str(e)
            }
        finally:
            # Cleanup temporary directory
            if self.temp_dir and os.path.exists(self.temp_dir):
                shutil.rmtree(self.temp_dir)
                self.temp_dir = None
    
    def _parse_results(self, stdout: str, sequences: List[str], 
                      output_format: str) -> List[Dict[str, Any]]:
        """Parse MXFold2 output results"""
        results = []
        
        try:
            lines = stdout.strip().split('\n')
            current_sequence = None
            current_structure = None
            current_energy = None
            
            for line in lines:
                line = line.strip()
                if line.startswith('>'):
                    # Save previous result if exists
                    if current_sequence and current_structure:
                        result_data = self._create_result_data(
                            current_sequence, current_structure, output_format, current_energy
                        )
                        results.append(result_data)
                    
                    # Start new sequence
                    current_sequence = None
                    current_structure = None
                    current_energy = None
                elif line and not line.startswith('>'):
                    # This is a structure line
                    if current_sequence is None:
                        # This is the sequence line
                        current_sequence = line
                    else:
                        # This is the structure line with energy
                        # Format: structure (energy)
                        if '(' in line and ')' in line:
                            # Extract structure and energy
                            parts = line.rsplit('(', 1)
                            if len(parts) == 2:
                                current_structure = parts[0].strip()
                                energy_str = parts[1].rstrip(')').strip()
                                try:
                                    current_energy = float(energy_str)
                                except ValueError:
                                    current_energy = None
                            else:
                                current_structure = line
                                current_energy = None
                        else:
                            current_structure = line
                            current_energy = None
            
            # Save last result if exists
            if current_sequence and current_structure:
                result_data = self._create_result_data(
                    current_sequence, current_structure, output_format, current_energy
                )
                results.append(result_data)
            
            # If we didn't get results from parsing, try to match with input sequences
            if not results and sequences:
                logger.warning("Could not parse MXFold2 output, trying to match with input sequences")
                for i, seq in enumerate(sequences):
                    result_data = self._create_result_data(seq, "", output_format)
                    results.append(result_data)
            
        except Exception as e:
            logger.error(f"Failed to parse MXFold2 results: {e}")
        
        return results
    
    def _create_result_data(self, sequence: str, structure: str, output_format: str, energy: float = None) -> Dict[str, Any]:
        """Create result data dictionary"""
        result_data = {
            "sequence": sequence,
            "structure": structure,
            "format": output_format,
            "length": len(sequence)
        }
        
        # Add energy if available
        if energy is not None:
            result_data["energy"] = energy
        
        # Convert to CT format if needed
        if output_format == "ct" and structure:
            ct_data = self._convert_to_ct(sequence, structure)
            result_data["ct_data"] = ct_data
        
        # Convert to BPSEQ format if needed
        if output_format == "bpseq" and structure:
            bpseq_data = self._convert_to_bpseq(sequence, structure)
            result_data["bpseq_data"] = bpseq_data
        
        return result_data
    
    def _convert_to_ct(self, sequence: str, structure: str) -> str:
        """Convert dot-bracket notation to CT format"""
        ct_lines = [f">seq length: {len(sequence)}\t seq name: sequence"]
        
        pairs = {}
        stack = []
        
        for i, char in enumerate(structure):
            if char == '(':
                stack.append(i)
            elif char == ')':
                if stack:
                    j = stack.pop()
                    pairs[i] = j
                    pairs[j] = i
        
        for i, base in enumerate(sequence):
            pair_pos = pairs.get(i, 0)
            ct_lines.append(f"{i+1}\t{base}\t{i}\t{i+2}\t{pair_pos}\t{i+1}")
        
        return '\n'.join(ct_lines)
    
    def _convert_to_bpseq(self, sequence: str, structure: str) -> str:
        """Convert dot-bracket notation to BPSEQ format"""
        bpseq_lines = []
        
        pairs = {}
        stack = []
        
        for i, char in enumerate(structure):
            if char == '(':
                stack.append(i)
            elif char == ')':
                if stack:
                    j = stack.pop()
                    pairs[i] = j
                    pairs[j] = i
        
        for i, base in enumerate(sequence):
            pair_pos = pairs.get(i, 0)
            bpseq_lines.append(f"{i+1} {base} {pair_pos}")
        
        return '\n'.join(bpseq_lines)
    
    def get_model_info(self) -> Dict[str, Any]:
        """Get MXFold2 model information"""
        return {
            "name": "MXFold2",
            "description": "RNA secondary structure prediction using deep learning with thermodynamic integration",
            "version": "0.1.2",
            "paper": "https://www.nature.com/articles/s41467-021-21294-1",
            "github": "https://github.com/mxfold/mxfold2",
            "model_path": self.model_path,
            "environment_path": self.environment_path,
            "available": True,
            "environment_ready": os.path.exists(self.environment_path),
            "supported_formats": ["ct", "dotbracket", "bpseq"],
            "supported_models": ["Turner", "Zuker", "ZukerS", "ZukerL", "ZukerC", "Mix", "MixC"],
            "features": [
                "Deep learning-based prediction",
                "Thermodynamic integration",
                "Fast inference",
                "High accuracy",
                "Support for long sequences",
                "Multiple model architectures",
                "GPU acceleration support"
            ]
        }
    
    def cleanup(self):
        """Cleanup resources"""
        if self.temp_dir and os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
            self.temp_dir = None