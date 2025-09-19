"""
MXFold2 API Routes
"""

from flask import Blueprint, request, jsonify, send_file
import tempfile
import logging
import os
from app.utils.wrappers.mxfold2_wrapper import MXFold2Wrapper
from app.utils.input import validate_rna_sequence
from app.utils.output import generate_ct_content, generate_multiple_ct_files, create_ct_zip_file, cleanup_temp_files

logger = logging.getLogger(__name__)

mxfold2_bp = Blueprint("mxfold2", __name__, url_prefix='/api/mxfold2')

# Global wrapper instance
_mxfold2_wrapper = None

def get_mxfold2_wrapper():
    """Get or create MXFold2 wrapper instance"""
    global _mxfold2_wrapper
    if _mxfold2_wrapper is None:
        _mxfold2_wrapper = MXFold2Wrapper()
    return _mxfold2_wrapper

@mxfold2_bp.route('/predict', methods=['POST'])
def predict_sequences():
    """Predict RNA secondary structures from sequences"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({
                "success": False,
                "error": "No data provided"
            }), 400
        
        sequences = data.get('sequences', [])
        if not sequences:
            return jsonify({
                "success": False,
                "error": "No sequences provided"
            }), 400
        
        # Validate and convert sequences to uppercase
        validated_sequences = []
        for i, seq in enumerate(sequences):
            try:
                # Convert to uppercase before validation
                seq_upper = seq.upper()
                if validate_rna_sequence(seq_upper):
                    validated_sequences.append(seq_upper)
                else:
                    return jsonify({
                        "success": False, 
                        "error": f"Invalid sequence at index {i}: contains non-RNA characters"
                    }), 400
            except Exception as e:
                return jsonify({
                    "success": False, 
                    "error": f"Invalid sequence at index {i}: {str(e)}"
                }), 400
        
        if not validated_sequences:
            return jsonify({
                "success": False,
                "error": "No valid RNA sequences provided"
            }), 400
        
        # Run prediction
        wrapper = get_mxfold2_wrapper()
        result = wrapper.predict(validated_sequences)
        
        if result["success"]:
            return jsonify({
                "success": True,
                "results": result["results"],
                "model": "MXFold2",
                "stdout": result.get("stdout", ""),
                "stderr": result.get("stderr", "")
            })
        else:
            return jsonify({
                "success": False,
                "error": result["error"]
            }), 500
            
    except Exception as e:
        logger.error(f"MXFold2 prediction error: {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@mxfold2_bp.route('/predict/file', methods=['POST'])
def predict_file():
    """Predict RNA secondary structures from uploaded file"""
    try:
        if 'file' not in request.files:
            return jsonify({
                "success": False,
                "error": "No file provided"
            }), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({
                "success": False,
                "error": "No file selected"
            }), 400
        
        # Read and parse file content
        content = file.read().decode('utf-8')
        
        # Parse FASTA format
        sequences = []
        current_sequence = ""
        
        for line in content.split('\n'):
            line = line.strip()
            if line.startswith('>'):
                if current_sequence:
                    sequences.append(current_sequence)
                    current_sequence = ""
            elif line and not line.startswith('>'):
                current_sequence += line
        
        if current_sequence:
            sequences.append(current_sequence)
        
        if not sequences:
            return jsonify({
                "success": False,
                "error": "No sequences found in file"
            }), 400
        
        # Validate and convert sequences to uppercase
        validated_sequences = []
        for i, seq in enumerate(sequences):
            try:
                # Convert to uppercase before validation
                seq_upper = seq.upper()
                if validate_rna_sequence(seq_upper):
                    validated_sequences.append(seq_upper)
                else:
                    return jsonify({
                        "success": False, 
                        "error": f"Invalid sequence at index {i}: contains non-RNA characters"
                    }), 400
            except Exception as e:
                return jsonify({
                    "success": False, 
                    "error": f"Invalid sequence at index {i}: {str(e)}"
                }), 400
        
        if not validated_sequences:
            return jsonify({
                "success": False,
                "error": "No valid RNA sequences provided"
            }), 400
        
        # Run prediction
        wrapper = get_mxfold2_wrapper()
        result = wrapper.predict(validated_sequences)
        
        if result["success"]:
            return jsonify({
                "success": True,
                "results": result["results"],
                "model": "MXFold2",
                "stdout": result.get("stdout", ""),
                "stderr": result.get("stderr", "")
            })
        else:
            return jsonify({
                "success": False,
                "error": result["error"]
            }), 500
            
    except Exception as e:
        logger.error(f"MXFold2 file prediction error: {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@mxfold2_bp.route('/download/<format>', methods=['POST'])
def download_results(format):
    """Download prediction results in specified format"""
    try:
        data = request.get_json()
        if not data or 'results' not in data:
            return jsonify({
                "success": False,
                "error": "No results provided"
            }), 400
        
        results = data['results']
        output_format = data.get('format', 'ct')
        
        # Create temporary file with results
        with tempfile.NamedTemporaryFile(mode='w', suffix=f'.{output_format}', delete=False) as temp_file:
            if output_format == 'ct':
                for i, result in enumerate(results):
                    temp_file.write(f">sequence_{i+1}\n")
                    temp_file.write(result['data'])
                    temp_file.write('\n')
            else:
                # Default to dot-bracket format
                for i, result in enumerate(results):
                    temp_file.write(f">sequence_{i+1}\n")
                    temp_file.write(result['data'])
                    temp_file.write('\n')
            
            temp_file_path = temp_file.name
        
        return send_file(
            temp_file_path,
            as_attachment=True,
            download_name=f'mxfold2_results.{output_format}',
            mimetype='text/plain'
        )
        
    except Exception as e:
        logger.error(f"Failed to download results: {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@mxfold2_bp.route('/info', methods=['GET'])
def get_model_info():
    """Get MXFold2 model information"""
    try:
        wrapper = get_mxfold2_wrapper()
        info = wrapper.get_model_info()
        
        return jsonify({
            "success": True,
            "model_info": info
        })
        
    except Exception as e:
        logger.error(f"Failed to get MXFold2 info: {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@mxfold2_bp.route('/status', methods=['GET'])
def get_status():
    """Get MXFold2 service status"""
    try:
        wrapper = get_mxfold2_wrapper()
        info = wrapper.get_model_info()
        
        return jsonify({
            "success": True,
            "status": "available",
            "model_info": info
        })
        
    except Exception as e:
        logger.error(f"Failed to get MXFold2 status: {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@mxfold2_bp.route('/download_ct', methods=['POST'])
def download_ct_files():
    """Download CT files for MXFold2 results"""
    try:
        data = request.get_json()
        if not data or 'results' not in data:
            return jsonify({"success": False, "error": "No results data provided"}), 400
        
        results = data['results']
        if not results:
            return jsonify({"success": False, "error": "No results to download"}), 400
        
        # Convert MXFold2 results to standard format for CT generation
        ct_results = []
        for i, result in enumerate(results):
            sequence = result.get('sequence', '')
            dot_bracket = result.get('data', '')  # MXFold2 uses 'data' field for dot-bracket
            
            if sequence and dot_bracket:
                ct_results.append({
                    'sequence': sequence,
                    'dot_bracket': dot_bracket,
                    'length': len(sequence)
                })
        
        if not ct_results:
            return jsonify({"success": False, "error": "No valid sequences found for CT generation"}), 400
        
        # Generate CT files
        ct_files = generate_multiple_ct_files(ct_results, "mxfold2_structures")
        
        if not ct_files:
            return jsonify({"success": False, "error": "Failed to generate CT files"}), 500
        
        try:
            # Create ZIP file if multiple sequences
            if len(ct_files) > 1:
                zip_path = create_ct_zip_file(ct_files, "mxfold2_structures.zip")
                return send_file(
                    zip_path,
                    as_attachment=True,
                    download_name="mxfold2_structures.zip",
                    mimetype="application/zip"
                )
            else:
                # Send single CT file
                return send_file(
                    ct_files[0],
                    as_attachment=True,
                    download_name=os.path.basename(ct_files[0]),
                    mimetype="text/plain"
                )
        finally:
            # Clean up temporary files after sending
            cleanup_temp_files(ct_files)
            
    except Exception as e:
        logger.error(f"CT file download error: {str(e)}")
        return jsonify({
            "success": False,
            "error": f"Download failed: {str(e)}"
        }), 500

@mxfold2_bp.route('/generate_ct', methods=['POST'])
def generate_single_ct():
    """Generate CT content for a single sequence"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({"success": False, "error": "No data provided"}), 400
        
        sequence = data.get('sequence', '')
        dot_bracket = data.get('dot_bracket', '')
        
        if not sequence or not dot_bracket:
            return jsonify({"success": False, "error": "Sequence and dot_bracket are required"}), 400
        
        if len(sequence) != len(dot_bracket):
            return jsonify({"success": False, "error": "Sequence and dot_bracket lengths must match"}), 400
        
        # Generate CT content with sequence name
        ct_content = generate_ct_content(sequence, dot_bracket, "sequence 1")
        
        return jsonify({
            "success": True,
            "ct_content": ct_content,
            "filename": f"mxfold2_structure_{len(sequence)}bp.ct"
        })
        
    except Exception as e:
        logger.error(f"CT generation error: {str(e)}")
        return jsonify({
            "success": False,
            "error": f"CT generation failed: {str(e)}"
        }), 500
