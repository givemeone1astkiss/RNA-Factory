#!/usr/bin/env python3
"""
Reformer model wrapper
For predicting protein-RNA binding affinity
"""

import os
import sys
import json
import subprocess
import tempfile
from typing import Dict, Any, Optional

class ReformerWrapper:
    """Reformer model wrapper class"""
    
    def __init__(self):
        self.model_name = "Reformer"
        self.model_type = "Interaction Prediction"
        self.environment_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), ".venv_reformer")
        self.model_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), "models", "Reformer")
        self.inference_script = os.path.join(self.model_path, "reformer_inference.py")
        
        # Check if environment exists
        if not os.path.exists(self.environment_path):
            raise RuntimeError(f"Reformer virtual environment not found: {self.environment_path}")
        
        # Check if inference script exists
        if not os.path.exists(self.inference_script):
            raise RuntimeError(f"Reformer inference script not found: {self.inference_script}")
    
    def get_model_info(self) -> Dict[str, Any]:
        """Get model information"""
        return {
            "name": self.model_name,
            "type": self.model_type,
            "description": "Deep learning model for predicting protein-RNA binding affinity at single-base resolution",
            "paper": "https://www.sciencedirect.com/science/article/pii/S2666389924003222",
            "github": "https://github.com/xilinshen/Reformer",
            "input_format": "cDNA sequence (FASTA format)",
            "output_format": "Binding affinity scores and statistics",
            "supported_rbps": ["AARS", "AATF", "ABCF1", "AGGF1", "AKAP1", "AKAP8L", "APOBEC3C", "AQR", "BCCIP", "BCLAF1", "BUD13", "CDC40", "CPEB4", "CPSF6", "CSTF2", "CSTF2T", "DDX21", "DDX24", "DDX3X", "DDX42", "DDX51", "DDX52", "DDX55", "DDX59", "DDX6", "DGCR8", "DHX30", "DKC1", "DROSHA", "EFTUD2", "EIF3D", "EIF3G", "EIF3H", "EIF4G2", "EWSR1", "EXOSC5", "FAM120A", "FASTKD2", "FKBP4", "FMR1", "FTO", "FUBP3", "FUS", "FXR1", "FXR2", "G3BP1", "GEMIN5", "GNL3", "GPKOW", "GRSF1", "GRWD1", "GTF2F1", "HLTF", "HNRNPA1", "HNRNPC", "HNRNPK", "HNRNPL", "HNRNPM", "HNRNPU", "HNRNPUL1", "IGF2BP1", "IGF2BP2", "IGF2BP3", "ILF3", "KHDRBS1", "KHSRP", "LARP4", "LARP7", "LIN28B", "LSM11", "MATR3", "METAP2", "MTPAP", "NCBP2", "NIP7", "NIPBL", "NKRF", "NOL12", "NOLC1", "NONO", "NPM1", "NSUN2", "PABPC4", "PABPN1", "PCBP1", "PCBP2", "PHF6", "POLR2G", "PPIG", "PPIL4", "PRPF4", "PRPF8", "PTBP1", "PUM1", "PUM2", "PUS1", "QKI", "RBFOX2", "RBM15", "RBM22", "RBM5", "RPS11", "RPS3", "SAFB", "SAFB2", "SBDS", "SDAD1", "SERBP1", "SF3A3", "SF3B1", "SF3B4", "SFPQ", "SLBP", "SLTM", "SMNDC1", "SND1", "SRSF1", "SRSF7", "SRSF9", "SSB", "STAU2", "SUB1", "SUGP2", "SUPV3L1", "TAF15", "TARDBP", "TBRG4", "TIA1", "TIAL1", "TRA2A", "TROVE2", "U2AF1", "U2AF2", "UCHL5", "UPF1", "UTP18", "UTP3", "WDR3", "WDR43", "WRN", "XPO5", "XRCC6", "XRN2", "YBX3", "YWHAG", "ZC3H11A", "ZC3H8", "ZNF622", "ZNF800", "ZRANB2"],
            "supported_cell_lines": ["HepG2", "K562", "adrenal_gland"]
        }
    
    def predict_binding_affinity(self, 
                                sequence: str, 
                                rbp_name: str = "U2AF2", 
                                cell_line: str = "HepG2",
                                model_path: Optional[str] = None) -> Dict[str, Any]:
        """
        Predict protein-RNA binding affinity
        
        Args:
            sequence: cDNA sequence
            rbp_name: RNA-binding protein name
            cell_line: Cell line name
            model_path: Model file path
        
        Returns:
            dict: Prediction results
        """
        try:
            # Validate input
            if not sequence or len(sequence.strip()) == 0:
                return {
                    "success": False,
                    "error": "cDNA sequence cannot be empty"
                }
            
            # Clean sequence
            sequence = sequence.upper().strip()
            
            valid_bases = set('ATCGN')
            if not all(base in valid_bases for base in sequence):
                return {
                    "success": False,
                    "error": "Sequence can only contain ATCGN characters (please provide cDNA sequence)"
                }
            
            # Check sequence length
            if len(sequence) < 10:
                return {
                    "success": False,
                    "error": "cDNA sequence must be at least 10 bases long"
                }
            
            # If sequence is too long, truncate to 512bp
            if len(sequence) > 512:
                sequence = sequence[:512]
            
            # Create temp directory if it doesn't exist
            temp_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), "temp")
            os.makedirs(temp_dir, exist_ok=True)
            
            # Create temporary input file
            input_file = os.path.join(temp_dir, f"reformer_input_{os.getpid()}_{hash(sequence) % 10000}.txt")
            with open(input_file, 'w') as f:
                f.write(sequence)
            
            # Create temporary output file
            output_file = os.path.join(temp_dir, f"reformer_output_{os.getpid()}_{hash(sequence) % 10000}.json")
            
            try:
                # Build command
                python_executable = os.path.join(self.environment_path, "bin", "python")
                
                cmd = [
                    python_executable,
                    self.inference_script,
                    "--sequence", sequence,
                    "--rbp", rbp_name,
                    "--cell_line", cell_line,
                    "--output", output_file
                ]
                
                if model_path:
                    cmd.extend(["--model_path", model_path])
                
                # Set environment variables
                env = os.environ.copy()
                env['PATH'] = f"{self.environment_path}/bin:{env['PATH']}"
                env['VIRTUAL_ENV'] = self.environment_path
                env['PYTHONPATH'] = f"{self.model_path}:{env.get('PYTHONPATH', '')}"
                
                # Execute inference
                print(f"🔮 Executing Reformer inference: {' '.join(cmd)}")
                result = subprocess.run(
                    cmd,
                    env=env,
                    capture_output=True,
                    text=True,
                    timeout=300,  # 5分钟超时
                    cwd=self.model_path
                )
                
                # Output inference script logs
                if result.stdout:
                    print("📊 Reformer inference output:")
                    print(result.stdout)
                if result.stderr:
                    print("⚠️ Reformer inference errors:")
                    print(result.stderr)
                
                # Check execution result
                if result.returncode != 0:
                    return {
                        "success": False,
                        "error": f"Inference execution failed: {result.stderr}",
                        "stdout": result.stdout
                    }
                
                # Read output results
                if os.path.exists(output_file):
                    with open(output_file, 'r') as f:
                        prediction_result = json.load(f)
                    
                    # Add additional information
                    prediction_result.update({
                        "sequence_length": len(sequence),
                        "rbp_name": rbp_name,
                        "cell_line": cell_line,
                        "model_name": self.model_name
                    })
                    
                    return prediction_result
                else:
                    return {
                        "success": False,
                        "error": "Output file not generated"
                    }
            
            finally:
                # Clean up input file, keep output file for debugging
                try:
                    if os.path.exists(input_file):
                        os.unlink(input_file)
                    # Keep output file in temp directory, do not delete
                    # if os.path.exists(output_file):
                    #     os.unlink(output_file)
                except:
                    pass
        
        except subprocess.TimeoutExpired:
            return {
                "success": False,
                "error": "Inference timeout (5 minutes)"
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"Error occurred during inference: {str(e)}"
            }
    
    def is_available(self) -> bool:
        """Check if model is available"""
        try:
            # Check environment
            if not os.path.exists(self.environment_path):
                return False
            
            # Check inference script
            if not os.path.exists(self.inference_script):
                return False
            
            # Try running simple test
            test_result = self.predict_binding_affinity("ATCGATCGATCG", "U2AF2", "HepG2")
            return test_result.get("success", False)
        
        except:
            return False

# Create global instance
reformer_wrapper = ReformerWrapper()
