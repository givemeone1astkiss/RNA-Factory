"""
UFold Model Wrapper
Fast and Accurate RNA Secondary Structure Prediction with Deep Learning
"""

import os
import subprocess
import tempfile
import logging
from typing import Dict, Any, List
import shutil
from ..path_manager import get_model_path, get_venv_path

logger = logging.getLogger(__name__)


class UFoldWrapper:
    """Wrapper for UFold RNA secondary structure prediction model"""
    
    def __init__(self, model_path: str = None, environment_path: str = None):
        """
        Initialize UFold wrapper
        
        Args:
            model_path: Path to UFold model directory
            environment_path: Path to uv virtual environment for UFold
        """
        self.model_path = model_path or get_model_path("UFold")
        self.environment_path = environment_path or get_venv_path(".venv_ufold")
        self.temp_dir = None
        
        # Validate model path
        if not os.path.exists(self.model_path):
            logger.warning(f"UFold model path not found: {self.model_path}")
            self.model_path = None
        else:
            logger.info(f"UFold model path found: {self.model_path}")
    
    def _setup_environment(self) -> bool:
        """Setup UFold uv virtual environment"""
        try:
            # Check if uv virtual environment exists
            if not os.path.exists(self.environment_path):
                logger.info(f"Creating UFold uv virtual environment: {self.environment_path}")
                
                # Create virtual environment
                subprocess.run(
                    ["uv", "venv", self.environment_path],
                    check=True
                )
                
                # Install UFold and dependencies
                subprocess.run([
                    "uv", "pip", "install", 
                    "--python", f"{self.environment_path}/bin/python",
                    "torch>=2.0.1",
                    "numpy",
                    "munch",
                    "matplotlib",
                    "seaborn",
                    "scipy",
                    "pandas",
                    "scikit-learn",
                    "tqdm",
                    "pillow",
                    "opencv-python"
                ], check=True)
                
                logger.info("UFold environment created successfully")
            else:
                logger.info("UFold environment already exists")
            
            return True
            
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to setup UFold environment: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error setting up UFold environment: {e}")
            return False
    
    def predict(self, sequences: List[str], predict_nc: bool = False) -> Dict[str, Any]:
        """
        Predict RNA secondary structures using UFold
        
        Args:
            sequences: List of RNA sequences
            predict_nc: Whether to predict non-canonical pairs
            
        Returns:
            Dictionary containing prediction results
        """
        if not self.model_path or not os.path.exists(self.model_path):
            return {
                "success": False,
                "error": "UFold model path not found"
            }
        
        if not self._setup_environment():
            return {
                "success": False,
                "error": "Failed to setup UFold environment"
            }
        
        # Check if model file exists
        model_file = os.path.join(self.model_path, "models", "ufold_train_alldata.pt")
        if not os.path.exists(model_file):
            return {
                "success": False,
                "error": f"UFold model file not found: {model_file}. Please download the pre-trained model from: https://drive.google.com/drive/folders/1Sq7MVgFOshGPlumRE_hpNXadvhJKaryi?usp=sharing and place it as models/UFold/models/ufold_train_alldata.pt"
            }
        
        try:
            # Create temporary directory for input/output
            self.temp_dir = tempfile.mkdtemp(prefix="ufold_")
            data_dir = os.path.join(self.temp_dir, "data")
            os.makedirs(data_dir, exist_ok=True)
            
            # Write sequences to input.txt file (UFold expects this format)
            input_file = os.path.join(data_dir, "input.txt")
            with open(input_file, 'w') as f:
                for i, seq in enumerate(sequences):
                    # Ensure seq is a string
                    if not isinstance(seq, str):
                        logger.warning(f"Sequence {i+1} is not a string, skipping")
                        continue
                    
                    # Clean sequence to only contain standard RNA characters
                    clean_seq = ''.join(c for c in seq.upper() if c in 'AUCG')
                    if not clean_seq:
                        logger.warning(f"Sequence {i+1} contains no valid RNA characters, skipping")
                        continue
                    f.write(f">sequence_{i+1}\n{clean_seq}\n")
            
            # Copy data directory to model directory for UFold to find
            model_data_dir = os.path.join(self.model_path, "data")
            if os.path.exists(model_data_dir):
                shutil.rmtree(model_data_dir)
            shutil.copytree(data_dir, model_data_dir)
            
            # Create a modified UFold script that uses available CUDA device
            modified_script = os.path.join(self.temp_dir, "ufold_predict_modified.py")
            self._create_modified_ufold_script(modified_script)
            
            # Prepare UFold command using uv virtual environment
            python_path = f"{self.environment_path}/bin/python"
            cmd = [
                python_path, 
                modified_script,
                "--nc", str(predict_nc)
            ]
            
            # Run UFold
            logger.info(f"Running UFold command: {' '.join(cmd)}")
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                cwd=self.model_path,  # Run in model directory where config and data are located
                timeout=300,  # 5 minute timeout
                env={**os.environ, 'PYTHONPATH': self.model_path}  # Add model path to Python path
            )
            
            if result.returncode != 0:
                logger.error(f"UFold failed: {result.stderr}")
                return {
                    "success": False,
                    "error": f"UFold execution failed: {result.stderr}"
                }
            
            # Parse results (UFold outputs to results/ directory in model path)
            results_dir = os.path.join(self.model_path, "results")
            results = self._parse_results(results_dir, sequences)
            
            return {
                "success": True,
                "results": results,
                "stdout": result.stdout,
                "stderr": result.stderr
            }
            
        except Exception as e:
            logger.error(f"UFold prediction failed: {e}")
            return {
                "success": False,
                "error": str(e)
            }
        finally:
            # Cleanup temporary directory
            if self.temp_dir and os.path.exists(self.temp_dir):
                shutil.rmtree(self.temp_dir)
                self.temp_dir = None
    
    def _parse_results(self, output_dir: str, sequences: List[str]) -> List[Dict[str, Any]]:
        """Parse UFold output results"""
        results = []
        
        try:
            # Look for output files in the results directory
            for i, seq in enumerate(sequences):
                result_data = {
                    "sequence": seq,
                    "format": "ufold",
                    "data": ""
                }
                
                # Look for CT file in save_ct_file subdirectory
                ct_file = os.path.join(output_dir, "save_ct_file", f"sequence_{i+1}.ct")
                if os.path.exists(ct_file):
                    with open(ct_file, 'r') as f:
                        result_data["ct_data"] = f.read()
                
                # Look for BPSEQ file in save_ct_file subdirectory
                bpseq_file = os.path.join(output_dir, "save_ct_file", f"sequence_{i+1}.bpseq")
                if os.path.exists(bpseq_file):
                    with open(bpseq_file, 'r') as f:
                        result_data["bpseq_data"] = f.read()
                
                # Look for figure files in save_varna_fig subdirectory
                figure_file = os.path.join(output_dir, "save_varna_fig", f"sequence_{i+1}.png")
                if os.path.exists(figure_file):
                    result_data["figure_path"] = figure_file
                
                # Extract secondary structure from CT or BPSEQ data
                if "ct_data" in result_data:
                    structure = self._extract_structure_from_ct(result_data["ct_data"])
                    result_data["data"] = structure  # Only show dot-bracket notation
                elif "bpseq_data" in result_data:
                    structure = self._extract_structure_from_bpseq(result_data["bpseq_data"])
                    result_data["data"] = structure  # Only show dot-bracket notation
                
                results.append(result_data)
            
        except Exception as e:
            logger.error(f"Failed to parse UFold results: {e}")
        
        return results
    
    def _extract_structure_from_ct(self, ct_data: str) -> str:
        """Extract dot-bracket notation from CT format"""
        lines = ct_data.strip().split('\n')
        if len(lines) < 2:
            return ""
        
        # Skip header line, extract base pairs
        pairs = {}
        sequence_length = 0
        
        for line in lines[1:]:
            parts = line.split()
            if len(parts) >= 6:
                pos = int(parts[0]) - 1  # Convert to 0-based indexing
                pair_pos = int(parts[4]) - 1  # Convert to 0-based indexing
                sequence_length = max(sequence_length, pos + 1)
                
                # Only store valid base pairs (pair_pos > 0 means paired)
                if pair_pos >= 0 and pair_pos > pos:
                    pairs[pos] = pair_pos
        
        # Convert to dot-bracket notation
        if sequence_length == 0:
            return ""
            
        structure = ['.'] * sequence_length
        
        for pos, pair_pos in pairs.items():
            if pos < sequence_length and pair_pos < sequence_length:
                structure[pos] = '('
                structure[pair_pos] = ')'
        
        return ''.join(structure)
    
    def _create_modified_ufold_script(self, output_path: str):
        """Create a modified UFold script that uses available CUDA device"""
        original_script = os.path.join(self.model_path, "ufold_predict.py")
        
        with open(original_script, 'r') as f:
            content = f.read()
        
        # Replace hardcoded CUDA device with dynamic device selection
        modified_content = content.replace(
            "torch.cuda.set_device(1)",
            "if torch.cuda.is_available():\n        torch.cuda.set_device(0)\n    else:\n        print('CUDA not available, using CPU')"
        )
        
        # Replace hardcoded CUDA device mapping in torch.load
        modified_content = modified_content.replace(
            "map_location='cuda:1'",
            "map_location='cuda:0' if torch.cuda.is_available() else 'cpu'"
        )
        
        # Replace hardcoded CUDA device in device creation
        modified_content = modified_content.replace(
            'torch.device("cuda:1" if torch.cuda.is_available() else "cpu")',
            'torch.device("cuda:0" if torch.cuda.is_available() else "cpu")'
        )
        
        # Replace hardcoded CUDA device in main function
        modified_content = modified_content.replace(
            'torch.device("cuda:0" if torch.cuda.is_available() else "cpu")',
            'torch.device("cuda:0" if torch.cuda.is_available() else "cpu")'
        )
        
        # Fix multiprocessing issue with CUDA
        modified_content = modified_content.replace(
            "torch.multiprocessing.set_sharing_strategy('file_system')",
            "torch.multiprocessing.set_sharing_strategy('file_system')\n    torch.multiprocessing.set_start_method('spawn', force=True)"
        )
        
        # Set num_workers to 0 to avoid multiprocessing issues
        modified_content = modified_content.replace(
            "'num_workers': 6,",
            "'num_workers': 0,"
        )
        
        # Disable VARNA visualization to avoid Java dependency
        modified_content = modified_content.replace(
            "if not args.nc:\n            subprocess.Popen([\"java\", \"-cp\", \"VARNAv3-93.jar\", \"fr.orsay.lri.varna.applications.VARNAcmd\", '-i', 'results/save_ct_file/' + seq_name[0].replace('/','_') + '.ct', '-o', 'results/save_varna_fig/' + seq_name[0].replace('/','_') + '_radiate.png', '-algorithm', 'radiate', '-resolution', '8.0', '-bpStyle', 'lw'], stderr=subprocess.STDOUT, stdout=subprocess.PIPE).communicate()[0]\n        else:\n            subprocess.Popen([\"java\", \"-cp\", \"VARNAv3-93.jar\", \"fr.orsay.lri.varna.applications.VARNAcmd\", '-i', 'results/save_ct_file/' + seq_name[0].replace('/','_') + '.ct', '-o', 'results/save_varna_fig/' + seq_name[0].replace('/','_') + '_radiatenew.png', '-algorithm', 'radiate', '-resolution', '8.0', '-bpStyle', 'lw','-auxBPs', tertiary_bp], stderr=subprocess.STDOUT, stdout=subprocess.PIPE).communicate()[0]",
            "# VARNA visualization disabled - Java not available\n        # if not args.nc:\n        #     subprocess.Popen([\"java\", \"-cp\", \"VARNAv3-93.jar\", \"fr.orsay.lri.varna.applications.VARNAcmd\", '-i', 'results/save_ct_file/' + seq_name[0].replace('/','_') + '.ct', '-o', 'results/save_varna_fig/' + seq_name[0].replace('/','_') + '_radiate.png', '-algorithm', 'radiate', '-resolution', '8.0', '-bpStyle', 'lw'], stderr=subprocess.STDOUT, stdout=subprocess.PIPE).communicate()[0]\n        # else:\n        #     subprocess.Popen([\"java\", \"-cp\", \"VARNAv3-93.jar\", \"fr.orsay.lri.varna.applications.VARNAcmd\", '-i', 'results/save_ct_file/' + seq_name[0].replace('/','_') + '.ct', '-o', 'results/save_varna_fig/' + seq_name[0].replace('/','_') + '_radiatenew.png', '-algorithm', 'radiate', '-resolution', '8.0', '-bpStyle', 'lw','-auxBPs', tertiary_bp], stderr=subprocess.STDOUT, stdout=subprocess.PIPE).communicate()[0]\n        print('VARNA visualization skipped - Java not available')"
        )
        
        # Fix creatmat function to handle invalid one-hot encoding
        modified_content = modified_content.replace(
            "data = ''.join(['AUCG'[list(d).index(1)] for d in data])",
            "data = ''.join(['AUCG'[list(d).index(1)] if 1 in list(d) else 'A' for d in data])"
        )
        
        # Fix tensor type casting issue
        modified_content = modified_content.replace(
            "m1 *= torch.exp(-0.5*t*t)",
            "m1 = m1.float() * torch.exp(-0.5*t*t.float())"
        )
        
        with open(output_path, 'w') as f:
            f.write(modified_content)
    
    def _extract_structure_from_bpseq(self, bpseq_data: str) -> str:
        """Extract dot-bracket notation from BPSEQ format"""
        lines = bpseq_data.strip().split('\n')
        if len(lines) < 2:
            return ""
        
        # Skip header line, extract base pairs
        pairs = {}
        for line in lines[1:]:
            parts = line.split()
            if len(parts) >= 3:
                pos = int(parts[0]) - 1  # Convert to 0-based indexing
                pair_pos = int(parts[2]) - 1  # Convert to 0-based indexing
                if pair_pos > pos:  # Only store upper triangle
                    pairs[pos] = pair_pos
        
        # Convert to dot-bracket notation
        length = max(pairs.keys()) + 1 if pairs else 0
        structure = ['.'] * length
        
        for pos, pair_pos in pairs.items():
            if pos < length and pair_pos < length:
                structure[pos] = '('
                structure[pair_pos] = ')'
        
        return ''.join(structure)
    
    def get_model_info(self) -> Dict[str, Any]:
        """Get UFold model information"""
        return {
            "name": "UFold",
            "description": "Fast and Accurate RNA Secondary Structure Prediction with Deep Learning",
            "version": "1.3",
            "paper": "https://academic.oup.com/nar/article/50/3/e14/6430845",
            "github": "https://github.com/uci-cbcl/UFold",
            "model_path": self.model_path,
            "environment_path": self.environment_path,
            "available": self.model_path and os.path.exists(self.model_path),
            "environment_ready": os.path.exists(self.environment_path),
            "supported_formats": ["ct", "bpseq", "png"],
            "features": [
                "Deep learning-based prediction",
                "Image-like sequence representation",
                "Fully Convolutional Networks (FCNs)",
                "Fast inference (~160ms per sequence)",
                "High accuracy (10-30% improvement over traditional methods)",
                "Support for sequences up to 1600bp"
            ]
        }
    
    def cleanup(self):
        """Cleanup resources"""
        if self.temp_dir and os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
            self.temp_dir = None
