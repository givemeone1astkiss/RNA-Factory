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

    # Ensure upload directory exists
    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)
    os.makedirs(app.config["MODEL_FOLDER"], exist_ok=True)

    # Register blueprints
    from app.api.copilot_routes import copilot_bp
    from app.api.bpfold_routes import bpfold_bp
    from app.api.ufold_routes import ufold_bp
    from app.api.mxfold2_routes import mxfold2_bp
    from app.api.model_config_routes import model_config_bp
    from app.api.zhmolgraph_routes import zhmolgraph_bp

    app.register_blueprint(copilot_bp, url_prefix="/api/copilot")
    app.register_blueprint(bpfold_bp, url_prefix="/api/bpfold")
    app.register_blueprint(ufold_bp, url_prefix="/api/ufold")
    app.register_blueprint(mxfold2_bp, url_prefix="/api/mxfold2")
    app.register_blueprint(zhmolgraph_bp, url_prefix="/api/zhmolgraph")
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
                "category_name": "2nd Structure Prediction",
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
                "category_name": "2nd Structure Prediction",
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
                "category_name": "2nd Structure Prediction",
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
                "id": "zhmolgraph",
                "name": "ZHMolGraph",
                "type": "rna_protein_interaction",
                "category": "interaction_prediction",
                "category_name": "RNA-Protein Interaction",
                "description": "ZHMolGraph is an advanced pipeline that integrates graph neural network sampling strategy and unsupervised large language models to enhance binding predictions for novel RNAs and proteins.",
                "input_types": ["fasta", "text"],
                "output_types": ["interaction_probability", "prediction", "confidence"],
                "model_path": "utils/wrappers/zhmolgraph_wrapper.py",
                "weights_path": "models/ZHMolGraph",
                "input_description": "Supports FASTA file or text input for both RNA and protein sequences",
                "output_description": "Outputs RNA-Protein interaction probability, prediction confidence, and binding strength",
                "github_url": "https://github.com/ZHMolGraph/ZHMolGraph",
                "paper_url": "https://doi.org/10.1038/s41467-025-59389-8",
                "features": [
                    "Graph Neural Network based prediction",
                    "RNA-Protein interaction prediction",
                    "High accuracy prediction",
                    "Support for novel sequences",
                    "Integration with large language models"
                ],
                "environment_required": True,
                "environment_type": "uv",
                "environment_path": "/home/huaizhi/Software/.venv_zhmolgraph"
            },
            {
                "id": "deeprpi",
                "name": "DeepRPI",
                "type": "rna_protein_interaction",
                "category": "interaction_prediction",
                "category_name": "Interaction Prediction",
                "description": "DeepRPI is a deep learning model specifically designed for predicting RNA-protein interactions.",
                "input_types": ["fasta", "text"],
                "output_types": ["binding_affinity", "binding_sites", "interaction_score"],
                "model_path": "models/deep_rpi.py",
                "weights_path": "models/deep_rpi.pth",
                "input_description": "Input RNA and protein FASTA files or sequence text separately",
                "output_description": "Output binding affinity, binding sites and interaction scores",
            },
            {
                "id": "rnampnn",
                "name": "RNA-MPNN",
                "type": "rna_structure",
                "category": "sequence_design",
                "category_name": "Sequence Design",
                "description": "RNA-MPNN is a graph neural network-based RNA structure prediction model that can learn from 3D structural information in PDB files.",
                "input_types": ["pdb"],
                "output_types": ["3d_structure", "coordinates", "confidence"],
                "model_path": "models/rna_mpnn.py",
                "weights_path": "models/rna_mpnn.pth",
                "input_description": "Input PDB format 3D structure file",
                "output_description": "Output predicted 3D structure, coordinates and confidence",
                "github_url": "https://github.com/givemeone1astkiss/RNA-MPNN",
                "paper_url": "https://github.com/givemeone1astkiss/RNA-MPNN",
                "architecture_image": "static/images/rnampnn.jpg",
            },
            {
                "id": "rdesign",
                "name": "RDesign",
                "type": "rna_design",
                "category": "sequence_design",
                "category_name": "Sequence Design",
                "description": "RDesign is an AI-powered RNA sequence design tool that can generate RNA sequences with specific structural and functional properties.",
                "input_types": ["fasta", "text", "pdb"],
                "output_types": ["designed_sequence", "structure_prediction", "confidence"],
                "model_path": "models/rdesign.py",
                "weights_path": "models/rdesign.pth",
                "input_description": "Supports FASTA, text, or PDB format input",
                "output_description": "Outputs designed RNA sequences with structural predictions",
            },
            {
                "id": "gardn",
                "name": "GARDN",
                "type": "rna_generation",
                "category": "sequence_generation",
                "category_name": "Sequence Generation",
                "description": "GARDN (Generative AI for RNA Design and Navigation) is a generative model that can create novel RNA sequences with desired properties.",
                "input_types": ["text", "fasta"],
                "output_types": ["generated_sequence", "property_prediction", "diversity_score"],
                "model_path": "models/gardn.py",
                "weights_path": "models/gardn.pth",
                "input_description": "Supports text prompts or FASTA file input",
                "output_description": "Outputs generated RNA sequences with property predictions",
            },
        ]

        # Store model configuration in application context
        app.config["PREDEFINED_MODELS"] = models_config

        logger.info(f"Successfully preloaded {len(models_config)} model configurations")

    except Exception as e:
        logger.error(f"Model preloading failed: {e}")
        # Even if preloading fails, the application can still start
        app.config["PREDEFINED_MODELS"] = []
