"""
RNAmigos2 Model Wrapper
RNA-ligand interaction prediction using deep graph learning
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


class RNAmigos2Wrapper:
    """Wrapper for RNAmigos2 RNA-ligand interaction prediction model"""
    
    def __init__(self, model_path: str = None, environment_path: str = None):
        """
        Initialize RNAmigos2 wrapper
        
        Args:
            model_path: Path to RNAmigos2 model directory
            environment_path: Path to uv virtual environment for RNAmigos2
        """
        self.model_path = model_path or "/home/huaizhi/Software/models/rnamigos2"
        self.environment_path = environment_path or "/home/huaizhi/Software/.venv_rnamigos2"
        self.temp_dir = None
        
    def setup_environment(self) -> bool:
        """Setup RNAmigos2 environment using uv"""
        try:
            # Check if environment exists
            if not os.path.exists(self.environment_path):
                logger.error(f"RNAmigos2 environment not found at {self.environment_path}")
                return False
                
            # Check if model directory exists
            if not os.path.exists(self.model_path):
                logger.error(f"RNAmigos2 model directory not found at {self.model_path}")
                return False
                
            logger.info("RNAmigos2 environment setup completed")
            return True
            
        except Exception as e:
            logger.error(f"Failed to setup RNAmigos2 environment: {e}")
            return False
    
    def predict_interactions(self, 
                           cif_path: str, 
                           residue_list: List[str], 
                           smiles_list: List[str],
                           output_path: str = None) -> Dict[str, Any]:
        """
        Predict RNA-ligand interactions using RNAmigos2
        
        Args:
            cif_path: Path to mmCIF structure file
            residue_list: List of binding site residue identifiers (e.g., ['A.20', 'A.19', 'A.18'])
            smiles_list: List of SMILES strings for ligands
            output_path: Optional path to save results
            
        Returns:
            Dictionary containing prediction results
        """
        try:
            if not self.setup_environment():
                return {"success": False, "error": "Environment setup failed"}
            
            # Create temporary directory for processing
            self.temp_dir = tempfile.mkdtemp()
            
            # Create temporary SMILES file
            smiles_file = os.path.join(self.temp_dir, "ligands.txt")
            with open(smiles_file, 'w') as f:
                for smiles in smiles_list:
                    f.write(f"{smiles}\n")
            
            # Create temporary output file
            if output_path is None:
                output_path = os.path.join(self.temp_dir, "results.csv")
            
            # Prepare residue list string
            residue_str = ",".join(residue_list)
            
            # Build command
            cmd = [
                "python", "rnamigos/inference.py",
                f"cif_path={cif_path}",
                f"residue_list=[{residue_str}]",
                f"ligands_path={smiles_file}",
                f"out_path={output_path}"
            ]
            
            # Change to model directory and run inference
            original_cwd = os.getcwd()
            os.chdir(self.model_path)
            
            # Set up environment variables
            env = os.environ.copy()
            env['PATH'] = f"{self.environment_path}/bin:{env['PATH']}"
            env['VIRTUAL_ENV'] = self.environment_path
            
            logger.info(f"Running RNAmigos2 inference: {' '.join(cmd)}")
            
            result = subprocess.run(
                cmd,
                env=env,
                capture_output=True,
                text=True,
                timeout=300  # 5 minute timeout
            )
            
            os.chdir(original_cwd)
            
            if result.returncode != 0:
                logger.error(f"RNAmigos2 inference failed: {result.stderr}")
                return {
                    "success": False, 
                    "error": f"Inference failed: {result.stderr}"
                }
            
            # Parse results
            results = self._parse_results(output_path)
            
            return {
                "success": True,
                "results": results,
                "output_path": output_path
            }
            
        except subprocess.TimeoutExpired:
            logger.error("RNAmigos2 inference timed out")
            return {"success": False, "error": "Inference timed out"}
        except Exception as e:
            logger.error(f"RNAmigos2 prediction failed: {e}")
            return {"success": False, "error": str(e)}
        finally:
            # Cleanup temporary directory
            if self.temp_dir and os.path.exists(self.temp_dir):
                shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def _parse_results(self, output_path: str) -> Dict[str, Any]:
        """Parse RNAmigos2 output results"""
        try:
            import pandas as pd
            
            if not os.path.exists(output_path):
                return {"error": "Output file not found"}
            
            # Read CSV results
            df = pd.read_csv(output_path)
            
            # Convert to list of dictionaries
            results = []
            for _, row in df.iterrows():
                result_item = {
                    "smiles": row.get("smiles", ""),
                    "score": float(row.get("mixed", row.get("raw_score", 0.0))),
                    "raw_scores": {}
                }
                
                # Add individual model scores if available
                for col in df.columns:
                    if col not in ["smiles", "mixed"]:
                        result_item["raw_scores"][col] = float(row[col])
                
                results.append(result_item)
            
            # Sort by score (higher is better)
            results.sort(key=lambda x: x["score"], reverse=True)
            
            return {
                "interactions": results,
                "total_ligands": len(results),
                "summary": {
                    "best_score": results[0]["score"] if results else 0.0,
                    "worst_score": results[-1]["score"] if results else 0.0,
                    "average_score": sum(r["score"] for r in results) / len(results) if results else 0.0
                }
            }
            
        except Exception as e:
            logger.error(f"Failed to parse RNAmigos2 results: {e}")
            return {"error": f"Failed to parse results: {e}"}
    
    def get_model_info(self) -> Dict[str, Any]:
        """Get model information"""
        return {
            "name": "RNAmigos2",
            "version": "2.0",
            "description": "RNA-ligand interaction prediction using deep graph learning",
            "input_types": ["mmcif", "smiles"],
            "output_types": ["interaction_scores"],
            "model_path": self.model_path,
            "environment_path": self.environment_path
        }
    
    def cleanup(self):
        """Cleanup resources"""
        if self.temp_dir and os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir, ignore_errors=True)
