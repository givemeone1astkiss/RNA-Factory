"""
RiboDiffusion Model Wrapper
Tertiary Structure-based RNA Inverse Folding with Generative Diffusion Models
"""

import os
import sys
import subprocess
import tempfile
import logging
from typing import Dict, Any, List, Optional
import shutil
import json

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
sys.path.insert(0, project_root)

from app.utils.path_manager import get_model_path, get_venv_path

logger = logging.getLogger(__name__)

class RiboDiffusionWrapper:
    """Wrapper for RiboDiffusion RNA inverse folding model"""
    
    def __init__(self, model_path: str = None, environment_path: str = None):
        """
        Initialize RiboDiffusion wrapper
        
        Args:
            model_path: Path to RiboDiffusion model directory
            environment_path: Path to uv virtual environment for RiboDiffusion
        """
        self.model_path = model_path or get_model_path("RiboDiffusion")
        self.environment_path = environment_path or get_venv_path(".venv_ribodiffusion")
        self.temp_dir = None
        
    def setup_environment(self) -> bool:
        """Setup RiboDiffusion environment using uv"""
        try:
            # Check if environment exists
            if not os.path.exists(self.environment_path):
                logger.error(f"RiboDiffusion environment not found at {self.environment_path}")
                return False
                
            # Check if model directory exists
            if not os.path.exists(self.model_path):
                logger.error(f"RiboDiffusion model directory not found at {self.model_path}")
                return False
                
            # Check if checkpoint exists
            checkpoint_path = os.path.join(self.model_path, "ckpts", "exp_inf.pth")
            if not os.path.exists(checkpoint_path):
                logger.error(f"RiboDiffusion checkpoint not found at {checkpoint_path}")
                return False
                
            logger.info("RiboDiffusion environment setup completed")
            return True
            
        except Exception as e:
            logger.error(f"Failed to setup RiboDiffusion environment: {e}")
            return False
    
    def inverse_fold(self, 
                     pdb_file: str,
                     num_samples: int = 1,
                     sampling_steps: int = 50,
                     cond_scale: float = -1.0,
                     dynamic_threshold: bool = False) -> Dict[str, Any]:
        """
        Perform RNA inverse folding using RiboDiffusion
        
        Args:
            pdb_file: Path to input PDB file
            num_samples: Number of sequences to generate
            sampling_steps: Number of sampling steps
            cond_scale: Conditional scaling weight
            dynamic_threshold: Whether to use dynamic thresholding
            
        Returns:
            Dictionary containing generated RNA sequences and results
        """
        try:
            # Setup environment
            if not self.setup_environment():
                return {
                    "success": False,
                    "error": "Failed to setup RiboDiffusion environment"
                }
            
            # Create temporary directory for output
            self.temp_dir = tempfile.mkdtemp(prefix="ribodiffusion_")
            
            # Prepare command components
            python_path = os.path.join(self.environment_path, "bin", "python")
            main_script = os.path.join(self.model_path, "main.py")
            
            all_sequences = []
            all_recovery_rates = []
            
            # Run inference for each sample individually to avoid DataParallel issues
            for i in range(num_samples):
                logger.info(f"Running RiboDiffusion inference {i+1}/{num_samples}")
                
                # Create individual output directory for each sample
                output_dir = os.path.join(self.temp_dir, f"exp_inf_{i}")
                
                cmd = [
                    python_path,
                    main_script,
                    "--PDB_file", pdb_file,
                    "--save_folder", output_dir,
                    "--config.eval.n_samples", "1",  # Always generate 1 sample per call
                    "--config.eval.sampling_steps", str(sampling_steps),
                    "--config.eval.cond_scale", str(cond_scale)
                ]
                
                if dynamic_threshold:
                    cmd.append("--config.eval.dynamic_threshold")
                
                # Run inference for single sample
                result = subprocess.run(
                    cmd,
                    cwd=self.model_path,
                    capture_output=True,
                    text=True,
                    timeout=300  # 5 minutes timeout per sample
                )
                
                if result.returncode != 0:
                    logger.error(f"RiboDiffusion inference failed for sample {i+1}: {result.stderr}")
                    return {
                        "success": False,
                        "error": f"RiboDiffusion inference failed for sample {i+1}: {result.stderr}"
                    }
                
                # Parse output for this sample
                output_text = result.stdout
                recovery_rate = None
                
                # Extract recovery rate from output
                for line in output_text.split('\n'):
                    if 'recovery_rate' in line:
                        try:
                            recovery_rate = float(line.split('recovery_rate')[-1].strip())
                            break
                        except:
                            pass
                
                if recovery_rate is not None:
                    all_recovery_rates.append(recovery_rate)
                
                # Read generated sequence for this sample
                fasta_dir = os.path.join(output_dir, "fasta")
                if os.path.exists(fasta_dir):
                    fasta_file = os.path.join(fasta_dir, f"{os.path.splitext(os.path.basename(pdb_file))[0]}_0.fasta")
                    if os.path.exists(fasta_file):
                        with open(fasta_file, 'r') as f:
                            content = f.read().strip()
                            if content:
                                # Extract sequence from FASTA format
                                lines = content.split('\n')
                                if len(lines) > 1:
                                    all_sequences.append(lines[1])
                                else:
                                    all_sequences.append(content)
            
            # Calculate average recovery rate
            avg_recovery_rate = sum(all_recovery_rates) / len(all_recovery_rates) if all_recovery_rates else 0.0
            
            return {
                "success": True,
                "sequences": all_sequences,
                "recovery_rate": avg_recovery_rate,
                "num_samples": num_samples,
                "sampling_steps": sampling_steps,
                "cond_scale": cond_scale,
                "dynamic_threshold": dynamic_threshold,
                "output_dir": self.temp_dir
            }
            
        except subprocess.TimeoutExpired:
            logger.error("RiboDiffusion inference timed out")
            return {
                "success": False,
                "error": "RiboDiffusion inference timed out"
            }
        except Exception as e:
            logger.error(f"RiboDiffusion inference failed: {e}")
            return {
                "success": False,
                "error": f"RiboDiffusion inference failed: {str(e)}"
            }
        finally:
            # Cleanup temporary directory
            if self.temp_dir and os.path.exists(self.temp_dir):
                try:
                    shutil.rmtree(self.temp_dir)
                except Exception as e:
                    logger.warning(f"Failed to cleanup temporary directory: {e}")
    
    def get_model_info(self) -> Dict[str, Any]:
        """Get model information"""
        return {
            "name": "RiboDiffusion",
            "description": "Tertiary Structure-based RNA Inverse Folding with Generative Diffusion Models",
            "type": "De Novo Design",
            "input_type": "PDB file",
            "output_type": "RNA sequences",
            "model_path": self.model_path,
            "environment_path": self.environment_path,
            "checkpoint_exists": os.path.exists(os.path.join(self.model_path, "ckpts", "exp_inf.pth")) if self.model_path else False
        }
    
    def cleanup(self):
        """Cleanup resources"""
        if self.temp_dir and os.path.exists(self.temp_dir):
            try:
                shutil.rmtree(self.temp_dir)
            except Exception as e:
                logger.warning(f"Failed to cleanup temporary directory: {e}")
