"""
RNA-FrameFlow Model Wrapper
Flow Matching for de novo 3D RNA Backbone Design
"""

import os
import sys
import subprocess
import tempfile
import logging
from typing import Dict, Any, List, Optional
import json

# 禁用Lightning日志
logging.getLogger("pytorch_lightning").setLevel(logging.ERROR)
logging.getLogger("lightning").setLevel(logging.ERROR)
logging.getLogger("pytorch_lightning.utilities").setLevel(logging.ERROR)
logging.getLogger("pytorch_lightning.trainer").setLevel(logging.ERROR)
logging.getLogger("pytorch_lightning.callbacks").setLevel(logging.ERROR)

# 设置环境变量禁用Lightning日志
os.environ["PYTORCH_LIGHTNING_LOGGING_LEVEL"] = "ERROR"

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
sys.path.insert(0, project_root)

from app.utils.path_manager import get_model_path, get_venv_path

logger = logging.getLogger(__name__)

class RNAFrameFlowWrapper:
    """Wrapper for RNA-FrameFlow 3D RNA backbone design model"""
    
    def __init__(self, model_path: str = None, environment_path: str = None):
        """
        Initialize RNA-FrameFlow wrapper
        
        Args:
            model_path: Path to RNA-FrameFlow model directory
            environment_path: Path to uv virtual environment for RNA-FrameFlow
        """
        self.model_path = model_path or get_model_path("rna-backbone-design")
        self.environment_path = environment_path or "/home/zhangliqin/RNA-Factory/.venv_rnaframeflow"
        
        # 检查环境是否存在
        if not os.path.exists(self.environment_path):
            logger.error(f"RNA-FrameFlow environment not found at {self.environment_path}")
            raise FileNotFoundError(f"RNA-FrameFlow environment not found at {self.environment_path}")
        
        logger.info(f"RNA-FrameFlow wrapper initialized with environment: {self.environment_path}")
    
    def design_rna_backbone(self,
                          sequence_length: int = 50,
                          num_sequences: int = 5,
                          temperature: float = 1.0,
                          random_seed: int = None,
                          num_timesteps: int = 50,
                          min_t: float = 0.01,
                          exp_rate: int = 10,
                          self_condition: bool = True,
                          overwrite: bool = False,
                          **kwargs) -> Dict[str, Any]:
        """
        Design RNA backbone structures using RNA-FrameFlow
        
        Args:
            sequence_length: Length of RNA structures to generate (10-200)
            num_sequences: Number of structures to generate (1-20)
            temperature: Sampling temperature (0.1-2.0)
            random_seed: Random seed for reproducible results
            num_timesteps: Number of timesteps for sampling (10-200)
            min_t: Minimum time step for interpolation (0.001-0.1)
            exp_rate: Exponential rate for sampling schedule (1-50)
            self_condition: Enable self-conditioning during sampling
            overwrite: Overwrite existing output files
            **kwargs: Additional parameters
            
        Returns:
            Dict containing generated structures
        """
        try:
            # 验证输入参数
            if not isinstance(sequence_length, int) or sequence_length < 10 or sequence_length > 200:
                raise ValueError("Sequence length must be an integer between 10 and 200")
            
            if not isinstance(num_sequences, int) or num_sequences < 1 or num_sequences > 20:
                raise ValueError("Number of sequences must be an integer between 1 and 20")
            
            if not isinstance(temperature, (int, float)) or temperature < 0.1 or temperature > 2.0:
                raise ValueError("Temperature must be a number between 0.1 and 2.0")
            
            # 创建临时输入文件
            with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
                input_data = {
                    'sequence_length': sequence_length,
                    'num_sequences': num_sequences,
                    'temperature': temperature,
                    'random_seed': random_seed,
                    'num_timesteps': num_timesteps,
                    'min_t': min_t,
                    'exp_rate': exp_rate,
                    'self_condition': self_condition,
                    'overwrite': overwrite
                }
                json.dump(input_data, f)
                input_file = f.name
            
            try:
                # 创建临时输出文件
                with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
                    output_file = f.name
                
                # 构建Python脚本路径
                script_path = os.path.join(self.model_path, 'rnaframeflow_inference.py')
                
                # 检查脚本是否存在
                if not os.path.exists(script_path):
                    raise FileNotFoundError(f"RNA-FrameFlow inference script not found at {script_path}")
                
                # 设置环境变量
                env = os.environ.copy()
                env['PATH'] = f"{self.environment_path}/bin:{env['PATH']}"
                env['VIRTUAL_ENV'] = self.environment_path
                env['PYTHONPATH'] = f"{self.model_path}:{env.get('PYTHONPATH', '')}"
                # 禁用Lightning日志
                env['PYTORCH_LIGHTNING_LOGGING_LEVEL'] = 'ERROR'
                
                # 运行RNA-FrameFlow推理
                python_executable = os.path.join(self.environment_path, "bin", "python")
                
                # 确保脚本使用正确的Python解释器
                with open(script_path, 'r') as f:
                    script_content = f.read()
                
                # 替换shebang行
                if script_content.startswith('#!/usr/bin/env python3'):
                    script_content = f'#!{python_executable}\n' + script_content.split('\n', 1)[1]
                    with open(script_path, 'w') as f:
                        f.write(script_content)
                    os.chmod(script_path, 0o755)
                
                
                result = subprocess.run(
                    [python_executable, script_path, input_file, output_file],
                    env=env,
                    capture_output=True,
                    text=True,
                    timeout=300,  # 5分钟超时
                    cwd=self.model_path
                )
                
                
                # 即使出现段错误，也尝试读取结果文件
                if result.returncode != 0 and result.returncode != -11:
                    logger.error(f"RNA-FrameFlow inference failed: {result.stderr}")
                    raise RuntimeError(f"RNA-FrameFlow inference failed: {result.stderr}")
                
                # 检查输出文件是否存在
                if not os.path.exists(output_file):
                    logger.error(f"Output file not found: {output_file}")
                    raise RuntimeError(f"Output file not found: {output_file}")
                
                # 读取结果
                with open(output_file, 'r') as f:
                    result_data = json.load(f)
                
                # 如果推理成功但出现段错误，记录警告
                if result.returncode == -11:
                    logger.warning("RNA-FrameFlow inference completed with segmentation fault, but results were generated successfully")
                
                # 添加PDB文件路径信息
                if result_data.get('success') and result_data.get('structures'):
                    # 使用根目录下的temp文件夹
                    project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
                    temp_dir = os.path.join(project_root, 'temp', 'samples')
                    for i, structure in enumerate(result_data['structures']):
                        pdb_filename = f"na_sample_{i}.pdb"
                        pdb_path = os.path.join(temp_dir, f"length_{sequence_length}", pdb_filename)
                        structure['pdb_file_path'] = pdb_path
                        structure['pdb_filename'] = pdb_filename
                
                return result_data
                
            finally:
                # 清理临时文件（保留输出文件，因为推理脚本已经将其保存到temp目录）
                if os.path.exists(input_file):
                    os.unlink(input_file)
                # 不删除output_file，因为推理脚本已经将其保存到temp目录
                # 但是需要确保输出文件存在
                if not os.path.exists(output_file):
                    logger.warning(f"Output file not found: {output_file}")
                    # 创建一个空的成功结果
                    empty_result = {
                        'success': True,
                        'structures': [],
                        'statistics': {
                            'total_structures': 0,
                            'average_length': 0.0,
                            'average_confidence': 0.0
                        },
                        'model_info': {
                            'name': 'RNA-FrameFlow',
                            'type': '3D Structure Design',
                            'description': 'Flow Matching for 3D RNA Backbone Structure Design',
                            'model_used': 'real_official',
                            'note': 'Generates 3D structures only - no sequence information'
                        }
                    }
                    with open(output_file, 'w') as f:
                        json.dump(empty_result, f, indent=2)
                    
        except subprocess.TimeoutExpired:
            logger.error("RNA-FrameFlow inference timed out")
            return {
                'success': False,
                'error': 'RNA-FrameFlow inference timed out',
                'sequences': [],
                'structures': []
            }
        except Exception as e:
            logger.error(f"Error in RNA-FrameFlow inference: {e}")
            return {
                'success': False,
                'error': str(e),
                'sequences': [],
                'structures': []
            }
    
    
    def get_model_info(self) -> Dict[str, Any]:
        """
        Get information about the model
        
        Returns:
            Dict containing model information
        """
        return {
            'name': 'RNA-FrameFlow',
            'type': 'De Novo Design',
            'description': 'Flow Matching for 3D RNA Backbone Structure Design',
            'paper': 'https://arxiv.org/abs/2406.13839',
            'github': 'https://github.com/rish-16/rna-backbone-design',
            'environment_path': self.environment_path,
            'environment_ready': os.path.exists(self.environment_path),
            'model_path': self.model_path
        }