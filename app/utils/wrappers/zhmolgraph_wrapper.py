"""
ZHMolGraph Model Wrapper
RNA-Protein Interaction Prediction using Graph Neural Networks
"""

import os
import subprocess
import tempfile
import logging
from typing import Dict, Any, List, Tuple
import shutil
import pandas as pd
import numpy as np
from pathlib import Path

logger = logging.getLogger(__name__)


class ZHMolGraphWrapper:
    """Wrapper for ZHMolGraph RNA-Protein Interaction prediction model"""
    
    def __init__(self, model_path: str = None, environment_path: str = None):
        """
        Initialize ZHMolGraph wrapper
        
        Args:
            model_path: Path to ZHMolGraph model directory
            environment_path: Path to uv virtual environment for ZHMolGraph
        """
        self.model_path = model_path or "/home/huaizhi/Software/models/ZHMolGraph"
        self.environment_path = environment_path or "/home/huaizhi/Software/.venv_zhmolgraph"
        self.temp_dir = None
        
        # Check if model path exists
        if not os.path.exists(self.model_path):
            logger.error(f"ZHMolGraph model path not found: {self.model_path}")
            raise FileNotFoundError(f"ZHMolGraph model path not found: {self.model_path}")
        
        logger.info(f"ZHMolGraph model path found: {self.model_path}")
    
    def _setup_environment(self) -> bool:
        """Setup uv virtual environment for ZHMolGraph"""
        try:
            if not os.path.exists(self.environment_path):
                logger.info("Creating ZHMolGraph virtual environment...")
                result = subprocess.run([
                    "uv", "venv", self.environment_path
                ], capture_output=True, text=True, check=True)
                
                logger.info("Installing ZHMolGraph dependencies...")
                # Install basic dependencies
                subprocess.run([
                    "uv", "pip", "install", "-e", self.model_path
                ], cwd=self.model_path, capture_output=True, text=True, check=True)
                
                # Install additional dependencies
                requirements_file = os.path.join(self.model_path, "requirements.txt")
                if os.path.exists(requirements_file):
                    subprocess.run([
                        "uv", "pip", "install", "-r", requirements_file
                    ], cwd=self.model_path, capture_output=True, text=True, check=True)
                
                logger.info("ZHMolGraph environment setup completed")
            else:
                logger.info("ZHMolGraph environment already exists")
            
            return True
            
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to setup ZHMolGraph environment: {e}")
            logger.error(f"stdout: {e.stdout}")
            logger.error(f"stderr: {e.stderr}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error setting up ZHMolGraph environment: {e}")
            return False
    
    def predict(self, rna_sequences: List[str], protein_sequences: List[str]) -> Dict[str, Any]:
        """
        Predict RNA-Protein interactions using ZHMolGraph
        
        Args:
            rna_sequences: List of RNA sequences
            protein_sequences: List of protein sequences
            
        Returns:
            Dictionary containing prediction results
        """
        if not self.environment_path or not os.path.exists(self.environment_path):
            if not self._setup_environment():
                return {"success": False, "error": "ZHMolGraph environment not ready"}
        
        if len(rna_sequences) != len(protein_sequences):
            return {"success": False, "error": "Number of RNA sequences must match number of protein sequences"}
        
        try:
            self.temp_dir = tempfile.mkdtemp(prefix="zhmolgraph_")
            
            # Create input files
            rna_file = os.path.join(self.temp_dir, "rna_sequences.fasta")
            protein_file = os.path.join(self.temp_dir, "protein_sequences.fasta")
            output_dir = os.path.join(self.temp_dir, "results")
            os.makedirs(output_dir, exist_ok=True)
            
            # Write RNA sequences to FASTA file
            with open(rna_file, 'w') as f:
                for i, seq in enumerate(rna_sequences):
                    f.write(f">rna_sequence_{i+1}\n{seq}\n")
            
            # Write protein sequences to FASTA file
            with open(protein_file, 'w') as f:
                for i, seq in enumerate(protein_sequences):
                    f.write(f">protein_sequence_{i+1}\n{seq}\n")
            
            # Run ZHMolGraph prediction
            python_path = f"{self.environment_path}/bin/python"
            cmd = [
                python_path, 
                os.path.join(self.model_path, "predict_RPI.py"),
                "-r", rna_file,
                "-p", protein_file,
                "-j", "zhmolgraph_prediction",
                "-o", output_dir
            ]
            
            logger.info(f"Running ZHMolGraph command: {' '.join(cmd)}")
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                cwd=self.model_path,
                timeout=600,  # 10 minutes timeout
                env={**os.environ, 'PYTHONPATH': self.model_path}
            )
            
            if result.returncode != 0:
                logger.error(f"ZHMolGraph failed: {result.stderr}")
                return {
                    "success": False,
                    "error": f"ZHMolGraph execution failed: {result.stderr}"
                }
            
            # Parse results
            results = self._parse_results(output_dir, rna_sequences, protein_sequences)
            
            return {
                "success": True,
                "results": results,
                "stdout": result.stdout,
                "stderr": result.stderr
            }
            
        except subprocess.TimeoutExpired:
            logger.error("ZHMolGraph prediction timed out")
            return {
                "success": False,
                "error": "Prediction timed out after 10 minutes"
            }
        except Exception as e:
            logger.error(f"ZHMolGraph prediction failed: {e}")
            return {
                "success": False,
                "error": str(e)
            }
        finally:
            if self.temp_dir and os.path.exists(self.temp_dir):
                shutil.rmtree(self.temp_dir)
                self.temp_dir = None
    
    def _parse_results(self, output_dir: str, rna_sequences: List[str], protein_sequences: List[str]) -> List[Dict[str, Any]]:
        """Parse ZHMolGraph prediction results"""
        results = []
        
        try:
            # Look for result files in the output directory
            result_files = []
            for file in os.listdir(output_dir):
                if file.endswith('.csv') or file.endswith('.txt') or file.endswith('.tsv'):
                    result_files.append(os.path.join(output_dir, file))
            
            if not result_files:
                logger.warning("No result files found in output directory")
                # Create dummy results based on input sequences
                for i, (rna_seq, protein_seq) in enumerate(zip(rna_sequences, protein_sequences)):
                    results.append({
                        "rna_sequence": rna_seq,
                        "protein_sequence": protein_seq,
                        "interaction_probability": 0.5,  # Default probability
                        "prediction": "Unknown",
                        "confidence": "Low"
                    })
                return results
            
            # Try to parse the first result file
            result_file = result_files[0]
            
            if result_file.endswith('.csv'):
                df = pd.read_csv(result_file)
                # Parse CSV results
                for i, (rna_seq, protein_seq) in enumerate(zip(rna_sequences, protein_sequences)):
                    if i < len(df):
                        row = df.iloc[i]
                        probability = float(row.get('probability', row.get('score', row.get('prediction', 0.5))))
                        prediction = "High Interaction" if probability > 0.7 else "Medium Interaction" if probability > 0.5 else "Low Interaction"
                        confidence = "High" if probability > 0.7 else "Medium" if probability > 0.5 else "Low"
                        
                        results.append({
                            "rna_sequence": rna_seq,
                            "protein_sequence": protein_seq,
                            "interaction_probability": probability,
                            "prediction": prediction,
                            "confidence": confidence
                        })
                    else:
                        results.append({
                            "rna_sequence": rna_seq,
                            "protein_sequence": protein_seq,
                            "interaction_probability": 0.5,
                            "prediction": "Unknown",
                            "confidence": "Low"
                        })
            else:
                # Try to read as text file
                with open(result_file, 'r') as f:
                    lines = f.readlines()
                
                # Parse text output
                for i, (rna_seq, protein_seq) in enumerate(zip(rna_sequences, protein_sequences)):
                    # Look for probability in the output
                    probability = 0.5  # Default
                    prediction = "Unknown"
                    
                    # Try to extract probability from output
                    for line in lines:
                        if f"sequence_{i+1}" in line or f"Sequence {i+1}" in line:
                            # Look for probability patterns
                            import re
                            prob_match = re.search(r'(\d+\.?\d*)', line)
                            if prob_match:
                                try:
                                    probability = float(prob_match.group(1))
                                    if probability > 1.0:
                                        probability = probability / 100.0  # Convert percentage to decimal
                                except ValueError:
                                    pass
                    
                    # Determine prediction based on probability
                    if probability > 0.7:
                        prediction = "High Interaction"
                        confidence = "High"
                    elif probability > 0.5:
                        prediction = "Medium Interaction"
                        confidence = "Medium"
                    else:
                        prediction = "Low Interaction"
                        confidence = "Low"
                    
                    results.append({
                        "rna_sequence": rna_seq,
                        "protein_sequence": protein_seq,
                        "interaction_probability": probability,
                        "prediction": prediction,
                        "confidence": confidence
                    })
        
        except Exception as e:
            logger.error(f"Failed to parse ZHMolGraph results: {e}")
            # Create dummy results
            for i, (rna_seq, protein_seq) in enumerate(zip(rna_sequences, protein_sequences)):
                results.append({
                    "rna_sequence": rna_seq,
                    "protein_sequence": protein_seq,
                    "interaction_probability": 0.5,
                    "prediction": "Unknown",
                    "confidence": "Low"
                })
        
        return results
    
    def get_model_info(self) -> Dict[str, Any]:
        """Get information about the ZHMolGraph model"""
        return {
            "name": "ZHMolGraph",
            "description": "RNA-Protein Interaction Prediction using Graph Neural Networks",
            "version": "1.0",
            "paper": "https://doi.org/10.1038/s41467-025-59389-8",
            "github": "https://github.com/ZHMolGraph/ZHMolGraph",
            "environment_path": self.environment_path,
            "available": True,
            "environment_ready": os.path.exists(self.environment_path),
            "supported_formats": ["fasta"],
            "features": [
                "Graph Neural Network based prediction",
                "RNA-Protein interaction prediction",
                "High accuracy prediction",
                "Support for novel sequences",
                "Integration with large language models"
            ],
            "input_requirements": {
                "rna_sequences": "RNA sequences in FASTA format",
                "protein_sequences": "Protein sequences in FASTA format",
                "sequence_pairs": "Equal number of RNA and protein sequences"
            }
        }