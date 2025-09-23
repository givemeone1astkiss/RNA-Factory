"""
RiboDiffusion API Routes
"""

from flask import Blueprint, request, jsonify
import logging
import os
from app.utils.wrappers.ribodiffusion_wrapper import RiboDiffusionWrapper
from app.utils.input import validate_pdb_file

logger = logging.getLogger(__name__)

ribodiffusion_bp = Blueprint("ribodiffusion", __name__, url_prefix='/api/ribodiffusion')

# Global wrapper instance
_ribodiffusion_wrapper = None

def get_ribodiffusion_wrapper():
    """Get or create RiboDiffusion wrapper instance"""
    global _ribodiffusion_wrapper
    if _ribodiffusion_wrapper is None:
        _ribodiffusion_wrapper = RiboDiffusionWrapper()
    return _ribodiffusion_wrapper

@ribodiffusion_bp.route('/inverse_fold', methods=['POST'])
def inverse_fold():
    """Perform RNA inverse folding from PDB structure"""
    try:
        # Check if request contains file upload
        if 'pdb_file' in request.files:
            # Handle file upload
            pdb_file_obj = request.files['pdb_file']
            if not pdb_file_obj or pdb_file_obj.filename == '':
                return jsonify({
                    "success": False,
                    "error": "No PDB file provided"
                }), 400
            
            # Save uploaded file temporarily
            import tempfile
            temp_dir = tempfile.mkdtemp()
            pdb_file = os.path.join(temp_dir, pdb_file_obj.filename)
            pdb_file_obj.save(pdb_file)
            
            # Get parameters from form data
            num_samples = int(request.form.get('num_samples', 1))
            sampling_steps = int(request.form.get('sampling_steps', 50))
            cond_scale = float(request.form.get('cond_scale', -1.0))
            dynamic_threshold = True  # Always set to True
        else:
            # Handle JSON data
            data = request.get_json()
            
            if not data:
                return jsonify({
                    "success": False,
                    "error": "No JSON data provided"
                }), 400
            
            # Validate required fields
            if 'pdb_file' not in data:
                return jsonify({
                    "success": False,
                    "error": "Missing required field: pdb_file"
                }), 400
            
            pdb_file = data['pdb_file']
            num_samples = data.get('num_samples', 1)
            sampling_steps = data.get('sampling_steps', 50)
            cond_scale = data.get('cond_scale', -1.0)
            dynamic_threshold = True  # Always set to True
            
            # Validate PDB file
            if not os.path.exists(pdb_file):
                return jsonify({
                    "success": False,
                    "error": f"PDB file not found: {pdb_file}"
                }), 400
        
        # Validate parameters
        if not isinstance(num_samples, int) or num_samples < 1 or num_samples > 10:
            return jsonify({
                "success": False,
                "error": "num_samples must be an integer between 1 and 10"
            }), 400
        
        if not isinstance(sampling_steps, int) or sampling_steps < 10 or sampling_steps > 1000:
            return jsonify({
                "success": False,
                "error": "sampling_steps must be an integer between 10 and 1000"
            }), 400
        
        if not isinstance(cond_scale, (int, float)) or cond_scale < -1.0 or cond_scale > 2.0:
            return jsonify({
                "success": False,
                "error": "cond_scale must be a number between -1.0 and 2.0"
            }), 400
        
        # Get wrapper and run inference
        wrapper = get_ribodiffusion_wrapper()
        result = wrapper.inverse_fold(
            pdb_file=pdb_file,
            num_samples=num_samples,
            sampling_steps=sampling_steps,
            cond_scale=cond_scale,
            dynamic_threshold=dynamic_threshold
        )
        
        if result["success"]:
            response_data = {
                "success": True,
                "data": {
                    "sequences": result["sequences"],
                    "recovery_rate": result["recovery_rate"],
                    "num_samples": result["num_samples"],
                    "sampling_steps": result["sampling_steps"],
                    "cond_scale": result["cond_scale"],
                    "dynamic_threshold": result["dynamic_threshold"]
                }
            }
            
            # Clean up temporary file if it was uploaded
            if 'pdb_file' in request.files and 'temp_dir' in locals():
                try:
                    import shutil
                    shutil.rmtree(temp_dir)
                except Exception as cleanup_error:
                    logger.warning(f"Failed to cleanup temporary directory: {cleanup_error}")
            
            return jsonify(response_data)
        else:
            # Clean up temporary file if it was uploaded
            if 'pdb_file' in request.files and 'temp_dir' in locals():
                try:
                    import shutil
                    shutil.rmtree(temp_dir)
                except Exception as cleanup_error:
                    logger.warning(f"Failed to cleanup temporary directory: {cleanup_error}")
            
            return jsonify({
                "success": False,
                "error": result["error"]
            }), 500
            
    except Exception as e:
        # Clean up temporary file if it was uploaded
        if 'pdb_file' in request.files and 'temp_dir' in locals():
            try:
                import shutil
                shutil.rmtree(temp_dir)
            except Exception as cleanup_error:
                logger.warning(f"Failed to cleanup temporary directory: {cleanup_error}")
        
        logger.error(f"RiboDiffusion inverse fold error: {e}")
        return jsonify({
            "success": False,
            "error": f"Internal server error: {str(e)}"
        }), 500

@ribodiffusion_bp.route('/info', methods=['GET'])
def get_model_info():
    """Get RiboDiffusion model information"""
    try:
        wrapper = get_ribodiffusion_wrapper()
        info = wrapper.get_model_info()
        
        return jsonify({
            "success": True,
            "data": info
        })
        
    except Exception as e:
        logger.error(f"RiboDiffusion info error: {e}")
        return jsonify({
            "success": False,
            "error": f"Internal server error: {str(e)}"
        }), 500

@ribodiffusion_bp.route('/health', methods=['GET'])
def health_check():
    """Health check for RiboDiffusion service"""
    try:
        wrapper = get_ribodiffusion_wrapper()
        is_ready = wrapper.setup_environment()
        
        return jsonify({
            "success": True,
            "data": {
                "status": "healthy" if is_ready else "unhealthy",
                "ready": is_ready
            }
        })
        
    except Exception as e:
        logger.error(f"RiboDiffusion health check error: {e}")
        return jsonify({
            "success": False,
            "error": f"Health check failed: {str(e)}"
        }), 500
