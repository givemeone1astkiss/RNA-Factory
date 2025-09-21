import os
import sys
import subprocess
import logging
from typing import List, Dict, Any, Optional
import re

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
sys.path.insert(0, project_root)

from app.utils.path_manager import get_model_path, get_venv_path

logger = logging.getLogger(__name__)

class Mol2AptamerWrapper:
    """Wrapper for Mol2Aptamer de novo RNA aptamer design model"""
    
    def __init__(self, model_path: str = None, environment_path: str = None):
        """
        Initialize Mol2Aptamer wrapper
        
        Args:
            model_path: Path to Mol2Aptamer model directory
            environment_path: Path to uv virtual environment for Mol2Aptamer
        """
        self.model_path = model_path or get_model_path("Mol2Aptamer")
        self.environment_path = environment_path or get_venv_path(".venv_mol2aptamer")
        
    def setup_environment(self) -> bool:
        """Setup Mol2Aptamer environment using uv"""
        try:
            # Check if environment exists
            if not os.path.exists(self.environment_path):
                logger.error(f"Mol2Aptamer environment not found at {self.environment_path}")
                return False
                
            # Check if model directory exists
            if not os.path.exists(self.model_path):
                logger.error(f"Mol2Aptamer model directory not found at {self.model_path}")
                return False
                
            # Check if inference script exists
            script_path = os.path.join(self.model_path, "mol2aptamer_inference.py")
            if not os.path.exists(script_path):
                logger.error(f"Mol2Aptamer inference script not found at {script_path}")
                return False
                
            logger.info("Mol2Aptamer environment setup completed")
            return True
            
        except Exception as e:
            logger.error(f"Failed to setup Mol2Aptamer environment: {e}")
            return False
    
    def predict_aptamers(self, 
                        smiles: str, 
                        num_sequences: int = 10,
                        max_length: int = 50,
                        temperature: float = 1.0,
                        top_k: int = 50,
                        top_p: float = 0.9,
                        strategy: str = "greedy") -> List[Dict[str, Any]]:
        """
        Generate RNA aptamer sequences from SMILES string
        
        Args:
            smiles: SMILES string of small molecule
            num_sequences: Number of sequences to generate
            max_length: Maximum length of generated sequences
            temperature: Sampling temperature
            top_k: Top-K sampling parameter
            top_p: Top-P sampling parameter
            strategy: Sampling strategy (greedy, top_k, top_p)
            
        Returns:
            List of dictionaries containing generated aptamer sequences
        """
        try:
            if not self.setup_environment():
                raise RuntimeError("Environment setup failed")
            
            # Get python executable from virtual environment
            python_executable = os.path.join(self.environment_path, "bin", "python")
            if not os.path.exists(python_executable):
                raise FileNotFoundError(f"Python executable not found in venv: {python_executable}")
            
            # Map strategy names to match inference script expectations
            strategy_map = {
                'greedy': 'greedy',
                'top_k': 'topk',
                'top_p': 'topp'
            }
            mapped_strategy = strategy_map.get(strategy, 'greedy')
            
            # Build command
            script_path = os.path.join(self.model_path, "mol2aptamer_inference.py")
            cmd = [
                python_executable,
                script_path,
                "--smiles", smiles,
                "--num_sequences", str(num_sequences),
                "--max_length", str(max_length),
                "--temperature", str(temperature),
                "--top_k", str(top_k),
                "--top_p", str(top_p),
                "--strategy", mapped_strategy,
                "--num_generate", str(num_sequences * 10),  # 生成更多候选用于过滤
                "--return_top", str(num_sequences)
            ]
            
            # Set up environment variables
            env = os.environ.copy()
            env['PATH'] = f"{self.environment_path}/bin:{env['PATH']}"
            env['VIRTUAL_ENV'] = self.environment_path
            
            logger.info(f"Running Mol2Aptamer inference: {' '.join(cmd)}")
            
            result = subprocess.run(
                cmd,
                env=env,
                capture_output=True,
                text=True,
                timeout=300  # 5 minute timeout
            )
            
            if result.returncode != 0:
                logger.error(f"Mol2Aptamer inference failed: {result.stderr}")
                raise RuntimeError(f"Inference failed: {result.stderr}")
            
            # Parse results from stdout
            aptamers = self._parse_results(result.stdout)
            
            return aptamers
            
        except subprocess.TimeoutExpired:
            logger.error("Mol2Aptamer inference timed out")
            raise RuntimeError("Inference timed out")
        except Exception as e:
            logger.error(f"Mol2Aptamer generation failed: {e}")
            raise
    
    def _parse_results(self, stdout: str) -> List[Dict[str, Any]]:
        """Parse Mol2Aptamer output results from stdout"""
        try:
            output_lines = stdout.strip().split('\n')
            generated_sequences = []
            
            # 查找 "Top 适配体候选（按ΔG排序）：" 之后的行
            in_results_section = False
            for line in output_lines:
                if "Top 适配体候选（按ΔG排序）：" in line:
                    in_results_section = True
                    continue
                
                if in_results_section and line.strip():
                    try:
                        # 解析格式: "1. Ġ CGA GAGG AGU GGU GG GGU CA GAU GCA CU CGG ACC CC AUU CU CC C   ΔG=-4.10 kcal/mol"
                        # 或者: "1. sequence_text   ΔG=-4.10 kcal/mol"
                        match = re.match(r'^\d+\.\s+(.+?)\s+ΔG=([-\d.]+)\s+kcal/mol', line.strip())
                        if match:
                            sequence_text = match.group(1).strip()
                            delta_g = float(match.group(2))
                            
                            # 清理序列文本，移除BPE token标记和特殊字符
                            clean_sequence = sequence_text.replace('Ġ', '').replace('č', '').replace('Ċ', '').replace(' ', '')
                            # 只保留RNA碱基字符
                            clean_sequence = ''.join([c for c in clean_sequence if c in 'ACGU'])
                            
                            generated_sequences.append({
                                "sequence": clean_sequence,
                                "length": len(clean_sequence),
                                "delta_g": delta_g
                            })
                    except Exception as e:
                        logger.warning(f"Failed to parse line: {line}. Error: {e}")
                        continue

            # 如果没有找到结果，尝试解析其他格式
            if not generated_sequences:
                for line in output_lines:
                    if (line.strip() and 
                        not line.startswith("Using device") and 
                        not line.startswith("模型嵌入层") and 
                        not line.startswith("SMILES嵌入层") and 
                        not line.startswith("RNA嵌入层") and 
                        not line.startswith("原始权重") and 
                        not line.startswith("跳过冗余键") and 
                        not line.startswith("权重加载成功") and 
                        not line.startswith("输入SMILES") and 
                        not line.startswith("Top 适配体候选")):
                        try:
                            # 尝试解析简单格式
                            if "ΔG=" in line and "kcal/mol" in line:
                                parts = line.split("ΔG=")
                                if len(parts) == 2:
                                    sequence_part = parts[0].strip()
                                    delta_g_part = parts[1].split("kcal/mol")[0].strip()
                                    
                                    # 清理序列，移除BPE token标记和特殊字符
                                    clean_sequence = sequence_part.replace('Ġ', '').replace('č', '').replace('Ċ', '').replace(' ', '')
                                    # 只保留RNA碱基字符
                                    clean_sequence = ''.join([c for c in clean_sequence if c in 'ACGU'])
                                    
                                    generated_sequences.append({
                                        "sequence": clean_sequence,
                                        "length": len(clean_sequence),
                                        "delta_g": float(delta_g_part)
                                    })
                        except Exception as e:
                            logger.warning(f"Failed to parse alternative format line: {line}. Error: {e}")
                            continue

            return generated_sequences
            
        except Exception as e:
            logger.error(f"Failed to parse Mol2Aptamer results: {e}")
            return []
    
    def get_model_info(self) -> Dict[str, Any]:
        """Get model information"""
        return {
            "name": "Mol2Aptamer",
            "version": "1.0",
            "description": "De novo RNA aptamer design from small molecule SMILES strings",
            "input_types": ["smiles"],
            "output_types": ["rna_sequences", "aptamer_candidates"],
            "model_path": self.model_path,
            "environment_path": self.environment_path
        }