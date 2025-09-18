"""
ZHMolGraph API Routes
RNA-Protein Interaction Prediction
"""

from flask import Blueprint, request, jsonify, Response
import os
import tempfile
import logging
from pathlib import Path

from app.utils.wrappers.zhmolgraph_wrapper import ZHMolGraphWrapper
from app.utils.input import (
    parse_text_input, parse_fasta_file, extract_sequences_from_fasta,
    parse_protein_text_input, parse_protein_fasta_file, extract_protein_sequences_from_fasta,
    validate_zhmolgraph_input
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

zhmolgraph_bp = Blueprint("zhmolgraph", __name__)

# Initialize wrapper
wrapper = None

def get_wrapper():
    """Get or create ZHMolGraph wrapper instance"""
    global wrapper
    if wrapper is None:
        wrapper = ZHMolGraphWrapper()
    return wrapper

@zhmolgraph_bp.route("/status", methods=["GET"])
def zhmolgraph_status():
    """Get ZHMolGraph model status"""
    try:
        wrapper = get_wrapper()
        model_info = wrapper.get_model_info()
        
        return jsonify({
            "success": True,
            "status": "available" if model_info["available"] else "unavailable",
            "model_info": model_info
        })
    except Exception as e:
        logger.error(f"Failed to get ZHMolGraph status: {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@zhmolgraph_bp.route("/predict", methods=["POST"])
def predict_interactions():
    """Predict RNA-Protein interactions from text input"""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({"success": False, "error": "No JSON data provided"}), 400
        
        rna_text = data.get("rna_sequences", "")
        protein_text = data.get("protein_sequences", "")
        
        if not rna_text or not protein_text:
            return jsonify({
                "success": False, 
                "error": "Both RNA and protein sequences are required"
            }), 400
        
        # Parse RNA sequences
        try:
            rna_sequences = parse_text_input(rna_text)
        except Exception as e:
            return jsonify({
                "success": False,
                "error": f"Invalid RNA sequences: {str(e)}"
            }), 400
        
        # Parse protein sequences
        try:
            protein_sequences = parse_protein_text_input(protein_text)
        except Exception as e:
            return jsonify({
                "success": False,
                "error": f"Invalid protein sequences: {str(e)}"
            }), 400
        
        # Validate input pairs
        try:
            rna_sequences, protein_sequences = validate_zhmolgraph_input(
                rna_sequences, protein_sequences
            )
        except Exception as e:
            return jsonify({
                "success": False,
                "error": f"Input validation failed: {str(e)}"
            }), 400
        
        # Run prediction
        wrapper = get_wrapper()
        result = wrapper.predict(rna_sequences, protein_sequences)
        
        if result["success"]:
            return jsonify({
                "success": True,
                "results": result["results"],
                "model": "ZHMolGraph",
                "input_count": len(rna_sequences)
            })
        else:
            return jsonify({
                "success": False,
                "error": result["error"]
            }), 500
            
    except Exception as e:
        logger.error(f"ZHMolGraph prediction failed: {e}")
        return jsonify({
            "success": False,
            "error": f"Prediction failed: {str(e)}"
        }), 500

@zhmolgraph_bp.route("/predict/file", methods=["POST"])
def predict_interactions_from_file():
    """Predict RNA-Protein interactions from uploaded files"""
    try:
        if 'rna_file' not in request.files or 'protein_file' not in request.files:
            return jsonify({
                "success": False, 
                "error": "Both RNA and protein files are required"
            }), 400
        
        rna_file = request.files['rna_file']
        protein_file = request.files['protein_file']
        
        if rna_file.filename == '' or protein_file.filename == '':
            return jsonify({
                "success": False, 
                "error": "No files selected"
            }), 400
        
        # Save uploaded files temporarily
        with tempfile.NamedTemporaryFile(mode='w+b', suffix='.fasta', delete=False) as rna_temp:
            rna_file.save(rna_temp.name)
            rna_temp_path = rna_temp.name
        
        with tempfile.NamedTemporaryFile(mode='w+b', suffix='.fasta', delete=False) as protein_temp:
            protein_file.save(protein_temp.name)
            protein_temp_path = protein_temp.name
        
        try:
            # Read sequences from files
            rna_sequences = extract_sequences_from_fasta(rna_temp_path)
            protein_sequences = extract_protein_sequences_from_fasta(protein_temp_path)
            
            # Validate input pairs
            rna_sequences, protein_sequences = validate_zhmolgraph_input(
                rna_sequences, protein_sequences
            )
            
            # Run prediction
            wrapper = get_wrapper()
            result = wrapper.predict(rna_sequences, protein_sequences)
            
            if result["success"]:
                return jsonify({
                    "success": True,
                    "results": result["results"],
                    "model": "ZHMolGraph",
                    "input_count": len(rna_sequences)
                })
            else:
                return jsonify({
                    "success": False,
                    "error": result["error"]
                }), 500
                
        finally:
            # Clean up temporary files
            if os.path.exists(rna_temp_path):
                os.unlink(rna_temp_path)
            if os.path.exists(protein_temp_path):
                os.unlink(protein_temp_path)
                
    except Exception as e:
        logger.error(f"ZHMolGraph file prediction failed: {e}")
        return jsonify({
            "success": False,
            "error": f"File prediction failed: {str(e)}"
        }), 500

@zhmolgraph_bp.route("/download/<format>", methods=["GET"])
def download_results(format):
    """Download prediction results in specified format"""
    try:
        # This would typically get results from session or database
        # For now, return a placeholder response
        return jsonify({
            "success": False,
            "error": "Download functionality not implemented yet"
        }), 501
        
    except Exception as e:
        logger.error(f"Download failed: {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500
