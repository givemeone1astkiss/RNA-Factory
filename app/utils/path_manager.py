"""
路径管理工具
动态获取项目根目录和模型路径，避免硬编码绝对路径
"""

import os
import sys
from pathlib import Path
from typing import Optional

def get_project_root() -> str:
    """
    获取项目根目录的绝对路径
    
    Returns:
        str: 项目根目录的绝对路径
    """
    # 方法1: 通过当前文件路径查找项目根目录
    current_file = Path(__file__).resolve()
    
    # 从当前文件向上查找，直到找到包含pyproject.toml的目录
    for parent in current_file.parents:
        if (parent / "pyproject.toml").exists():
            return str(parent)
    
    # 方法2: 通过环境变量获取
    project_root = os.environ.get('RNA_FACTORY_ROOT')
    if project_root and Path(project_root).exists():
        return project_root
    
    # 方法3: 通过当前工作目录查找
    cwd = Path.cwd()
    for parent in cwd.parents:
        if (parent / "pyproject.toml").exists():
            return str(parent)
    
    # 方法4: 通过sys.path查找
    for path in sys.path:
        if path and path != '':
            path_obj = Path(path)
            if path_obj.exists() and (path_obj / "pyproject.toml").exists():
                return str(path_obj)
    
    # 如果都找不到，返回当前工作目录
    return str(Path.cwd())

def get_model_path(model_name: str) -> str:
    """
    获取指定模型的路径
    
    Args:
        model_name: 模型名称 (如 'BPfold', 'UFold', 'rnamigos2' 等)
        
    Returns:
        str: 模型目录的绝对路径
    """
    project_root = get_project_root()
    model_path = Path(project_root) / "models" / model_name
    
    if not model_path.exists():
        raise FileNotFoundError(f"Model directory not found: {model_path}")
    
    return str(model_path)

def get_venv_path(venv_name: str) -> str:
    """
    获取指定虚拟环境的路径
    
    Args:
        venv_name: 虚拟环境名称 (如 '.venv_bpfold', '.venv_ufold' 等)
        
    Returns:
        str: 虚拟环境目录的绝对路径
    """
    project_root = get_project_root()
    venv_path = Path(project_root) / venv_name
    
    if not venv_path.exists():
        raise FileNotFoundError(f"Virtual environment not found: {venv_path}")
    
    return str(venv_path)

def get_models_dir() -> str:
    """
    获取models目录的路径
    
    Returns:
        str: models目录的绝对路径
    """
    project_root = get_project_root()
    models_dir = Path(project_root) / "models"
    
    if not models_dir.exists():
        raise FileNotFoundError(f"Models directory not found: {models_dir}")
    
    return str(models_dir)

def get_data_dir() -> str:
    """
    获取data目录的路径
    
    Returns:
        str: data目录的绝对路径
    """
    project_root = get_project_root()
    data_dir = Path(project_root) / "data"
    
    if not data_dir.exists():
        # 如果data目录不存在，创建它
        data_dir.mkdir(exist_ok=True)
    
    return str(data_dir)

def get_temp_dir() -> str:
    """
    获取临时目录的路径
    
    Returns:
        str: 临时目录的绝对路径
    """
    project_root = get_project_root()
    temp_dir = Path(project_root) / "temp"
    
    # 如果temp目录不存在，创建它
    temp_dir.mkdir(exist_ok=True)
    
    return str(temp_dir)

def validate_paths() -> dict:
    """
    验证所有关键路径是否存在
    
    Returns:
        dict: 路径验证结果
    """
    results = {
        "project_root": {"path": get_project_root(), "exists": True},
        "models_dir": {"path": get_models_dir(), "exists": True},
        "data_dir": {"path": get_data_dir(), "exists": True},
        "temp_dir": {"path": get_temp_dir(), "exists": True}
    }
    
    # 检查各个模型路径
    model_names = ["BPfold", "UFold", "rnamigos2", "mxfold2", "RNAformer", "rnaflow"]
    for model_name in model_names:
        try:
            model_path = get_model_path(model_name)
            results[f"model_{model_name.lower()}"] = {"path": model_path, "exists": True}
        except FileNotFoundError:
            results[f"model_{model_name.lower()}"] = {"path": f"models/{model_name}", "exists": False}
    
    # 检查各个虚拟环境路径
    venv_names = [".venv", ".venv_bpfold", ".venv_ufold", ".venv_rnamigos2", 
                  ".venv_mxfold2", ".venv_rnaformer", ".venv_rnaflow"]
    for venv_name in venv_names:
        try:
            venv_path = get_venv_path(venv_name)
            results[f"venv_{venv_name.replace('.', '')}"] = {"path": venv_path, "exists": True}
        except FileNotFoundError:
            results[f"venv_{venv_name.replace('.', '')}"] = {"path": venv_name, "exists": False}
    
    return results

# 全局变量，用于缓存项目根目录
_project_root: Optional[str] = None

def get_cached_project_root() -> str:
    """
    获取缓存的项目根目录，避免重复计算
    
    Returns:
        str: 项目根目录的绝对路径
    """
    global _project_root
    if _project_root is None:
        _project_root = get_project_root()
    return _project_root

# 导出主要函数
__all__ = [
    'get_project_root',
    'get_model_path', 
    'get_venv_path',
    'get_models_dir',
    'get_data_dir',
    'get_temp_dir',
    'validate_paths',
    'get_cached_project_root'
]
