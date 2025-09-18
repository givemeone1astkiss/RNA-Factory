"""
BPFold API Routes
API endpoints for BPFold RNA secondary structure prediction
"""

import logging
from flask import Blueprint, request, jsonify, send_file
import tempfile
import os
from pathlib import Path

from app.utils.wrappers import BPFoldWrapper

logger = logging.getLogger(__name__)

# Create blueprint
bpfold_bp = Blueprint('bpfold', __name__, url_prefix='/api/bpfold')

# Global BPFold wrapper instance
bpfold_wrapper = None

def get_bpfold_wrapper():
    """Get or initialize BPFold wrapper"""
    global bpfold_wrapper
    if bpfold_wrapper is None:
        bpfold_wrapper = BPFoldWrapper(
            model_path="/home/huaizhi/Software/models/BPfold/model_predict",
            environment_path="/home/huaizhi/Software/.venv_bpfold"
        )
    return bpfold_wrapper

@bpfold_bp.route('/info', methods=['GET'])
def get_model_info():
    """Get BPFold model information"""
    try:
        wrapper = get_bpfold_wrapper()
        info = wrapper.get_model_info()
        return jsonify({
            "success": True,
            "model_info": info
        })
    except Exception as e:
        logger.error(f"Failed to get BPFold model info: {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@bpfold_bp.route('/predict', methods=['POST'])
def predict_structures():
    """Predict RNA secondary structures using BPFold"""
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
        
        # Validate sequences
        valid_sequences = []
        for seq in sequences:
            if isinstance(seq, str) and seq.strip():
                # Basic RNA sequence validation
                seq = seq.strip().upper()
                if all(c in 'AUGC' for c in seq):
                    valid_sequences.append(seq)
                else:
                    logger.warning(f"Invalid RNA sequence: {seq}")
        
        if not valid_sequences:
            return jsonify({
                "success": False,
                "error": "No valid RNA sequences provided"
            }), 400
        
        # Get parameters
        output_format = data.get('output_format', 'ct')
        ignore_nc = data.get('ignore_nc', False)
        
        # Validate output format
        valid_formats = ['csv', 'bpseq', 'ct', 'dbn']
        if output_format not in valid_formats:
            return jsonify({
                "success": False,
                "error": f"Invalid output format. Must be one of: {valid_formats}"
            }), 400
        
        # Run prediction
        wrapper = get_bpfold_wrapper()
        result = wrapper.predict(
            sequences=valid_sequences,
            output_format=output_format,
            ignore_nc=ignore_nc
        )
        
        if not result['success']:
            return jsonify(result), 500
        
        return jsonify({
            "success": True,
            "results": result['results'],
            "num_sequences": len(valid_sequences),
            "output_format": output_format,
            "ignore_nc": ignore_nc
        })
        
    except Exception as e:
        logger.error(f"BPFold prediction failed: {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@bpfold_bp.route('/predict/file', methods=['POST'])
def predict_from_file():
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
        
        # Get parameters
        output_format = request.form.get('output_format', 'ct')
        ignore_nc = request.form.get('ignore_nc', 'false').lower() == 'true'
        
        # Validate output format
        valid_formats = ['csv', 'bpseq', 'ct', 'dbn']
        if output_format not in valid_formats:
            return jsonify({
                "success": False,
                "error": f"Invalid output format. Must be one of: {valid_formats}"
            }), 400
        
        # Save uploaded file temporarily
        with tempfile.NamedTemporaryFile(mode='w+b', suffix='.fasta', delete=False) as temp_file:
            file.save(temp_file.name)
            temp_file_path = temp_file.name
        
        try:
            # Read sequences from file
            sequences = []
            with open(temp_file_path, 'r') as f:
                current_seq = ""
                for line in f:
                    line = line.strip()
                    if line.startswith('>'):
                        if current_seq:
                            sequences.append(current_seq)
                        current_seq = ""
                    else:
                        current_seq += line
                if current_seq:
                    sequences.append(current_seq)
            
            if not sequences:
                return jsonify({
                    "success": False,
                    "error": "No valid sequences found in file"
                }), 400
            
            # Run prediction
            wrapper = get_bpfold_wrapper()
            result = wrapper.predict(
                sequences=sequences,
                output_format=output_format,
                ignore_nc=ignore_nc
            )
            
            if not result['success']:
                return jsonify(result), 500
            
            return jsonify({
                "success": True,
                "results": result['results'],
                "num_sequences": len(sequences),
                "output_format": output_format,
                "ignore_nc": ignore_nc
            })
            
        finally:
            # Cleanup temporary file
            if os.path.exists(temp_file_path):
                os.unlink(temp_file_path)
        
    except Exception as e:
        logger.error(f"BPFold file prediction failed: {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@bpfold_bp.route('/download/<format>', methods=['POST'])
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
            if output_format == 'csv':
                for i, result in enumerate(results):
                    temp_file.write(f"Sequence {i+1}: {result['sequence']}\n")
                    temp_file.write(result['data'])
                    temp_file.write('\n\n')
            
            elif output_format in ['bpseq', 'ct', 'dbn']:
                for i, result in enumerate(results):
                    temp_file.write(f">sequence_{i+1}\n")
                    temp_file.write(result['data'])
                    temp_file.write('\n')
            
            temp_file_path = temp_file.name
        
        return send_file(
            temp_file_path,
            as_attachment=True,
            download_name=f'bpfold_results.{output_format}',
            mimetype='text/plain'
        )
        
    except Exception as e:
        logger.error(f"Failed to download results: {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@bpfold_bp.route('/status', methods=['GET'])
def get_status():
    """Get BPFold service status"""
    try:
        wrapper = get_bpfold_wrapper()
        info = wrapper.get_model_info()
        
        return jsonify({
            "success": True,
            "status": "ready" if (info['available'] and info['environment_ready']) else "not_ready",
            "model_available": info['available'],
            "environment_ready": info['environment_ready'],
            "model_path": info['model_path'],
            "environment_path": info['environment_path']
        })
        
    except Exception as e:
        logger.error(f"Failed to get BPFold status: {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@bpfold_bp.route('/setup', methods=['POST'])
def setup_model():
    """Setup BPFold model and environment"""
    try:
        wrapper = get_bpfold_wrapper()
        
        # Download model if needed
        if not wrapper.model_path or not os.path.exists(wrapper.model_path):
            if not wrapper._download_model():
                return jsonify({
                    "success": False,
                    "error": "Failed to download BPFold model"
                }), 500
        
        # Setup environment
        if not wrapper._setup_environment():
            return jsonify({
                "success": False,
                "error": "Failed to setup BPFold environment"
            }), 500
        
        return jsonify({
            "success": True,
            "message": "BPFold model and environment setup completed"
        })
        
    except Exception as e:
        logger.error(f"Failed to setup BPFold: {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500
