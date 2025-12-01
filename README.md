# RNA-Factory

A comprehensive web platform for RNA analysis, structure prediction, and interaction prediction, featuring an AI-powered design assistant with multimodal RAG capabilities.

## ⚠️ Important Notice

**Before running the software, please ensure you complete the following preparations:**

1. **Clone Open Source Model Repositories**: First clone the required open source model repositories to the `models` folder
2. **Configure Virtual Environments**: Set up the main project virtual environment `.venv` and individual software model virtual environments `.venv_<software_name>` in the root directory according to `pyproject.toml`
3. **Configure API Key**: Fill in your own `DEEPSEEK_API_KEY` in the `.env` file to run the software correctly

For detailed configuration steps, please refer to the [Getting Started](#getting-started) section below.

Given that the model used by this software requires substantial computational power for inference, we strongly advise against deploying it on personal computers.

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

**Reformer**
- Deep learning model for predicting protein-RNA binding affinity at single-base resolution
- Uses transformer architecture with cDNA sequences for high-accuracy prediction
- Supports 150+ RBP types and multiple cell lines for comprehensive analysis
- Provides binding site identification and confidence scoring
- [GitHub](https://github.com/xilinshen/Reformer) | [Paper](https://www.sciencedirect.com/science/article/pii/S2666389924003222)

**CoPRA**
- State-of-the-art predictor of protein-RNA binding affinity based on protein language model and RNA language model
- Uses ESM2 protein language model and RiNALMo RNA language model with complex structure as input
- Pre-trained on PRI30k dataset and fine-tuned on PRA310 for high accuracy
- Provides binding affinity prediction in kcal/mol with confidence scoring
- Supports protein and RNA sequence input for comprehensive interaction analysis
- [GitHub](https://github.com/hanrthu/CoPRA) | [Paper](https://arxiv.org/abs/2409.03773)

**DeepRPI**
- Deep learning-based RNA-protein interaction prediction using ESM-2 protein language model and RNABert RNA language model
- Features bidirectional cross-attention mechanism for enhanced interaction understanding
- Provides interaction prediction (0/1) with probability scores and confidence levels
- Supports protein sequences up to 500 amino acids and RNA sequences up to 220 nucleotides
- High accuracy prediction with attention heatmap visualization capabilities
- [GitHub](https://github.com/PekingHSC-iGEM/DeepRPI)

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

**RiboDiffusion**
- Diffusion-based model for RNA inverse folding from protein structures
- Generates RNA sequences that can fold into target protein-bound conformations
- Uses conditional diffusion with protein structure conditioning
- Supports customizable sampling parameters and generation settings
- Provides recovery rate scoring and multiple sequence generation
- [GitHub](https://github.com/ml4bio/RiboDiffusion) | [Paper](https://arxiv.org/abs/2404.11199)

### 🔧 Platform Capabilities

- **Multi-format Input Support**: FASTA files, text input, mmCIF structures, PDB structures, SMILES strings, protein sequences, cDNA sequences, RNA sequences, protein-RNA interaction pairs
- **Unified Interface**: Consistent user experience across all models with standardized input areas
- **Real-time Processing**: Fast analysis with progress tracking
- **Multiple Output Formats**: CT, BPSEQ, dot-bracket notation, CSV, PDB, and more
- **Batch Processing**: Support for multiple sequences, ligands, and protein targets
- **Download Options**: Individual files, ZIP archives, or CSV exports for batch results
- **Smart File Upload**: Intelligent file handling with content validation and format detection
- **Adaptive UI**: Dynamic input areas that adjust to content and file uploads
- **Dark Mode Support**: Complete dark theme with consistent styling across all components
- **Responsive Design**: Works on desktop and mobile devices
- **Intelligent Agent System**: Automated model orchestration and multi-step analysis workflows
- **AI-Powered Workflows**: Natural language-driven analysis with automatic tool selection
- **Document Intelligence**: OCR and multimodal analysis of research papers and images
- **Contextual Analysis**: Maintains conversation context and learns from user interactions

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
│   │   ├── reformer_routes.py   # Reformer API endpoints
│   │   ├── copra_routes.py      # CoPRA API endpoints
│   │   ├── deeprpi_routes.py    # DeepRPI API endpoints
│   │   ├── mol2aptamer_routes.py # Mol2Aptamer API endpoints
│   │   ├── rnaflow_routes.py    # RNAFlow API endpoints
│   │   ├── rnaframeflow_routes.py # RNA-FrameFlow API endpoints
│   │   ├── ribodiffusion_routes.py # RiboDiffusion API endpoints
│   │   ├── copilot_routes.py    # AI assistant API endpoints
│   │   └── model_config_routes.py # Model configuration endpoints
│   ├── copilot/                 # AI assistant and RAG system
│   │   ├── copilot.py           # LangGraph-based AI assistant
│   │   ├── agent.py             # Intelligent Agent system for model orchestration
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

#### Agent System (`app/copilot/agent.py`)

The platform features an intelligent Agent system that orchestrates complex RNA analysis workflows:

- **Model Orchestration**: Automatically selects and executes appropriate models based on user queries
- **Multi-Model Analysis**: Coordinates multiple models for comprehensive RNA analysis (e.g., structure prediction + interaction analysis)
- **Tool Management**: Manages 10+ integrated models including BPFold, UFold, MXFold2, RNAformer, RNAmigos2, Reformer, CoPRA, DeepRPI, Mol2Aptamer, RNAFlow, and RiboDiffusion
- **Sequential Workflows**: Executes complex analysis pipelines with proper data flow between models
- **Error Handling**: Robust error handling and fallback mechanisms for model failures
- **Result Integration**: Combines results from multiple models into coherent analysis reports
- **Dynamic Tool Selection**: Intelligently chooses the most appropriate tools based on input data and analysis requirements
- **Progress Tracking**: Real-time progress updates during multi-step analysis workflows
- **Resource Management**: Efficiently manages computational resources and model execution

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
   git clone https://github.com/givemeone1astkiss/RNA-Factory.git
   cd RNA-Factory
```

2. **Clone Required Open Source Model Repositories**
```bash
   # Clone each open source model repository to the models folder
   # Please refer to each model's GitHub links for cloning
   # For example:
   # git clone https://github.com/heqin-zhu/BPfold.git models/BPfold
   # git clone https://github.com/uci-cbcl/UFold.git models/UFold
   # Clone other models to the models folder in the same way
```

3. **Configure Project Virtual Environments**
```bash
   # Configure the main project virtual environment according to pyproject.toml
   python -m venv .venv
   
   # Activate the main virtual environment
   # Windows:
   .venv\Scripts\activate
   # Linux/Mac:
   source .venv/bin/activate
   
   # Install project dependencies
   pip install -e .
   
   # Create independent virtual environments for each software model
   # Note: Each model's environment configuration should be determined according to its own open source repository
   # Please refer to each model's GitHub repository for specific installation and configuration requirements
   python -m venv .venv_bpfold
   python -m venv .venv_ufold
   python -m venv .venv_mxfold2
   python -m venv .venv_rnaformer
   python -m venv .venv_rnamigos2
   python -m venv .venv_reformer
   python -m venv .venv_copra
   python -m venv .venv_deeprpi
   python -m venv .venv_mol2aptamer
   python -m venv .venv_rnaflow
   python -m venv .venv_rnaframeflow
   python -m venv .venv_ribodiffusion
```

4. **Configure Environment Variables**
```bash
   # Create .env file in the root directory and fill in your DEEPSEEK_API_KEY
   echo "DEEPSEEK_API_KEY=your_deepseek_api_key_here" > .env
   # Please replace your_deepseek_api_key_here with your actual API key
```

5. **Run the Application**
```bash
   python run.py
```

6. **Access the Platform**
   Open your browser and navigate to `http://localhost:5000`

## Usage

### Structure Prediction

1. Select a structure prediction model (BPFold, UFold, MXFold2, or RNAformer)
2. Input RNA sequences via text or upload FASTA files
3. Run analysis and view results
4. Download results in various formats (CT, BPSEQ, dot-bracket)

### Interaction Prediction

#### RNAmigos2
1. Select RNAmigos2 for RNA-ligand interaction prediction
2. Upload mmCIF structure file
3. Specify binding site residues
4. Input SMILES strings of ligands
5. Run analysis to get interaction scores

#### Reformer
1. Select Reformer for protein-RNA binding affinity prediction
2. Input cDNA sequence (ATCGN characters only)
3. Select RBP (RNA-binding protein) type from 150+ options
4. Choose cell line (HepG2, K562, or MCF-7)
5. Run analysis to get single-base resolution binding scores

#### CoPRA
1. Select CoPRA for protein-RNA binding affinity prediction
2. Input protein sequence (single letter amino acid codes)
3. Input RNA sequence (A, U, G, C only)
4. Configure confidence threshold (Low/Medium/High/Very High)
5. Run analysis to get binding affinity prediction in kcal/mol with confidence score

#### DeepRPI
1. Select DeepRPI for RNA-protein interaction prediction
2. Input protein sequence (amino acid codes, max 500 residues)
3. Input RNA sequence (A, U, G, C nucleotides, max 220 bases)
4. Run analysis to get interaction prediction (0/1) with probability and confidence scores
5. View results with detailed interaction analysis

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

#### RiboDiffusion
1. Select RiboDiffusion for RNA inverse folding from protein structures
2. Input PDB structure file (via text input or file upload)
3. Configure generation parameters (number of sequences, sampling steps, conditional scale)
4. Run analysis to generate RNA sequences that can fold into target conformations
5. View results with recovery rate scores and download CSV files with generated sequences

### AI Assistant

#### Basic Usage
1. Access the AI assistant from the main interface
2. Ask questions about RNA design, structure analysis, or general bioinformatics
3. Upload documents for multimodal analysis
4. Get expert guidance and recommendations

#### Agent-Powered Analysis
The AI assistant features an intelligent Agent system that can automatically orchestrate complex RNA analysis workflows:

**Automatic Model Selection**
- Upload RNA sequences and let the Agent automatically select appropriate models
- The Agent analyzes your input and determines the best combination of tools
- No need to manually choose between BPFold, UFold, MXFold2, or RNAformer

**Multi-Model Workflows**
- Request comprehensive analysis: "Analyze this RNA sequence for structure and interactions"
- The Agent will automatically run multiple models in sequence
- Get integrated results combining structure prediction, interaction analysis, and design recommendations

**Intelligent Tool Orchestration**
- Upload protein-RNA pairs for interaction analysis
- The Agent automatically selects between Reformer, CoPRA, and DeepRPI based on your data
- Coordinate structure prediction with interaction analysis for complete insights

**Document-Based Analysis**
- Upload research papers, PDFs, or images containing RNA sequences
- The Agent extracts sequences and automatically runs appropriate analyses
- Get comprehensive reports combining document insights with computational predictions

**Custom Analysis Pipelines**
- Request specific analysis workflows: "Design an RNA aptamer for this protein target"
- The Agent orchestrates Mol2Aptamer, RNAFlow, and structure validation tools
- Receive end-to-end solutions with multiple design candidates

**Real-Time Progress Tracking**
- Watch as the Agent executes multiple models in sequence
- Get real-time updates on analysis progress
- Receive detailed reports with results from all executed tools

**Error Recovery and Fallbacks**
- If one model fails, the Agent automatically tries alternative approaches
- Robust error handling ensures you always get useful results
- Intelligent fallback mechanisms maintain analysis quality

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Contact

**Author**: Huaizhi Wang  
**Email**: realwiseking@outlook.com
