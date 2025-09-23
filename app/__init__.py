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
    from app.api.mol2aptamer_routes import mol2aptamer_bp
    from app.api.rnaflow_routes import rnaflow_bp
    from app.api.rnaframeflow_routes import rnaframeflow_bp
    from app.api.reformer_routes import reformer_bp
    from app.api.copra_routes import copra_bp
    from app.api.ribodiffusion_routes import ribodiffusion_bp
    from app.api.model_config_routes import model_config_bp

    app.register_blueprint(copilot_bp, url_prefix="/api/copilot")
    app.register_blueprint(bpfold_bp, url_prefix="/api/bpfold")
    app.register_blueprint(ufold_bp, url_prefix="/api/ufold")
    app.register_blueprint(mxfold2_bp, url_prefix="/api/mxfold2")
    app.register_blueprint(rnamigos2_bp, url_prefix="/api/rnamigos2")
    app.register_blueprint(rnaformer_bp, url_prefix="/api/rnaformer")
    app.register_blueprint(mol2aptamer_bp, url_prefix="/api/mol2aptamer")
    app.register_blueprint(rnaflow_bp, url_prefix="/api/rnaflow")
    app.register_blueprint(rnaframeflow_bp, url_prefix="/api/rnaframeflow")
    app.register_blueprint(reformer_bp, url_prefix="/api/reformer")
    app.register_blueprint(copra_bp, url_prefix="/api/copra")
    app.register_blueprint(ribodiffusion_bp, url_prefix="/api/ribodiffusion")
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
                "environment_path": "/home/huaizhi/Software/.venv_bpfold",
                "architecture_image": "/static/images/bpfold.png"
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
                "environment_path": "/home/huaizhi/Software/.venv_ufold",
                "architecture_image": "/static/images/ufold.png"
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
                "environment_path": "/home/huaizhi/Software/.venv_mxfold2",
                "architecture_image": "/static/images/mxfold2.png"
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
                "environment_path": "/home/huaizhi/Software/.venv_rnamigos2",
                "architecture_image": "/static/images/rnamigos2.png"
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
                "environment_path": "/home/huaizhi/Software/.venv_rnaformer",
                "architecture_image": "/static/images/rnaformer.png"
            },
            {
                "id": "mol2aptamer",
                "name": "Mol2Aptamer",
                "type": "rna_design",
                "category": "de_novo_design",
                "category_name": "De Novo Design",
                "description": "Mol2Aptamer is a deep learning model for de novo RNA aptamer design from small molecule SMILES strings. It generates RNA sequences that can bind to specific small molecules using transformer architecture and BPE tokenization.",
                "input_types": ["smiles"],
                "output_types": ["rna_sequences", "aptamer_candidates"],
                "model_path": "utils/wrappers/mol2aptamer_wrapper.py",
                "weights_path": "models/Mol2Aptamer",
                "input_description": "Requires SMILES string of small molecule and generation parameters",
                "output_description": "Outputs generated RNA aptamer sequences with length and ΔG information",
                "features": [
                    "De novo RNA aptamer design",
                    "Transformer architecture",
                    "BPE tokenization",
                    "Multiple sampling strategies",
                    "RNAfold integration",
                    "Customizable generation parameters"
                ],
                "environment_required": True,
                "environment_type": "uv",
                "environment_path": "/home/huaizhi/Software/.venv_mol2aptamer"
            },
            {
                "id": "rnaflow",
                "name": "RNAFlow",
                "type": "rna_design",
                "category": "de_novo_design",
                "category_name": "De Novo Design",
                "description": "RNAFlow is a flow matching model for protein-conditioned RNA sequence-structure design. It integrates an RNA inverse folding model and a pre-trained RosettaFold2NA network for generation of RNA sequences and structures.",
                "input_types": ["protein_sequence", "protein_coordinates", "rna_length"],
                "output_types": ["rna_sequences", "rna_structures"],
                "model_path": "utils/wrappers/rnaflow_wrapper.py",
                "weights_path": "models/rnaflow",
                "input_description": "Requires protein sequence, protein coordinates, and desired RNA length",
                "output_description": "Outputs designed RNA sequences and structures for protein binding",
                "github_url": "https://github.com/divnori/rnaflow",
                "paper_url": "https://arxiv.org/abs/2405.18768",
                "features": [
                    "Flow matching-based design",
                    "Protein-conditioned generation",
                    "RNA inverse folding integration",
                    "RosettaFold2NA network",
                    "Sequence and structure co-design",
                    "High-quality RNA-protein complexes"
                ],
                "environment_required": True,
                "environment_type": "uv",
                "environment_path": "/home/huaizhi/Software/.venv_rnaflow",
                "architecture_image": "/static/images/rnaflow.png"
            },
            {
                "id": "rnaframeflow",
                "name": "RNA-FrameFlow",
                "type": "rna_design",
                "category": "de_novo_design",
                "category_name": "De Novo Design",
                "description": "RNA-FrameFlow is a generative model for 3D RNA backbone structure design based on SE(3) flow matching. It generates all-atom RNA backbone structures using flow matching techniques for 3D RNA structure design.",
                "input_types": ["structure_length", "num_structures"],
                "output_types": ["rna_structures", "3d_coordinates", "pdb_files"],
                "model_path": "utils/wrappers/rnaframeflow_wrapper.py",
                "weights_path": "models/rna-backbone-design",
                "input_description": "Requires desired structure length and number of structures to generate",
                "output_description": "Outputs generated 3D RNA backbone structures in PDB format (no sequence information)",
                "github_url": "https://github.com/rish-16/rna-backbone-design",
                "paper_url": "https://arxiv.org/abs/2406.13839",
                "features": [
                    "SE(3) flow matching",
                    "3D RNA backbone design",
                    "All-atom structure generation",
                    "PDB file output",
                    "Flow matching techniques",
                    "High-quality RNA structures"
                ],
                "environment_required": True,
                "environment_type": "uv",
                "environment_path": "/home/zhangliqin/RNA-Factory/.venv_rnaframeflow",
                "architecture_image": "/static/images/rna-frameflow.png"
            },
            {
                "id": "reformer",
                "name": "Reformer",
                "type": "rna_interaction",
                "category": "interaction_prediction",
                "category_name": "Interaction Prediction",
                "description": "Reformer is a deep learning model for predicting protein-RNA binding affinity at single-base resolution using transformer architecture and cDNA sequences.",
                "input_types": ["rna_sequence", "rbp_name", "cell_line"],
                "output_types": ["binding_scores", "affinity_prediction"],
                "model_path": "utils/wrappers/reformer_wrapper.py",
                "weights_path": "models/Reformer",
                "input_description": "Requires cDNA sequence, RBP name, and cell line for binding affinity prediction",
                "output_description": "Outputs binding affinity scores at single-base resolution with statistics",
                "github_url": "https://github.com/xilinshen/Reformer",
                "paper_url": "https://www.sciencedirect.com/science/article/pii/S2666389924003222",
                "features": [
                    "Single-base resolution prediction",
                    "Transformer architecture",
                    "Multiple RBP support",
                    "Cell line specific prediction",
                    "Binding site identification",
                    "High prediction accuracy"
                ],
                "environment_required": True,
                "environment_type": "uv",
                "environment_path": "/home/zhangliqin/RNA-Factory/.venv_reformer",
                "architecture_image": "/static/images/reformer.png"
            },
            {
                "id": "copra",
                "name": "CoPRA",
                "type": "protein_rna_interaction",
                "category": "interaction_prediction",
                "category_name": "Interaction Prediction",
                "description": "CoPRA is a state-of-the-art predictor of protein-RNA binding affinity based on protein language model and RNA language model with complex structure as input. Pre-trained on PRI30k dataset and fine-tuned on PRA310.",
                "input_types": ["protein_sequence", "rna_sequence"],
                "output_types": ["binding_affinity", "confidence_score"],
                "model_path": "models/CoPRA/copra_inference.py",
                "weights_path": "models/CoPRA/weights",
                "input_description": "Requires protein sequence and RNA sequence for binding affinity prediction",
                "output_description": "Outputs protein-RNA binding affinity in kcal/mol with confidence score",
                "github_url": "https://github.com/hanrthu/CoPRA",
                "paper_url": "https://arxiv.org/abs/2409.03773",
                "features": [
                    "Protein-RNA binding affinity prediction",
                    "Cross-domain pretrained models",
                    "Complex structure integration",
                    "ESM2 protein language model",
                    "RiNALMo RNA language model",
                    "State-of-the-art performance"
                ],
                "environment_required": True,
                "environment_type": "uv",
                "environment_path": "/home/zhangliqin/RNA-Factory/.venv_copra",
                "architecture_image": "/static/images/copra.png"
            },
            {
                "id": "ribodiffusion",
                "name": "RiboDiffusion",
                "type": "rna_design",
                "category": "de_novo_design",
                "category_name": "De Novo Design",
                "description": "RiboDiffusion is a generative diffusion model for tertiary structure-based RNA inverse folding. It generates RNA sequences that can fold into specific 3D structures using diffusion-based generation.",
                "input_types": ["pdb"],
                "output_types": ["rna_sequences", "fasta_files"],
                "model_path": "utils/wrappers/ribodiffusion_wrapper.py",
                "weights_path": "models/RiboDiffusion/ckpts",
                "input_description": "Requires PDB file of target RNA structure",
                "output_description": "Outputs generated RNA sequences in FASTA format that can fold into the target structure",
                "github_url": "https://github.com/ml4bio/RiboDiffusion",
                "paper_url": "https://arxiv.org/abs/2404.11199",
                "features": [
                    "Tertiary structure-based inverse folding",
                    "Generative diffusion models",
                    "High-quality RNA sequence generation",
                    "Structure-conditioned generation",
                    "Multiple sampling strategies",
                    "Recovery rate evaluation"
                ],
                "environment_required": True,
                "environment_type": "uv",
                "environment_path": "/home/zhangliqin/RNA-Factory/.venv_ribodiffusion",
                "architecture_image": "/static/images/ribodiffusion.png"
            }
        ]

        # Store model configuration in application context
        app.config["PREDEFINED_MODELS"] = models_config

        logger.info(f"Successfully preloaded {len(models_config)} model configurations")

    except Exception as e:
        logger.error(f"Model preloading failed: {e}")
        # Even if preloading fails, the application can still start
        app.config["PREDEFINED_MODELS"] = []
