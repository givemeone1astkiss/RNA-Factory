"""
RNAFlow API Routes
"""

from flask import Blueprint, request, jsonify
import logging
from app.utils.wrappers.rnaflow_wrapper import RNAFlowWrapper
from app.utils.input import validate_protein_sequence

logger = logging.getLogger(__name__)

rnaflow_bp = Blueprint("rnaflow", __name__, url_prefix='/api/rnaflow')

# Global wrapper instance
_rnaflow_wrapper = None

def get_rnaflow_wrapper():
    """Get or create RNAFlow wrapper instance"""
    global _rnaflow_wrapper
    if _rnaflow_wrapper is None:
        _rnaflow_wrapper = RNAFlowWrapper()
    return _rnaflow_wrapper

@rnaflow_bp.route('/design', methods=['POST'])
def design_rna():
    """Design RNA sequences and structures for protein binding"""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({
                "success": False,
                "error": "No JSON data provided"
            }), 400
        
        # Validate required fields
        required_fields = ['protein_sequence', 'rna_length']
        for field in required_fields:
            if field not in data:
                return jsonify({
                    "success": False,
                    "error": f"Missing required field: {field}"
                }), 400
        
        protein_sequence = data['protein_sequence'].strip().upper()
        rna_length = data.get('rna_length', 20)
        num_samples = data.get('num_samples', 1)
        protein_coordinates = data.get('protein_coordinates', [])
        
        # Validate protein sequence
        if not validate_protein_sequence(protein_sequence):
            return jsonify({
                "success": False,
                "error": "Invalid protein sequence. Only standard amino acid letters (A-Z) are allowed."
            }), 400
        
        # Validate RNA length
        if not isinstance(rna_length, int) or rna_length < 5 or rna_length > 200:
            return jsonify({
                "success": False,
                "error": "RNA length must be an integer between 5 and 200"
            }), 400
        
        # Validate number of samples
        if not isinstance(num_samples, int) or num_samples < 1 or num_samples > 10:
            return jsonify({
                "success": False,
                "error": "Number of samples must be an integer between 1 and 10"
            }), 400
        
        logger.info(f"RNAFlow design request: protein_length={len(protein_sequence)}, rna_length={rna_length}, num_samples={num_samples}")
        
        # Run design
        wrapper = get_rnaflow_wrapper()
        result = wrapper.design_rna(
            protein_sequence=protein_sequence,
            protein_coordinates=protein_coordinates,
            rna_length=rna_length,
            num_samples=num_samples
        )
        
        if result.get("success", False):
            return jsonify(result)
        else:
            return jsonify({
                "success": False,
                "error": result.get("error", "RNAFlow design failed")
            }), 500
            
    except Exception as e:
        logger.error(f"RNAFlow design error: {e}")
        return jsonify({
            "success": False,
            "error": f"Internal server error: {str(e)}"
        }), 500

@rnaflow_bp.route('/status', methods=['GET'])
def get_status():
    """Get RNAFlow model status"""
    try:
        wrapper = get_rnaflow_wrapper()
        info = wrapper.get_model_info()
        
        # Check if environment is properly set up
        env_status = wrapper.setup_environment()
        
        return jsonify({
            "success": True,
            "model_info": info,
            "environment_ready": env_status,
            "status": "ready" if env_status else "environment_not_ready"
        })
        
    except Exception as e:
        logger.error(f"Failed to get RNAFlow status: {e}")
        return jsonify({
            "success": False,
            "error": f"Failed to get status: {str(e)}"
        }), 500

@rnaflow_bp.route('/info', methods=['GET'])
def get_model_info():
    """Get RNAFlow model information"""
    try:
        wrapper = get_rnaflow_wrapper()
        info = wrapper.get_model_info()
        
        return jsonify({
            "success": True,
            "model_info": info
        })
        
    except Exception as e:
        logger.error(f"Failed to get RNAFlow model info: {e}")
        return jsonify({
            "success": False,
            "error": f"Failed to get model info: {str(e)}"
        }), 500

