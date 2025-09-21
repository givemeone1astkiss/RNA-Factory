"""
BPFold Model Wrapper
Deep generalizable prediction of RNA secondary structure via base pair motif energy
"""

import os
import subprocess
import tempfile
import logging
from typing import Dict, Any, List
import shutil
from ..path_manager import get_model_path, get_venv_path

logger = logging.getLogger(__name__)


class BPFoldWrapper:
    """Wrapper for BPFold RNA secondary structure prediction model"""
    
    def __init__(self, model_path: str = None, environment_path: str = None):
        """
        Initialize BPFold wrapper
        
        Args:
            model_path: Path to BPFold model checkpoints
            environment_path: Path to uv virtual environment for BPFold
        """
        self.model_path = model_path or get_model_path("BPfold") + "/model_predict"
        self.environment_path = environment_path or get_venv_path(".venv_bpfold")
        self.temp_dir = None
        
        # Validate model path
        if not os.path.exists(self.model_path):
            logger.warning(f"BPFold model path not found: {self.model_path}")
            self.model_path = None
        else:
            logger.info(f"BPFold model path found: {self.model_path}")
    
    def _setup_environment(self) -> bool:
        """Setup BPFold uv virtual environment"""
        try:
            # Check if uv virtual environment exists
            if not os.path.exists(self.environment_path):
                logger.info(f"Creating BPFold uv virtual environment: {self.environment_path}")
                
                # Create virtual environment
                subprocess.run(
                    ["uv", "venv", self.environment_path],
                    check=True
                )
                
                # Install BPFold and dependencies
                subprocess.run([
                    "uv", "pip", "install", 
                    "--python", f"{self.environment_path}/bin/python",
                    "BPfold",
                    "torch",
                    "numpy",
                    "pandas",
                    "scipy",
                    "scikit-learn",
                    "tqdm",
                    "pyyaml",
                    "einops",
                    "torchmetrics",
                    "fastai",
                    "scikit-image"
                ], check=True)
                
                logger.info("BPFold environment created successfully")
            else:
                logger.info("BPFold environment already exists")
            
            return True
            
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to setup BPFold environment: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error setting up BPFold environment: {e}")
            return False
    
    def _download_model(self) -> bool:
        """Download BPFold model if not present"""
        if self.model_path and os.path.exists(self.model_path):
            return True
            
        try:
            logger.info("Downloading BPFold model...")
            from ..path_manager import get_model_path
            model_dir = get_model_path("BPfold")
            os.makedirs(model_dir, exist_ok=True)
            
            # Download model
            subprocess.run([
                "wget", 
                "https://github.com/heqin-zhu/BPfold/releases/latest/download/model_predict.tar.gz",
                "-O", f"{model_dir}/model_predict.tar.gz"
            ], check=True)
            
            # Extract model
            subprocess.run([
                "tar", "-xzf", f"{model_dir}/model_predict.tar.gz", "-C", model_dir
            ], check=True)
            
            self.model_path = f"{model_dir}/model_predict"
            return True
            
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to download BPFold model: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error downloading BPFold model: {e}")
            return False
    
    def predict(self, rna_sequences: List[str], output_format: str = "ct", 
                ignore_nc: bool = False) -> Dict[str, Any]:
        """
        Predict RNA secondary structures using BPFold
        
        Args:
            rna_sequences: List of RNA sequences
            output_format: Output format (csv, bpseq, ct, dbn)
            ignore_nc: Whether to ignore non-canonical pairs
            
        Returns:
            Dictionary containing prediction results
        """
        if not self.model_path or not os.path.exists(self.model_path):
            if not self._download_model():
                return {
                    "success": False,
                    "error": "Failed to download BPFold model"
                }
        
        if not self._setup_environment():
            return {
                "success": False,
                "error": "Failed to setup BPFold environment"
            }
        
        try:
            # Create temporary directory for input/output
            self.temp_dir = tempfile.mkdtemp(prefix="bpfold_")
            input_file = os.path.join(self.temp_dir, "input.fasta")
            output_dir = os.path.join(self.temp_dir, "output")
            
            # Write sequences to FASTA file
            with open(input_file, 'w') as f:
                for i, seq in enumerate(rna_sequences):
                    f.write(f">sequence_{i+1}\n{seq}\n")
            
            # Prepare BPFold command using uv virtual environment
            python_path = f"{self.environment_path}/bin/python"
            cmd = [
                python_path, "-m", "BPfold.predict",
                "--checkpoint_dir", self.model_path,
                "--input", input_file,
                "--output", output_dir,
                "--out_type", output_format
            ]
            
            if ignore_nc:
                cmd.extend(["--ignore_nc"])
            
            # Run BPFold
            logger.info(f"Running BPFold command: {' '.join(cmd)}")
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                cwd=self.temp_dir,
                timeout=300  # 5 minute timeout
            )
            
            if result.returncode != 0:
                logger.error(f"BPFold failed: {result.stderr}")
                return {
                    "success": False,
                    "error": f"BPFold execution failed: {result.stderr}"
                }
            
            # Parse results
            results = self._parse_results(output_dir, rna_sequences, output_format)
            
            return {
                "success": True,
                "results": results,
                "stdout": result.stdout,
                "stderr": result.stderr
            }
            
        except Exception as e:
            logger.error(f"BPFold prediction failed: {e}")
            return {
                "success": False,
                "error": str(e)
            }
        finally:
            # Cleanup temporary directory
            if self.temp_dir and os.path.exists(self.temp_dir):
                shutil.rmtree(self.temp_dir)
                self.temp_dir = None
    
    def _parse_results(self, output_dir: str, rna_sequences: List[str], 
                      output_format: str) -> List[Dict[str, Any]]:
        """Parse BPFold output results"""
        results = []
        
        try:
            if output_format == "csv":
                # Parse CSV results - BPFold creates files with timestamp names
                csv_files = [f for f in os.listdir(output_dir) if f.endswith('.csv')]
                
                if csv_files:
                    csv_file = os.path.join(output_dir, csv_files[0])
                    with open(csv_file, 'r') as f:
                        content = f.read()
                    
                    # Parse CSV content
                    lines = content.strip().split('\n')
                    if len(lines) > 1:  # Skip header
                        for i, line in enumerate(lines[1:], 1):  # Skip header line
                            if i <= len(rna_sequences):
                                results.append({
                                    "sequence": rna_sequences[i-1],
                                    "format": "csv",
                                    "data": line
                                })
            
            elif output_format == "bpseq":
                # Parse BPSEQ results
                for i, seq in enumerate(rna_sequences):
                    bpseq_file = os.path.join(output_dir, f"sequence_{i+1}.bpseq")
                    if os.path.exists(bpseq_file):
                        with open(bpseq_file, 'r') as f:
                            content = f.read()
                        results.append({
                            "sequence": seq,
                            "format": "bpseq",
                            "data": content
                        })
            
            elif output_format == "ct":
                # Parse CT results
                for i, seq in enumerate(rna_sequences):
                    ct_file = os.path.join(output_dir, f"sequence_{i+1}.ct")
                    if os.path.exists(ct_file):
                        with open(ct_file, 'r') as f:
                            content = f.read()
                        results.append({
                            "sequence": seq,
                            "format": "ct",
                            "data": content
                        })
            
            elif output_format == "dbn":
                # Parse DBN results
                for i, seq in enumerate(rna_sequences):
                    dbn_file = os.path.join(output_dir, f"sequence_{i+1}.dbn")
                    if os.path.exists(dbn_file):
                        with open(dbn_file, 'r') as f:
                            content = f.read()
                        results.append({
                            "sequence": seq,
                            "format": "dbn",
                            "data": content
                        })
            
            # Parse confidence file if exists
            confidence_files = [f for f in os.listdir(output_dir) if f.startswith("BPfold_results_confidence_")]
            if confidence_files:
                confidence_file = os.path.join(output_dir, confidence_files[0])
                with open(confidence_file, 'r') as f:
                    confidence_data = f.read()
                # Add confidence data to results
                for result in results:
                    result["confidence_data"] = confidence_data
            
        except Exception as e:
            logger.error(f"Failed to parse BPFold results: {e}")
        
        return results
    
    def get_model_info(self) -> Dict[str, Any]:
        """Get BPFold model information"""
        return {
            "name": "BPFold",
            "description": "Deep generalizable prediction of RNA secondary structure via base pair motif energy",
            "version": "0.2.0",
            "paper": "https://www.nature.com/articles/s41467-025-60048-1",
            "github": "https://github.com/heqin-zhu/BPfold",
            "model_path": self.model_path,
            "environment_path": self.environment_path,
            "available": self.model_path and os.path.exists(self.model_path),
            "environment_ready": os.path.exists(self.environment_path),
            "supported_formats": ["csv", "bpseq", "ct", "dbn"],
            "features": [
                "RNA secondary structure prediction",
                "Base pair motif energy modeling",
                "Canonical and non-canonical base pairs",
                "Confidence scoring",
                "Multiple output formats"
            ]
        }
    
    def cleanup(self):
        """Cleanup resources"""
        if self.temp_dir and os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
            self.temp_dir = None
