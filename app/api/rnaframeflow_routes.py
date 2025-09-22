"""
RNA-FrameFlow API Routes
"""

from flask import Blueprint, request, jsonify, send_file, abort
import logging
import os
import sys
from pathlib import Path

# Add the app directory to Python path
app_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, app_dir)

from utils.wrappers.rnaframeflow_wrapper import RNAFrameFlowWrapper

logger = logging.getLogger(__name__)

rnaframeflow_bp = Blueprint("rnaframeflow", __name__)

# Global wrapper instance
rnaframeflow_wrapper = None

def get_wrapper():
    """Get or create RNA-FrameFlow wrapper instance"""
    global rnaframeflow_wrapper
    if rnaframeflow_wrapper is None:
        try:
            rnaframeflow_wrapper = RNAFrameFlowWrapper()
            logger.info("RNA-FrameFlow wrapper created successfully")
        except Exception as e:
            logger.error(f"Failed to create RNA-FrameFlow wrapper: {e}")
            return None
    return rnaframeflow_wrapper

@rnaframeflow_bp.route('/design', methods=['POST'])
def design_rna_backbone():
    """Design RNA backbone structures using RNA-FrameFlow"""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({
                "success": False,
                "error": "No input data provided"
            }), 400
        
        # Extract parameters
        sequence_length = data.get('sequence_length', 50)
        num_sequences = data.get('num_sequences', 5)
        temperature = data.get('temperature', 1.0)
        random_seed = data.get('random_seed', None)
        num_timesteps = data.get('num_timesteps', 50)
        min_t = data.get('min_t', 0.01)
        exp_rate = data.get('exp_rate', 10)
        self_condition = data.get('self_condition', True)
        overwrite = data.get('overwrite', False)
        
        # Validate parameters
        if not isinstance(sequence_length, int) or sequence_length < 10 or sequence_length > 200:
            return jsonify({
                "success": False,
                "error": "Sequence length must be an integer between 10 and 200"
            }), 400
        
        if not isinstance(num_sequences, int) or num_sequences < 1 or num_sequences > 20:
            return jsonify({
                "success": False,
                "error": "Number of sequences must be an integer between 1 and 20"
            }), 400
        
        if not isinstance(temperature, (int, float)) or temperature < 0.1 or temperature > 2.0:
            return jsonify({
                "success": False,
                "error": "Temperature must be a number between 0.1 and 2.0"
            }), 400
        
        if not isinstance(num_timesteps, int) or num_timesteps < 10 or num_timesteps > 200:
            return jsonify({
                "success": False,
                "error": "Sampling timesteps must be an integer between 10 and 200"
            }), 400
        
        if not isinstance(min_t, (int, float)) or min_t < 0.001 or min_t > 0.1:
            return jsonify({
                "success": False,
                "error": "Minimum time must be a number between 0.001 and 0.1"
            }), 400
        
        if not isinstance(exp_rate, int) or exp_rate < 1 or exp_rate > 50:
            return jsonify({
                "success": False,
                "error": "Exponential rate must be an integer between 1 and 50"
            }), 400
        
        # Get wrapper
        wrapper = get_wrapper()
        if not wrapper:
            return jsonify({
                "success": False,
                "error": "Failed to initialize RNA-FrameFlow wrapper"
            }), 500
        
        # Design RNA backbone
        result = wrapper.design_rna_backbone(
            sequence_length=sequence_length,
            num_sequences=num_sequences,
            temperature=temperature,
            random_seed=random_seed,
            num_timesteps=num_timesteps,
            min_t=min_t,
            exp_rate=exp_rate,
            self_condition=self_condition,
            overwrite=overwrite
        )
        
        if result['success']:
            return jsonify({
                "success": True,
                "result": result
            })
        else:
            return jsonify({
                "success": False,
                "error": result.get('error', 'Unknown error occurred')
            }), 500
            
    except Exception as e:
        logger.error(f"Error in design_rna_backbone: {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@rnaframeflow_bp.route('/info', methods=['GET'])
def get_model_info():
    """Get RNA-FrameFlow model information"""
    try:
        wrapper = get_wrapper()
        if not wrapper:
            return jsonify({
                "success": False,
                "error": "Failed to initialize RNA-FrameFlow wrapper"
            }), 500
        
        info = wrapper.get_model_info()
        return jsonify({
            "success": True,
            "info": info
        })
        
    except Exception as e:
        logger.error(f"Error in get_model_info: {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@rnaframeflow_bp.route('/status', methods=['GET'])
def get_model_status():
    """Get RNA-FrameFlow model status"""
    try:
        wrapper = get_wrapper()
        if not wrapper:
            return jsonify({
                "success": False,
                "status": "unavailable",
                "error": "Failed to initialize RNA-FrameFlow wrapper"
            })
        
        return jsonify({
            "success": True,
            "status": "available" if wrapper.is_loaded else "loading",
            "loaded": wrapper.is_loaded,
            "device": str(wrapper.device)
        })
        
    except Exception as e:
        logger.error(f"Error in get_model_status: {e}")
        return jsonify({
            "success": False,
            "status": "error",
            "error": str(e)
        }), 500

@rnaframeflow_bp.route('/download/<path:filename>', methods=['GET'])
def download_pdb_file(filename):
    """Download PDB file"""
    try:
        # 构建文件路径（使用根目录下的temp文件夹）
        # 从API文件路径: /home/zhangliqin/RNA-Factory/app/api/rnaframeflow_routes.py
        # 回到项目根目录: /home/zhangliqin/RNA-Factory
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        temp_samples_dir = os.path.join(project_root, 'temp', 'samples')
        
        # 支持两种路径格式：
        # 1. 直接文件名: na_sample_0.pdb
        # 2. 完整路径: length_25/na_sample_0.pdb
        if '/' in filename:
            # 完整路径
            file_path = os.path.join(temp_samples_dir, filename)
        else:
            # 直接文件名，需要查找对应的目录
            if os.path.exists(temp_samples_dir):
                # 查找包含该文件的子目录
                for subdir in os.listdir(temp_samples_dir):
                    if subdir.startswith('length_'):
                        potential_file = os.path.join(temp_samples_dir, subdir, filename)
                        if os.path.exists(potential_file):
                            file_path = potential_file
                            break
                else:
                    # 如果没找到，尝试直接路径
                    file_path = os.path.join(temp_samples_dir, filename)
            else:
                file_path = os.path.join(temp_samples_dir, filename)
        
        # 检查文件是否存在
        if not os.path.exists(file_path):
            logger.error(f"PDB file not found: {file_path}")
            logger.error(f"Available files in temp/samples:")
            if os.path.exists(temp_samples_dir):
                for root, dirs, files in os.walk(temp_samples_dir):
                    for file in files:
                        logger.error(f"  - {os.path.join(root, file)}")
            abort(404)
        
        # 发送文件
        return send_file(
            file_path,
            as_attachment=True,
            download_name=os.path.basename(filename),
            mimetype='text/plain'
        )
        
    except Exception as e:
        logger.error(f"Error downloading PDB file: {e}")
        abort(500)

@rnaframeflow_bp.route('/clear-temp', methods=['POST'])
def clear_temp_folder():
    """Clear temp folder contents"""
    try:
        import shutil
        
        # 构建temp目录路径
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        temp_dir = os.path.join(project_root, 'temp')
        
        if os.path.exists(temp_dir):
            # 删除temp目录下的所有内容
            for item in os.listdir(temp_dir):
                item_path = os.path.join(temp_dir, item)
                if os.path.isdir(item_path):
                    shutil.rmtree(item_path)
                else:
                    os.remove(item_path)
            
            logger.info(f"Cleared temp folder: {temp_dir}")
            return jsonify({
                "success": True,
                "message": "Temp folder cleared successfully"
            })
        else:
            logger.info("Temp folder does not exist, nothing to clear")
            return jsonify({
                "success": True,
                "message": "Temp folder does not exist"
            })
        
    except Exception as e:
        logger.error(f"Error clearing temp folder: {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500
