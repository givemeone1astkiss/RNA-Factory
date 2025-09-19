from flask import Flask
from config import config
import os
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def create_app(config_name="default"):
    """Application factory function"""
    app = Flask(__name__)

    # Load configuration
    app.config.from_object(config[config_name])

    # Ensure model directory exists
    os.makedirs(app.config["MODEL_FOLDER"], exist_ok=True)

    # Register blueprints
    from app.api.copilot_routes import copilot_bp
    from app.api.bpfold_routes import bpfold_bp
    from app.api.ufold_routes import ufold_bp
    from app.api.mxfold2_routes import mxfold2_bp
    from app.api.rnamigos2_routes import rnamigos2_bp
    from app.api.rnaformer_routes import rnaformer_bp
    from app.api.model_config_routes import model_config_bp

    app.register_blueprint(copilot_bp, url_prefix="/api/copilot")
    app.register_blueprint(bpfold_bp, url_prefix="/api/bpfold")
    app.register_blueprint(ufold_bp, url_prefix="/api/ufold")
    app.register_blueprint(mxfold2_bp, url_prefix="/api/mxfold2")
    app.register_blueprint(rnamigos2_bp, url_prefix="/api/rnamigos2")
    app.register_blueprint(rnaformer_bp, url_prefix="/api/rnaformer")
    app.register_blueprint(model_config_bp, url_prefix="/api")

    # Preload models
    preload_models(app)

    # Register main page route
    @app.route("/")
    def index():
        return app.send_static_file("index.html")

    @app.route("/health")
    def health():
        return {"status": "healthy", "message": "RNA-Factory is running"}

    return app


def preload_models(app):
    """Preload models in background"""
    try:
        logger.info("Starting model preloading...")

        # Configure models to preload here
        models_config = [
            {
                "id": "bpfold",
                "name": "BPFold",
                "type": "rna_structure",
                "category": "structure_prediction",
                "category_name": "Structure Prediction",
                "description": "BPFold is a deep learning model for RNA secondary structure prediction via base pair motif energy. It provides excellent generalizability on unseen RNA families.",
                "input_types": ["fasta", "text"],
                "output_types": ["secondary_structure", "base_pairs", "confidence", "energy"],
                "model_path": "utils/wrappers/bpfold_wrapper.py",
                "weights_path": "models/BPfold/model_predict",
                "input_description": "Supports FASTA file or RNA sequence text input",
                "output_description": "Outputs RNA secondary structure in multiple formats (CSV, BPSEQ, CT, DBN) with confidence scores",
                "github_url": "https://github.com/heqin-zhu/BPfold",
                "paper_url": "https://doi.org/10.1038/s41467-025-60048-1",
                "features": [
                    "Deep generalizable prediction",
                    "Base pair motif energy modeling",
                    "Canonical and non-canonical base pairs",
                    "Confidence scoring",
                    "Multiple output formats"
                ],
                "environment_required": True,
                "environment_type": "uv",
                "environment_path": "/home/huaizhi/Software/.venv_bpfold"
            },
            {
                "id": "ufold",
                "name": "UFold",
                "type": "rna_structure",
                "category": "structure_prediction",
                "category_name": "Structure Prediction",
                "description": "UFold is a deep learning-based method for RNA secondary structure prediction using image-like sequence representation and Fully Convolutional Networks (FCNs).",
                "input_types": ["fasta", "text"],
                "output_types": ["secondary_structure", "ct_format", "bpseq_format", "structure_figure"],
                "model_path": "utils/wrappers/ufold_wrapper.py",
                "weights_path": "models/UFold",
                "input_description": "Supports FASTA file or RNA sequence text input",
                "output_description": "Outputs RNA secondary structure in CT and BPSEQ formats with structure visualization",
                "github_url": "https://github.com/uci-cbcl/UFold",
                "paper_url": "https://doi.org/10.1093/nar/gkab1074",
                "features": [
                    "Deep learning-based prediction",
                    "Image-like sequence representation",
                    "Fully Convolutional Networks (FCNs)",
                    "Fast inference (~160ms per sequence)",
                    "High accuracy improvement",
                    "Support for sequences up to 1600bp"
                ],
                "environment_required": True,
                "environment_type": "uv",
                "environment_path": "/home/huaizhi/Software/.venv_ufold"
            },
            {
                "id": "mxfold2",
                "name": "MXFold2",
                "type": "rna_structure",
                "category": "structure_prediction",
                "category_name": "Structure Prediction",
                "description": "MXFold2 is a deep learning-based method for RNA secondary structure prediction using thermodynamic integration.",
                "input_types": ["fasta", "text"],
                "output_types": ["secondary_structure", "dot_bracket", "energy"],
                "model_path": "utils/wrappers/mxfold2_wrapper.py",
                "weights_path": "models/mxfold2",
                "input_description": "Supports FASTA file or RNA sequence text input",
                "output_description": "Outputs RNA secondary structure in dot-bracket notation with energy values",
                "github_url": "https://github.com/mxfold/mxfold2",
                "paper_url": "https://doi.org/10.1038/s41467-021-21194-4",
                "web_server": "http://www.dna.bio.keio.ac.jp/mxfold2/",
                "features": [
                    "Deep learning-based prediction",
                    "Thermodynamic integration",
                    "Fast prediction",
                    "High accuracy",
                    "Support for long sequences"
                ],
                "environment_required": True,
                "environment_type": "uv",
                "environment_path": "/home/huaizhi/Software/.venv_mxfold2"
            },
            {
                "id": "rnamigos2",
                "name": "RNAmigos2",
                "type": "rna_interaction",
                "category": "interaction_prediction",
                "category_name": "Interaction Prediction",
                "description": "RNAmigos2 is a virtual screening tool for RNA-ligand interaction prediction using deep graph learning. It ranks chemical compounds based on their binding potential to RNA targets.",
                "input_types": ["mmcif", "smiles"],
                "output_types": ["interaction_scores", "binding_affinity"],
                "model_path": "utils/wrappers/rnamigos2_wrapper.py",
                "weights_path": "models/rnamigos2",
                "input_description": "Requires mmCIF structure file, binding site residues, and SMILES strings of ligands",
                "output_description": "Outputs interaction scores (0-1) for each ligand, with higher scores indicating better binding potential",
                "github_url": "https://github.com/cgoliver/rnamigos2",
                "paper_url": "https://www.nature.com/articles/s41467-025-57852-0",
                "features": [
                    "Deep graph learning",
                    "Virtual screening",
                    "Fast inference (~10 seconds)",
                    "High enrichment factors",
                    "Structure-based prediction",
                    "Multiple ligand support"
                ],
                "environment_required": True,
                "environment_type": "uv",
                "environment_path": "/home/huaizhi/Software/.venv_rnamigos2"
            },
            {
                "id": "rnaformer",
                "name": "RNAformer",
                "type": "rna_structure",
                "category": "structure_prediction",
                "category_name": "Structure Prediction",
                "description": "RNAformer is a simple yet effective deep learning model for RNA secondary structure prediction using a two-dimensional latent space, axial attention, and recycling mechanisms.",
                "input_types": ["fasta", "text"],
                "output_types": ["secondary_structure", "dot_bracket", "ct_format"],
                "model_path": "utils/wrappers/rnaformer_wrapper.py",
                "weights_path": "models/RNAformer",
                "input_description": "Supports FASTA file or RNA sequence text input",
                "output_description": "Outputs RNA secondary structure in dot-bracket notation and CT format",
                "github_url": "https://github.com/automl/RNAformer",
                "paper_url": "https://arxiv.org/abs/2307.10073",
                "features": [
                    "Deep learning-based prediction",
                    "Two-dimensional latent space",
                    "Axial attention mechanism",
                    "Recycling in latent space",
                    "High accuracy on benchmarks",
                    "Single model approach"
                ],
                "environment_required": True,
                "environment_type": "uv",
                "environment_path": "/home/huaizhi/Software/.venv_rnaformer"
            }
        ]

        # Store model configuration in application context
        app.config["PREDEFINED_MODELS"] = models_config

        logger.info(f"Successfully preloaded {len(models_config)} model configurations")

    except Exception as e:
        logger.error(f"Model preloading failed: {e}")
        # Even if preloading fails, the application can still start
        app.config["PREDEFINED_MODELS"] = []
