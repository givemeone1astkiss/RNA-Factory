"""
MXFold2 Model Wrapper
RNA secondary structure prediction using deep learning with thermodynamic integration
"""

import os
import subprocess
import tempfile
import logging
from typing import Dict, Any, List
import shutil
import re

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
        self.model_path = model_path or "/home/huaizhi/Software/models/mxfold2"
        self.environment_path = environment_path or "/home/huaizhi/Software/.venv_mxfold2"
        self.temp_dir = None
        
    def setup_environment(self) -> bool:
        """Setup MXFold2 environment using uv"""
        try:
            # Create virtual environment if it doesn't exist
            if not os.path.exists(self.environment_path):
                logger.info(f"Creating MXFold2 virtual environment at {self.environment_path}")
                subprocess.run([
                    "uv", "venv", self.environment_path
                ], check=True)
            
            # Install MXFold2 in the virtual environment
            python_path = f"{self.environment_path}/bin/python"
            pip_path = f"{self.environment_path}/bin/pip"
            
            # Check if MXFold2 is already installed
            result = subprocess.run([
                python_path, "-c", "import mxfold2; print('MXFold2 is installed')"
            ], capture_output=True, text=True)
            
            if result.returncode != 0:
                logger.info("Installing MXFold2...")
                # Install MXFold2 from PyPI
                subprocess.run([
                    pip_path, "install", "mxfold2==0.1.2"
                ], check=True)
            
            logger.info("MXFold2 environment setup completed")
            return True
            
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to setup MXFold2 environment: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error setting up MXFold2 environment: {e}")
            return False
    
    def predict(self, sequences: List[str]) -> Dict[str, Any]:
        """
        Predict RNA secondary structures using MXFold2
        
        Args:
            sequences: List of RNA sequences
            
        Returns:
            Dictionary containing prediction results
        """
        if not self.environment_path or not os.path.exists(self.environment_path):
            if not self.setup_environment():
                return {
                    "success": False,
                    "error": "Failed to setup MXFold2 environment"
                }
        
        try:
            # Create temporary directory for input/output
            self.temp_dir = tempfile.mkdtemp(prefix="mxfold2_")
            input_file = os.path.join(self.temp_dir, "input.fasta")
            output_file = os.path.join(self.temp_dir, "output.txt")
            
            # Create FASTA input file
            with open(input_file, 'w') as f:
                for i, seq in enumerate(sequences):
                    f.write(f">sequence_{i+1}\n{seq}\n")
            
            # Prepare MXFold2 command using uv virtual environment
            python_path = f"{self.environment_path}/bin/python"
            cmd = [
                python_path, "-m", "mxfold2", "predict",
                input_file
            ]
            
            logger.info(f"Running MXFold2 command: {' '.join(cmd)}")
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                cwd=self.temp_dir,
                timeout=300
            )
            
            if result.returncode != 0:
                logger.error(f"MXFold2 failed: {result.stderr}")
                return {
                    "success": False,
                    "error": f"MXFold2 execution failed: {result.stderr}"
                }
            
            # Parse results
            results = self._parse_results(result.stdout, sequences)
            
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
    
    def _parse_results(self, output: str, sequences: List[str]) -> List[Dict[str, Any]]:
        """Parse MXFold2 output results"""
        results = []
        
        try:
            lines = output.strip().split('\n')
            current_sequence = None
            current_structure = None
            current_energy = None
            
            for line in lines:
                line = line.strip()
                if not line:
                    continue
                
                # Check if this is a sequence header
                if line.startswith('>'):
                    # Save previous result if exists
                    if current_sequence is not None and current_structure is not None:
                        results.append({
                            "sequence": current_sequence,
                            "format": "dot_bracket",
                            "data": current_structure,
                            "energy": current_energy
                        })
                    
                    # Start new sequence
                    current_sequence = None
                    current_structure = None
                    current_energy = None
                    continue
                
                # Check if this is a sequence line (contains only A, U, C, G)
                if re.match(r'^[AUCG]+$', line):
                    current_sequence = line
                    continue
                
                # Check if this is a structure line (contains dots, parentheses, and energy)
                # Format: structure (energy)
                structure_match = re.match(r'^([.()]+)\s+\(([0-9.-]+)\)$', line)
                if structure_match:
                    current_structure = structure_match.group(1)
                    try:
                        current_energy = float(structure_match.group(2))
                    except ValueError:
                        current_energy = None
                    continue
            
            # Save last result if exists
            if current_sequence is not None and current_structure is not None:
                results.append({
                    "sequence": current_sequence,
                    "format": "dot_bracket",
                    "data": current_structure,
                    "energy": current_energy
                })
            
            # If we didn't find any results, try to match with input sequences
            if not results and sequences:
                logger.warning("Could not parse MXFold2 output, using input sequences")
                for i, seq in enumerate(sequences):
                    results.append({
                        "sequence": seq,
                        "format": "dot_bracket",
                        "data": "",
                        "energy": None
                    })
            
        except Exception as e:
            logger.error(f"Failed to parse MXFold2 results: {e}")
            # Return empty results for each input sequence
            for seq in sequences:
                results.append({
                    "sequence": seq,
                    "format": "dot_bracket",
                    "data": "",
                    "energy": None
                })
        
        return results
    
    def get_model_info(self) -> Dict[str, Any]:
        """Get MXFold2 model information"""
        return {
            "name": "MXFold2",
            "description": "RNA secondary structure prediction using deep learning with thermodynamic integration",
            "version": "0.1.2",
            "paper": "https://doi.org/10.1038/s41467-021-21194-4",
            "github": "https://github.com/mxfold/mxfold2",
            "web_server": "http://www.dna.bio.keio.ac.jp/mxfold2/",
            "model_path": self.model_path,
            "environment_path": self.environment_path,
            "available": True,  # MXFold2 is available as a pip package
            "environment_ready": os.path.exists(self.environment_path),
            "supported_formats": ["dot_bracket"],
            "features": [
                "Deep learning-based prediction",
                "Thermodynamic integration",
                "Fast prediction",
                "High accuracy",
                "Support for long sequences"
            ]
        }
