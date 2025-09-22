#!/usr/bin/env python3
"""
Reformer模型API路由
"""

from flask import Blueprint, request, jsonify
from app.utils.wrappers.reformer_wrapper import reformer_wrapper
import logging

# 创建蓝图
reformer_bp = Blueprint('reformer', __name__)

# 设置日志
logger = logging.getLogger(__name__)

@reformer_bp.route('/info', methods=['GET'])
def get_model_info():
    """获取Reformer模型信息"""
    try:
        info = reformer_wrapper.get_model_info()
        return jsonify({
            "success": True,
            "info": info
        })
    except Exception as e:
        logger.error(f"获取Reformer模型信息失败: {str(e)}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@reformer_bp.route('/predict', methods=['POST'])
def predict_binding_affinity():
    """预测蛋白质-RNA结合亲和力"""
    try:
        data = request.get_json()
        
        # 验证输入数据
        if not data:
            return jsonify({
                "success": False,
                "error": "请求数据不能为空"
            }), 400
        
        sequence = data.get('sequence', '').strip()
        rbp_name = data.get('rbp_name', 'U2AF2').strip()
        cell_line = data.get('cell_line', 'HepG2').strip()
        model_path = data.get('model_path')
        
        # 验证必需参数
        if not sequence:
            return jsonify({
                "success": False,
                "error": "RNA序列不能为空"
            }), 400
        
        # 验证RBP名称
        supported_rbps = reformer_wrapper.get_model_info().get('supported_rbps', [])
        if rbp_name not in supported_rbps:
            return jsonify({
                "success": False,
                "error": f"不支持的RBP名称: {rbp_name}。支持的RBP: {', '.join(supported_rbps)}"
            }), 400
        
        # 验证细胞系（简化处理，具体组合验证由前端处理）
        # 这里只验证基本格式，避免无效组合的传递
        
        # 进行预测
        result = reformer_wrapper.predict_binding_affinity(
            sequence=sequence,
            rbp_name=rbp_name,
            cell_line=cell_line,
            model_path=model_path
        )
        
        return jsonify(result)
    
    except Exception as e:
        logger.error(f"Reformer预测失败: {str(e)}")
        return jsonify({
            "success": False,
            "error": f"预测过程中出现错误: {str(e)}"
        }), 500

@reformer_bp.route('/status', methods=['GET'])
def get_model_status():
    """获取模型状态"""
    try:
        is_available = reformer_wrapper.is_available()
        return jsonify({
            "success": True,
            "available": is_available,
            "model_name": "Reformer",
            "model_type": "Interaction Prediction"
        })
    except Exception as e:
        logger.error(f"获取Reformer模型状态失败: {str(e)}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@reformer_bp.route('/supported-rbps', methods=['GET'])
def get_supported_rbps():
    """获取支持的RBP列表"""
    try:
        info = reformer_wrapper.get_model_info()
        return jsonify({
            "success": True,
            "rbps": info.get('supported_rbps', []),
            "cell_lines": info.get('supported_cell_lines', [])
        })
    except Exception as e:
        logger.error(f"获取支持的RBP列表失败: {str(e)}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500
