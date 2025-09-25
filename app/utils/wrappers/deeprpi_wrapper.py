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

logger = logging.getLogger(__name__)

class DeepRPIWrapper:
    """
    Wrapper for DeepRPI model - RNA-protein interaction prediction
    """
    
    def __init__(self, model_path: str = None, environment_path: str = None):
        """
        Initialize DeepRPI wrapper
        
        Args:
            model_path: Path to DeepRPI model directory
            environment_path: Path to DeepRPI virtual environment
        """
        self.model_path = model_path or os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), 'models', 'DeepRPI')
        self.environment_path = environment_path or os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), '.venv_deeprpi')
        
        # Validate paths
        if not os.path.exists(self.model_path):
            raise FileNotFoundError(f"DeepRPI model path not found: {self.model_path}")
        
        if not os.path.exists(self.environment_path):
            raise FileNotFoundError(f"DeepRPI environment path not found: {self.environment_path}")
        
        # Set up Python executable
        self.python_exe = os.path.join(self.environment_path, "bin", "python")
        if not os.path.exists(self.python_exe):
            raise FileNotFoundError(f"Python executable not found at {self.python_exe}")
        
        self._load_model_info()
    
    def _run_script_in_venv(self, script_content: str, input_data: Optional[Dict] = None) -> Dict[str, Any]:
        """
        Run Python script in DeepRPI virtual environment
        
        Args:
            script_content: Python script content to execute
            input_data: Optional input data for the script
            
        Returns:
            Dictionary containing execution results
        """
        try:
            # Create temporary script file
            with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
                f.write(script_content)
                temp_script = f.name
            
            # Prepare command
            cmd = [self.python_exe, temp_script]
            
            # Set environment variables
            env = os.environ.copy()
            env['PYTHONPATH'] = str(self.model_path)
            
            # Run script
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                cwd=self.model_path,
                env=env,
                timeout=300
            )
            
            # Only log errors
            if result.returncode != 0:
                logger.error(f"DeepRPI script failed with return code {result.returncode}")
                if result.stderr:
                    logger.error(f"Script stderr: {result.stderr}")
            
            # Clean up temporary file
            os.unlink(temp_script)
            
            # Parse results
            if result.returncode == 0:
                try:
                    return json.loads(result.stdout)
                except json.JSONDecodeError:
                    return {
                        "success": True,
                        "output": result.stdout,
                        "error": None
                    }
            else:
                return {
                    "success": False,
                    "error": result.stderr,
                    "output": result.stdout
                }
                
        except subprocess.TimeoutExpired:
            return {
                "success": False,
                "error": "DeepRPI prediction timed out"
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"DeepRPI execution failed: {str(e)}"
            }
    
    def _load_model_info(self):
        """Load model information"""
        script_content = '''
import sys
import os
import json
sys.path.insert(0, os.getcwd())

try:
    # Check if model checkpoint exists
    checkpoint_path = "model_checkpoint.ckpt"
    checkpoint_exists = os.path.exists(checkpoint_path)
    
    # Return model info with checkpoint status
    model_info = {
        "success": True,
        "model_name": "DeepRPI",
        "version": "1.0.0",
        "description": "Deep learning-based RNA-protein interaction prediction using ESM-2 protein language model and RNABert RNA language model with bidirectional cross-attention mechanism",
        "input_types": ["protein_sequence", "rna_sequence"],
        "output_types": ["interaction_prediction", "probability", "confidence", "attention_maps"],
        "supported_formats": ["fasta", "text"],
        "max_protein_length": 500,
        "max_rna_length": 220,
        "checkpoint_available": checkpoint_exists,
        "checkpoint_path": checkpoint_path,
        "features": [
            "Deep learning-based prediction",
            "ESM-2 protein language model",
            "RNABert RNA language model", 
            "Bidirectional cross-attention mechanism",
            "Attention heatmap visualization",
            "High accuracy interaction prediction"
        ]
    }
    
    print(json.dumps(model_info))
except Exception as e:
    print(json.dumps({
        "success": False,
        "error": str(e)
    }))
'''
        
        result = self._run_script_in_venv(script_content)
        if result.get("success"):
            self.model_info = result
        else:
            logger.warning(f"Failed to load DeepRPI model info: {result.get('error')}")
            self.model_info = {
                "model_name": "DeepRPI",
                "version": "1.0.0",
                "description": "Deep learning-based RNA-protein interaction prediction",
                "checkpoint_available": False
            }
    
    def predict_interaction(self, protein_sequence: str, rna_sequence: str, 
                          plot_attention: bool = True, output_dir: str = None) -> Dict[str, Any]:
        """
        Predict RNA-protein interaction using the real DeepRPI model
        
        Args:
            protein_sequence: Protein sequence (amino acid sequence)
            rna_sequence: RNA sequence (nucleotide sequence)
            plot_attention: Whether to generate attention heatmaps
            output_dir: Output directory for results
            
        Returns:
            Dictionary containing prediction results
        """
        # Validate input sequences
        if not protein_sequence or not rna_sequence:
            return {
                "success": False,
                "error": "Both protein and RNA sequences are required"
            }
        
        # Validate sequence formats
        valid_aa = set("ACDEFGHIKLMNPQRSTVWY")
        valid_rna = set("AUCG")
        
        if not all(c.upper() in valid_aa for c in protein_sequence):
            return {
                "success": False,
                "error": "Invalid protein sequence. Only standard amino acids (ACDEFGHIKLMNPQRSTVWY) are allowed."
            }
        
        if not all(c.upper() in valid_rna for c in rna_sequence):
            return {
                "success": False,
                "error": "Invalid RNA sequence. Only standard nucleotides (AUCG) are allowed."
            }
        
        # Check sequence lengths
        if len(protein_sequence) > 500:
            return {
                "success": False,
                "error": "Protein sequence too long. Maximum length is 500 amino acids."
            }
        
        if len(rna_sequence) > 220:
            return {
                "success": False,
                "error": "RNA sequence too long. Maximum length is 220 nucleotides."
            }
        
        # Create prediction script that uses the real DeepRPI model
        script_content = f'''
import sys
import os
import json
import tempfile
import torch
import numpy as np
from pathlib import Path
sys.path.insert(0, os.getcwd())

try:
    from deeprpi.utils.prediction import predict_interaction
    
    protein_seq = "{protein_sequence}"
    rna_seq = "{rna_sequence}"
    plot_attention = {"True" if plot_attention else "False"}
    output_dir = "{output_dir or 'temp'}"
    
    # Create output directory
    Path(output_dir).mkdir(exist_ok=True, parents=True)
    
    # Use the actual DeepRPI model checkpoint
    checkpoint_path = "model_checkpoint.ckpt"
    
    # Check if checkpoint exists
    if not os.path.exists(checkpoint_path):
        print(json.dumps({{
            "success": False,
            "error": f"Model checkpoint not found at {{checkpoint_path}}"
        }}))
        sys.exit(1)
    
    # Predict interaction using real model
    result = predict_interaction(
        protein_seq=protein_seq,
        rna_seq=rna_seq,
        checkpoint_path=checkpoint_path,
        plot_attention=plot_attention,
        output_dir=output_dir
    )
    
    if result is not None:
        # Convert numpy arrays to lists for JSON serialization
        if 'protein_attention' in result and result['protein_attention'] is not None:
            if hasattr(result['protein_attention'], 'cpu'):
                result['protein_attention'] = result['protein_attention'].cpu().detach().numpy().tolist()
            else:
                result['protein_attention'] = result['protein_attention'].tolist()
        if 'rna_attention' in result and result['rna_attention'] is not None:
            if hasattr(result['rna_attention'], 'cpu'):
                result['rna_attention'] = result['rna_attention'].cpu().detach().numpy().tolist()
            else:
                result['rna_attention'] = result['rna_attention'].tolist()
        
        result['success'] = True
        result['protein_sequence'] = protein_seq
        result['rna_sequence'] = rna_seq
        result['protein_length'] = len(protein_seq)
        result['rna_length'] = len(rna_seq)
        
        print(json.dumps(result))
    else:
        print(json.dumps({{
            "success": False,
            "error": "Prediction failed - model returned None"
        }}))
        
except Exception as e:
    import traceback
    error_msg = f"DeepRPI prediction error: {{str(e)}}\\nTraceback: {{traceback.format_exc()}}"
    print(json.dumps({{
        "success": False,
        "error": error_msg
    }}))
'''
        
        result = self._run_script_in_venv(script_content)
        
        # Parse the output if it contains JSON
        if result.get("success") and result.get("output"):
            try:
                import json
                # Extract JSON from the output string
                output_lines = result["output"].strip().split('\n')
                json_line = None
                for line in output_lines:
                    if line.strip().startswith('{') and line.strip().endswith('}'):
                        json_line = line.strip()
                        break
                
                if json_line:
                    parsed_result = json.loads(json_line)
                    return parsed_result
            except Exception as e:
                return {
                    "success": False,
                    "error": f"Failed to parse result: {str(e)}"
                }
        
        return result
    
    def get_model_info(self) -> Dict[str, Any]:
        """Get model information"""
        return self.model_info
    
    def validate_sequences(self, protein_sequence: str, rna_sequence: str) -> Dict[str, Any]:
        """
        Validate input sequences
        
        Args:
            protein_sequence: Protein sequence to validate
            rna_sequence: RNA sequence to validate
            
        Returns:
            Dictionary containing validation results
        """
        validation_result = {
            "valid": True,
            "errors": [],
            "warnings": []
        }
        
        # Check if sequences are provided
        if not protein_sequence:
            validation_result["valid"] = False
            validation_result["errors"].append("Protein sequence is required")
        else:
            # Check protein sequence format
            valid_aa = set("ACDEFGHIKLMNPQRSTVWY")
            if not all(c.upper() in valid_aa for c in protein_sequence):
                validation_result["valid"] = False
                validation_result["errors"].append("Invalid protein sequence. Only standard amino acids are allowed.")
            
            # Check protein sequence length
            if len(protein_sequence) > 500:
                validation_result["valid"] = False
                validation_result["errors"].append("Protein sequence too long. Maximum length is 500 amino acids.")
            elif len(protein_sequence) > 300:
                validation_result["warnings"].append("Protein sequence is quite long, which may affect performance")
        
        if not rna_sequence:
            validation_result["valid"] = False
            validation_result["errors"].append("RNA sequence is required")
        else:
            # Check RNA sequence format
            valid_rna = set("AUCG")
            if not all(c.upper() in valid_rna for c in rna_sequence):
                validation_result["valid"] = False
                validation_result["errors"].append("Invalid RNA sequence. Only standard nucleotides (AUCG) are allowed.")
            
            # Check RNA sequence length
            if len(rna_sequence) > 220:
                validation_result["valid"] = False
                validation_result["errors"].append("RNA sequence too long. Maximum length is 220 nucleotides.")
            elif len(rna_sequence) > 150:
                validation_result["warnings"].append("RNA sequence is quite long, which may affect performance")
        
        return validation_result
