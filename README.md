# RNA-Factory

A comprehensive web platform for RNA analysis, structure prediction, and interaction prediction, featuring an AI-powered design assistant with multimodal RAG capabilities.

## Overview

RNA-Factory is an integrated platform that combines multiple state-of-the-art RNA analysis models with an intelligent AI assistant to provide comprehensive RNA research capabilities. The platform supports RNA secondary structure prediction, RNA-ligand interaction prediction, and offers an AI-powered design assistant with retrieval-augmented generation (RAG) for multimodal document processing.

## Features

### 🤖 AI Design Assistant

The platform includes a sophisticated AI assistant powered by LangGraph that provides:

- **Intelligent RNA Design Guidance**: Expert assistance for RNA sequence design, structure optimization, and functional analysis
- **Multimodal RAG System**: Advanced retrieval-augmented generation supporting both text and image documents
- **Document Processing**: Automatic processing of PDFs, images, and text documents with OCR capabilities
- **Contextual Knowledge**: Access to extensive RNA research literature and databases
- **Interactive Design Workflows**: Step-by-step guidance for complex RNA design tasks

### 🧬 Supported Models

#### Structure Prediction Models

**BPFold**
- Deep learning model for RNA secondary structure prediction via base pair motif energy
- Supports canonical and non-canonical base pairs
- Provides confidence scoring and multiple output formats (CSV, BPSEQ, CT, DBN)
- [GitHub](https://github.com/heqin-zhu/BPfold) | [Paper](https://doi.org/10.1038/s41467-025-60048-1)

**UFold**
- Deep learning-based method using image-like sequence representation and Fully Convolutional Networks
- Fast inference (~160ms per sequence)
- Supports sequences up to 1600bp
- [GitHub](https://github.com/uci-cbcl/UFold) | [Paper](https://doi.org/10.1093/nar/gkab1074)

**MXFold2**
- Deep learning-based method with thermodynamic integration
- High accuracy and fast prediction
- Supports long sequences
- [GitHub](https://github.com/mxfold/mxfold2) | [Paper](https://doi.org/10.1038/s41467-021-21194-4)

**RNAformer**
- Simple yet effective deep learning model using two-dimensional latent space
- Features axial attention mechanism and recycling in latent space
- High accuracy on benchmarks with single model approach
- [GitHub](https://github.com/automl/RNAformer) | [Paper](https://arxiv.org/abs/2307.10073)

#### Interaction Prediction Models

**RNAmigos2**
- Virtual screening tool for RNA-ligand interaction prediction using deep graph learning
- Ranks chemical compounds based on binding potential to RNA targets
- Fast inference (~10 seconds) with high enrichment factors
- [GitHub](https://github.com/cgoliver/rnamigos2) | [Paper](https://www.nature.com/articles/s41467-025-57852-0)

#### De Novo Design Models

**Mol2Aptamer**
- Deep learning model for generating RNA aptamers from small molecule SMILES
- Uses transformer-based architecture with BPE tokenization
- Generates high-quality RNA sequences with thermodynamic validation
- Supports customizable generation parameters (temperature, top-k, top-p)

**RNAFlow**
- Flow matching model for protein-conditioned RNA sequence-structure design
- Integrates RNA inverse folding model and RoseTTAFold2NA
- Generates RNA sequences and structures conditioned on protein targets
- Supports customizable RNA length and sample generation
- [GitHub](https://github.com/divnori/rnaflow) | [Paper](https://arxiv.org/abs/2405.18768)

**RNA-FrameFlow**
- Flow matching model for de novo 3D RNA backbone design using SE(3) flow matching
- Generates high-quality 3D RNA backbone structures without sequence information
- Supports customizable structure length, sampling parameters, and generation settings
- Provides confidence scoring and trajectory files for analysis
- [GitHub](https://github.com/rish-16/rna-backbone-design) | [Paper](https://arxiv.org/abs/2406.13839)

### 🔧 Platform Capabilities

- **Multi-format Input Support**: FASTA files, text input, mmCIF structures, SMILES strings, protein sequences
- **Unified Interface**: Consistent user experience across all models with standardized input areas
- **Real-time Processing**: Fast analysis with progress tracking
- **Multiple Output Formats**: CT, BPSEQ, dot-bracket notation, CSV, PDB, and more
- **Batch Processing**: Support for multiple sequences, ligands, and protein targets
- **Download Options**: Individual files, ZIP archives, or CSV exports for batch results
- **Smart File Upload**: Intelligent file handling with content validation and format detection
- **Adaptive UI**: Dynamic input areas that adjust to content and file uploads
- **Dark Mode Support**: Complete dark theme with consistent styling across all components
- **Responsive Design**: Works on desktop and mobile devices

## Code Structure

```
RNA-Factory/
├── app/                          # Main application package
│   ├── __init__.py              # Flask app factory and model configuration
│   ├── api/                     # API routes and endpoints
│   │   ├── bpfold_routes.py     # BPFold API endpoints
│   │   ├── ufold_routes.py      # UFold API endpoints
│   │   ├── mxfold2_routes.py    # MXFold2 API endpoints
│   │   ├── rnaformer_routes.py  # RNAformer API endpoints
│   │   ├── rnamigos2_routes.py  # RNAmigos2 API endpoints
│   │   ├── mol2aptamer_routes.py # Mol2Aptamer API endpoints
│   │   ├── rnaflow_routes.py    # RNAFlow API endpoints
│   │   ├── rnaframeflow_routes.py # RNA-FrameFlow API endpoints
│   │   ├── copilot_routes.py    # AI assistant API endpoints
│   │   └── model_config_routes.py # Model configuration endpoints
│   ├── copilot/                 # AI assistant and RAG system
│   │   ├── copilot.py           # LangGraph-based AI assistant
│   │   ├── rag.py               # Multimodal RAG system
│   │   └── prompts.py           # AI prompts and templates
│   ├── static/                  # Frontend assets
│   │   ├── index.html           # Main web interface
│   │   ├── css/                 # Stylesheets
│   │   └── js/                  # JavaScript functionality
│   └── utils/                   # Utility modules
│       ├── wrappers/            # Model wrapper classes
│       ├── input.py             # Input validation and processing
│       └── output.py            # Output formatting and file generation
├── models/                      # Model directories and weights
├── data/                        # Sample data and documents
├── config.py                    # Application configuration
├── run.py                       # Application entry point
└── pyproject.toml              # Python dependencies
```

## Key Components

### AI Assistant (`app/copilot/`)

The AI assistant is built using LangGraph and provides:

- **Query Classification**: Automatically categorizes user queries (RNA design, general bioinformatics, off-topic)
- **Tool Integration**: Seamless integration with platform models and external tools
- **Context Management**: Maintains conversation context and user preferences
- **Response Generation**: Generates structured, actionable responses

### RAG System (`app/copilot/rag.py`)

The multimodal RAG system features:

- **Document Processing**: Supports PDF, image, and text documents
- **OCR Capabilities**: Extracts text from images and PDFs using Tesseract
- **Vector Storage**: Uses ChromaDB for efficient document retrieval
- **Multimodal Embeddings**: CLIP-based embeddings for image-text understanding
- **Semantic Search**: Advanced retrieval based on semantic similarity

### Model Wrappers (`app/utils/wrappers/`)

Each model has a dedicated wrapper that:

- **Environment Management**: Handles virtual environment setup and activation
- **Input Processing**: Validates and preprocesses input data
- **Model Execution**: Runs model inference with proper error handling
- **Output Parsing**: Converts model outputs to standardized formats

### API Layer (`app/api/`)

RESTful API endpoints for:

- **Model Predictions**: Individual endpoints for each model
- **File Processing**: Upload and processing of various file formats
- **Result Download**: CT file generation and batch download
- **AI Assistant**: Chat interface and document processing

## Getting Started

1. **Clone the repository**
```bash
   git clone https://github.com/your-username/RNA-Factory.git
   cd RNA-Factory
   ```

2. **Install dependencies**
   ```bash
   pip install -e .
```

3. **Set up model environments**
```bash
   # Each model requires its own virtual environment
   # The platform will automatically set up environments on first use
   ```

4. **Run the application**
```bash
   python run.py
   ```

5. **Access the platform**
   Open your browser and navigate to `http://localhost:5000`

## Usage

### Structure Prediction

1. Select a structure prediction model (BPFold, UFold, MXFold2, or RNAformer)
2. Input RNA sequences via text or upload FASTA files
3. Run analysis and view results
4. Download results in various formats (CT, BPSEQ, dot-bracket)

### Interaction Prediction

1. Select RNAmigos2 for interaction prediction
2. Upload mmCIF structure file
3. Specify binding site residues
4. Input SMILES strings of ligands
5. Run analysis to get interaction scores

### De Novo Design

#### Mol2Aptamer
1. Select Mol2Aptamer for aptamer generation
2. Input small molecule SMILES string (via text or file upload)
3. Configure generation parameters (number of sequences, max length, temperature, etc.)
4. Run analysis to generate RNA aptamers
5. View results with thermodynamic validation and download CSV files

#### RNAFlow
1. Select RNAFlow for protein-conditioned RNA design
2. Input protein sequence (via text or file upload)
3. Specify desired RNA length and number of samples
4. Run analysis to generate RNA sequences and structures
5. View results with confidence scores and download PDB structures

#### RNA-FrameFlow
1. Select RNA-FrameFlow for de novo 3D RNA backbone design
2. Configure structure parameters (length, number of structures, temperature, random seed)
3. Set advanced sampling parameters (timesteps, minimum time, exponential rate, self-conditioning)
4. Run analysis to generate 3D RNA backbone structures
5. View results with confidence scores and download PDB files with trajectory data

### AI Assistant

1. Access the AI assistant from the main interface
2. Ask questions about RNA design, structure analysis, or general bioinformatics
3. Upload documents for multimodal analysis
4. Get expert guidance and recommendations

## Contributing

We welcome contributions to RNA-Factory! Please feel free to submit issues, feature requests, or pull requests.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Contact

**Author**: Huaizhi Wang  
**Email**: realwiseking@outlook.com

## Acknowledgments

We thank the developers of the integrated models and the open-source community for their valuable contributions to RNA research and machine learning.