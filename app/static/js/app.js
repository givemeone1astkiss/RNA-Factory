// RNA Model Integration Platform Frontend JavaScript

// Global variables
let availableModels = [];
let currentModel = null;
let analysisHistory = [];
let currentTheme = 'light';
let isAIResponding = false;
let currentAbortController = null;
let shouldStopStreaming = false;

// Markdown configuration
marked.setOptions({
    highlight: function(code, lang) {
        if (lang && Prism.languages[lang]) {
            return Prism.highlight(code, Prism.languages[lang], lang);
        }
        return code;
    },
    breaks: true,
    gfm: true,
    tables: true,
    sanitize: false,
    pedantic: false,
    smartLists: true,
    smartypants: true
});

// Initialize when page loads
document.addEventListener('DOMContentLoaded', function() {
    // RNA Model Integration Platform loaded
    showLoadingPage();
    initializeApp();
    initializeTheme();
    initializeMultimodalRAG();
});

// Show loading page with simplified animation
function showLoadingPage() {
    const loadingPage = document.getElementById('loadingPage');
    
    // Simple loading animation with random duration
    const minDuration = 2000; // Minimum 2 seconds
    const maxDuration = 4000; // Maximum 4 seconds
    const duration = Math.random() * (maxDuration - minDuration) + minDuration;
    
    setTimeout(() => {
        loadingPage.classList.add('fade-out');
        setTimeout(() => {
            loadingPage.style.display = 'none';
        }, 800);
    }, duration);
}

// Initialize application
async function initializeApp() {
    try {
        await loadAvailableModels();
        renderModelTabs();
        
        if (availableModels.length > 0) {
            selectModel(availableModels[0]);
        }
        
        bindEvents();
        initializeRNAmigos2FileUploads();
    } catch (error) {

        showNotification('Application initialization failed', 'error');
    }
}

// Initialize Multimodal RAG functionality
function initializeMultimodalRAG() {
    try {
        // RAG functionality is now integrated into the AI assistant automatically
        // No additional UI buttons needed - the system will automatically use data files

    } catch (error) {

    }
}

// RAG functionality is now automatically integrated into the AI assistant
// The system will automatically use documents from the data directory when answering questions
// No additional UI buttons are needed as the integration is seamless

// Update send button based on AI responding state
function updateSendButton() {
    const sendButton = document.querySelector('.ai-send-btn');
    if (!sendButton) return;
    
    if (isAIResponding) {
        // Change to stop button
        sendButton.innerHTML = '<i class="fas fa-stop"></i>';
        sendButton.title = 'Stop Response';
        sendButton.classList.add('stop-button');
    } else {
        // Change back to send button
        sendButton.innerHTML = '<i class="fas fa-paper-plane"></i>';
        sendButton.title = 'Send Message';
        sendButton.classList.remove('stop-button');
    }
}

// Stop AI response
function stopAIResponse() {

    // Force stop immediately - set flags first
    isAIResponding = false;
    shouldStopStreaming = true;
    updateSendButton();
    
    // Abort the request
    if (currentAbortController) {

        currentAbortController.abort();
        currentAbortController = null;
    }
    
    // Remove typing indicator if present
    removeTypingIndicator();
    
    // Add stopped message immediately
    addMessageToChat('assistant', 'Response stopped by user.');

}

// Initialize theme from localStorage
function initializeTheme() {
    const savedTheme = localStorage.getItem('theme') || 'light';
    setTheme(savedTheme);
}

// Toggle theme between light and dark
function toggleTheme() {
    const newTheme = currentTheme === 'light' ? 'dark' : 'light';
    setTheme(newTheme);
}

// Set theme and update UI
function setTheme(theme) {
    currentTheme = theme;
    document.documentElement.setAttribute('data-theme', theme);
    localStorage.setItem('theme', theme);
    
    // Update theme toggle button
    const themeIcon = document.getElementById('themeIcon');
    const themeText = document.getElementById('themeText');
    
    if (theme === 'dark') {
        themeIcon.className = 'fas fa-sun';
        themeText.textContent = 'Light Mode';
    } else {
        themeIcon.className = 'fas fa-moon';
        themeText.textContent = 'Dark Mode';
    }
}

// Load available models
async function loadAvailableModels() {
    try {
        // Try to load models from API first

        const response = await fetch('/api/models');
        
        if (response.ok) {
            const data = await response.json();
            if (data.success && data.models) {
                availableModels = data.models;

                return;
            }
        }
        
        // Fallback to hardcoded models if API fails

        availableModels = [
            {
                id: 'bpfold',
                name: 'BPFold',
                category: 'structure_prediction',
                category_name: 'Structure Prediction',
                status: 'available',
                description: 'Deep generalizable prediction of RNA secondary structure via base pair motif energy',
                version: '0.2.0',
                accuracy: '90%',
                github_url: 'https://github.com/heqin-zhu/BPfold',
                paper_url: 'https://doi.org/10.1038/s41467-025-60048-1'
            },
            {
                id: 'ufold',
                name: 'UFold',
                category: 'structure_prediction',
                category_name: 'Structure Prediction',
                status: 'available',
                description: 'Fast and Accurate RNA Secondary Structure Prediction with Deep Learning',
                version: '1.3',
                accuracy: '92%',
                github_url: 'https://github.com/uci-cbcl/UFold',
                paper_url: 'https://doi.org/10.1093/nar/gkab1074'
            },
            {
                id: 'mxfold2',
                name: 'MXFold2',
                category: 'structure_prediction',
                category_name: 'Structure Prediction',
                status: 'available',
                description: 'RNA secondary structure prediction using deep learning with thermodynamic integration',
                version: '0.1.2',
                accuracy: '91%',
                github_url: 'https://github.com/mxfold/mxfold2',
                paper_url: 'https://doi.org/10.1038/s41467-021-21194-4'
            },
            {
                id: 'rnamigos2',
                name: 'RNAmigos2',
                category: 'interaction_prediction',
                category_name: 'Interaction Prediction',
                status: 'available',
                description: 'RNA-ligand interaction prediction using deep graph learning for virtual screening',
                version: '2.0',
                accuracy: 'High enrichment',
                github_url: 'https://github.com/cgoliver/rnamigos2',
                paper_url: 'https://doi.org/10.1038/s41467-025-60048-1'
            }
        ];

    } catch (error) {

        throw error;
    }
}

// Render model tabs - organized by category
function renderModelTabs() {
    const tabsContainer = document.getElementById('modelTabs');
    
    if (!tabsContainer || availableModels.length === 0) {
        return;
    }
    
    // Group models by category
    const categories = {};
    availableModels.forEach(model => {
        const category = model.category || 'other';
        const categoryName = model.category_name || 'Other';
        if (!categories[category]) {
            categories[category] = {
                name: categoryName,
                models: []
            };
        }
        categories[category].models.push(model);
    });
    
    let html = '';
    
    // Render each category
    Object.keys(categories).forEach(categoryKey => {
        const category = categories[categoryKey];
        
        html += `
            <div class="category-section" data-category="${categoryKey}">
                <div class="category-header" onclick="toggleCategoryDropdown('${categoryKey}')">
                    <i class="fas fa-layer-group"></i>
                    <span>${category.name}</span>
                    <i class="fas fa-chevron-down dropdown-icon" id="dropdown-icon-${categoryKey}"></i>
                </div>
                <div class="category-models" id="category-models-${categoryKey}">
        `;
        
        // Render models in this category
        category.models.forEach(model => {
        html += `
            <button class="model-tab" data-model-id="${model.id}" onclick="selectModel('${model.id}')">
                <div class="model-name">${model.name}</div>
            </button>
            `;
        });
        
        html += `
                </div>
            </div>
        `;
    });
    
    tabsContainer.innerHTML = html;
    
    // Initialize dropdown states
    initializeCategoryDropdowns();
}

// Select model
function selectModel(modelId) {
    if (typeof modelId === 'string') {
        currentModel = availableModels.find(m => m.id === modelId);
    } else {
        currentModel = modelId;
    }
    
    if (!currentModel) {

        return;
    }
    
    // Auto-close other categories and expand the selected category
    autoCloseOtherCategories(modelId);
    
    // Add animation class to current tab
    const currentTab = document.querySelector(`[data-model-id="${currentModel.id}"]`);
    if (currentTab) {
        currentTab.classList.add('selection-animation');
        setTimeout(() => {
            currentTab.classList.remove('selection-animation');
        }, 600);
    }
    
    // Clear input areas when switching models
    clearInputAreas();
    
    // Animate content transition
    animateContentTransition(() => {
    updateModelSelection();
    updateModelInfo();
    showInputSection();
    // Adjust input interface based on model type after DOM updates
    // Use setTimeout to ensure DOM is fully updated
    setTimeout(() => {
        adjustInputInterface();
    }, 100);
    });
    
    // Selected model
}

// Clear input areas when switching models
function clearInputAreas() {
    // Clear main text input
    const inputText = document.getElementById('inputText');
    if (inputText) {
        inputText.value = '';
        // Reset textarea height
        autoResizeTextarea(inputText);
    }

    // Clear file input and file info display
    const inputFile = document.getElementById('inputFile');
    if (inputFile) {
        inputFile.value = '';
    }
    
    // Clear general file upload area
    const uploadArea = document.getElementById('fileUploadArea');
    if (uploadArea) {
        // Hide file info and show upload content
        const fileInfo = uploadArea.querySelector('.file-info');
        if (fileInfo) {
            fileInfo.style.display = 'none';
        }
        
        const uploadContent = uploadArea.querySelector('.upload-content');
        if (uploadContent) {
            uploadContent.style.display = 'block';
        }
    }
    
    // Clear RNAmigos2 specific inputs
    const rnamigos2Input = document.getElementById('rnamigos2Input');
    if (rnamigos2Input) {
        // Clear CIF file input
        const cifFileInput = document.getElementById('rnamigos2FileInput');
        if (cifFileInput) {
            cifFileInput.value = '';
        }
        
        // Clear CIF file display
        const cifUploadArea = document.getElementById('rnamigos2FileUpload');
        if (cifUploadArea) {
            const cifFileInfo = cifUploadArea.querySelector('.file-info');
            if (cifFileInfo) {
                cifFileInfo.style.display = 'none';
            }
            const cifUploadContent = cifUploadArea.querySelector('.upload-content');
            if (cifUploadContent) {
                cifUploadContent.style.display = 'block';
            }
        }
        
        // Clear SMILES file input
        const smilesFileInput = document.getElementById('rnamigos2SmilesFileInput');
        if (smilesFileInput) {
            smilesFileInput.value = '';
        }
        
        // Clear SMILES file display
        const smilesUploadArea = document.getElementById('rnamigos2SmilesFileUpload');
        if (smilesUploadArea) {
            const smilesFileInfo = smilesUploadArea.querySelector('.file-info');
            if (smilesFileInfo) {
                smilesFileInfo.style.display = 'none';
            }
            const smilesUploadContent = smilesUploadArea.querySelector('.upload-content');
            if (smilesUploadContent) {
                smilesUploadContent.style.display = 'block';
            }
        }
        
        // Clear text inputs
        const residuesElement = document.getElementById('rnamigos2Residues');
        if (residuesElement) {
            residuesElement.value = '';
            autoResizeTextarea(residuesElement);
        }
        
        const smilesTextElement = document.getElementById('rnamigos2SmilesText');
        if (smilesTextElement) {
            smilesTextElement.value = '';
            autoResizeTextarea(smilesTextElement);
        }
    }
    
    
    // Clear any result sections
    const resultSection = document.getElementById('resultSection');
    if (resultSection) {
        resultSection.style.display = 'none';
    }
    
    // Clear any analysis results
    const analysisResults = document.querySelector('.analysis-results');
    if (analysisResults) {
        analysisResults.innerHTML = '';
    }
    
    // Clear BPFold options
    const ignoreNonCanonical = document.getElementById('ignoreNonCanonical');
    if (ignoreNonCanonical) {
        ignoreNonCanonical.checked = false;
    }
}

// Update model selection state
function updateModelSelection() {
    document.querySelectorAll('.model-tab').forEach(tab => {
        tab.classList.remove('active');
    });
    
    const currentTab = document.querySelector(`[data-model-id="${currentModel.id}"]`);
    if (currentTab) {
        currentTab.classList.add('active');
    }
}

// Switch to selected model
function switchToModel(modelId) {
    if (!modelId) {

        return;
    }
    
    // Auto-close other categories and expand the selected category
    autoCloseOtherCategories(modelId);
    
    // Update active tab
    document.querySelectorAll('.model-tab').forEach(tab => {
        tab.classList.remove('active');
    });
    
    const activeTab = document.querySelector(`[data-model-id="${modelId}"]`);
    if (activeTab) {
        activeTab.classList.add('active');
    }
    
    // Add animation class to current tab
    const currentTab = document.querySelector('.model-tab.active');
    if (currentTab) {
        currentTab.classList.add('selection-animation');
        setTimeout(() => {
            currentTab.classList.remove('selection-animation');
        }, 600);
    }
    
    // Clear input areas when switching models
    clearInputAreas();
    
    // Animate content transition
    animateContentTransition(() => {
        updateModelSelection();
        updateModelInfo();
        showInputSection();
    });
    
    // Selected model
    selectedModel = modelId;

}

// Animate content transition when switching models
function animateContentTransition(callback) {
    const contentHeader = document.getElementById('contentHeader');
    const inputSection = document.getElementById('inputSection');
    const resultSection = document.getElementById('resultSection');
    const historySection = document.getElementById('historySection');
    
    // Add fade-out effect to current content
    [contentHeader, inputSection, resultSection, historySection].forEach(element => {
        if (element && element.style.display !== 'none') {
            element.classList.add('content-fade-out');
        }
    });
    
    // After fade-out, update content and fade-in
    setTimeout(() => {
        // Execute callback to update content
        if (callback) callback();
        
        // Add fade-in effect to new content
        setTimeout(() => {
            [contentHeader, inputSection, resultSection, historySection].forEach(element => {
                if (element && element.style.display !== 'none') {
                    element.classList.remove('content-fade-out');
                    element.classList.add('content-fade-in');
                }
            });
            
            // Remove animation classes after animation completes
            setTimeout(() => {
                [contentHeader, inputSection, resultSection, historySection].forEach(element => {
                    if (element) {
                        element.classList.remove('content-fade-out', 'content-fade-in');
                    }
                });
            }, 400);
        }, 50);
    }, 200);
}

// Update model information display
function updateModelInfo() {
    if (!currentModel) return;
    
    // Animate title and description update
    const titleElement = document.getElementById('currentModelTitle');
    const descElement = document.getElementById('currentModelDesc');
    
    if (titleElement && descElement) {
        // Fade out current content
        titleElement.style.opacity = '0.7';
        descElement.style.opacity = '0.7';
        
        setTimeout(() => {
            // Update content
            titleElement.textContent = currentModel.name;
            descElement.textContent = currentModel.description;
            
            // Fade in new content with slide effect
            titleElement.style.opacity = '1';
            descElement.style.opacity = '1';
            titleElement.style.transform = 'translateY(0)';
            descElement.style.transform = 'translateY(0)';
        }, 150);
    }
    
    // Update model links (GitHub and Paper)
    updateModelLinks(currentModel);
    
    // Update model architecture
    updateModelArchitecture(currentModel);
    
    // Adjust input interface based on model type
    adjustInputInterface();
}

// Adjust input interface based on model type
function adjustInputInterface() {
    const bpfoldOptions = document.getElementById('bpfoldOptions');
    const rnamigos2Input = document.getElementById('rnamigos2Input');
    const fileAcceptInfo = document.getElementById('fileAcceptInfo');
    
    // Get general input areas by ID
    const fileUploadArea = document.getElementById('generalFileUpload');
    const textInputArea = document.getElementById('generalTextInput');
    
    if (!fileAcceptInfo) return;
    
    // Hide all model-specific inputs first
    if (bpfoldOptions) bpfoldOptions.style.display = 'none';
    if (rnamigos2Input) rnamigos2Input.style.display = 'none';
    
    // Show general input areas by default
    if (fileUploadArea) fileUploadArea.style.display = 'flex';
    if (textInputArea) textInputArea.style.display = 'flex';
    
    if (currentModel.id === 'bpfold') {
        // BPFold model has specific options
        if (bpfoldOptions) bpfoldOptions.style.display = 'flex';
        const optionLabel = document.getElementById('optionLabel');
        if (optionLabel) optionLabel.textContent = 'Ignore non-canonical base pairs';
        fileAcceptInfo.textContent = 'Supports FASTA, TXT formats';
    } else if (currentModel.id === 'ufold') {
        // UFold model has specific options
        if (bpfoldOptions) bpfoldOptions.style.display = 'flex';
        const optionLabel = document.getElementById('optionLabel');
        if (optionLabel) optionLabel.textContent = 'Ignore non-canonical base pairs';
        fileAcceptInfo.textContent = 'Supports FASTA, TXT formats';
    } else if (currentModel.id === 'rnamigos2') {
        // RNAmigos2 model has specific input interface
        if (rnamigos2Input) rnamigos2Input.style.display = 'flex';
        // Hide general input areas for RNAmigos2
        if (fileUploadArea) fileUploadArea.style.display = 'none';
        if (textInputArea) textInputArea.style.display = 'none';
        fileAcceptInfo.textContent = 'Supports mmCIF, SMILES formats';
    } else if (currentModel.id === 'rnaformer') {
        // RNAformer model uses general input interface (same as MXFold2)
        fileAcceptInfo.textContent = 'Supports FASTA, TXT formats';
    } else {
        // Other models
        fileAcceptInfo.textContent = 'Supports FASTA, TXT formats';
    }
}

// Show input section
function showInputSection() {
    const inputSection = document.getElementById('inputSection');
    const historySection = document.getElementById('historySection');
    
    // Hide history section only (keep result section visible if it has content)
    if (historySection) {
        historySection.style.display = 'none';
    }
    
    // Show input section with slide-up animation
    if (inputSection) {
        inputSection.style.display = 'block';
        inputSection.classList.add('content-fade-in');
        
        // Remove animation class after completion
        setTimeout(() => {
            inputSection.classList.remove('content-fade-in');
        }, 400);
    }
}

// Show result section with animation
function showResultSection() {
    const resultSection = document.getElementById('resultSection');
    const historySection = document.getElementById('historySection');
    
    // Hide history section only (keep input section visible)
    if (historySection) {
        historySection.style.display = 'none';
    }
    
    // Show result section with slide-up animation
    if (resultSection) {
        resultSection.style.display = 'block';
        resultSection.classList.add('content-fade-in');
        
        // Remove animation class after completion
        setTimeout(() => {
            resultSection.classList.remove('content-fade-in');
        }, 400);
    }
}

// Show history section with animation
function showHistorySection() {
    const inputSection = document.getElementById('inputSection');
    const resultSection = document.getElementById('resultSection');
    const historySection = document.getElementById('historySection');
    
    // Hide other sections
    [inputSection, resultSection].forEach(section => {
        if (section) {
            section.style.display = 'none';
        }
    });
    
    // Show history section with slide-up animation
    if (historySection) {
        historySection.style.display = 'block';
        historySection.classList.add('content-fade-in');
        
        // Remove animation class after completion
        setTimeout(() => {
            historySection.classList.remove('content-fade-in');
        }, 400);
    }
}

// Bind events
function bindEvents() {
    // File upload events
    const fileInput = document.getElementById('inputFile');
    if (fileInput) {
        fileInput.addEventListener('change', handleFileSelect);
    }
    
    // Text input events
    const textInput = document.getElementById('inputText');
    if (textInput) {
        // Auto-resize functionality for main text input
        autoResizeTextarea(textInput);
    }

    // Drag and drop upload
    const uploadArea = document.getElementById('fileUploadArea');
    if (uploadArea) {
        uploadArea.addEventListener('dragover', handleDragOver);
        uploadArea.addEventListener('drop', handleDrop);
        uploadArea.addEventListener('click', () => fileInput.click());
        
        // Add drag leave event
        uploadArea.addEventListener('dragleave', () => {
            uploadArea.classList.remove('dragover');
        });
    }
}

// Handle file selection
function handleFileSelect(event) {
    const file = event.target.files[0];
    if (file) {
        // Selected file
        displayFileInfo(file);
    }
}

// Handle drag and drop
function handleDragOver(event) {
    event.preventDefault();
    event.currentTarget.classList.add('dragover');
}

function handleDrop(event) {
    event.preventDefault();
    event.currentTarget.classList.remove('dragover');
    
    const files = event.dataTransfer.files;
    if (files.length > 0) {
        const file = files[0];
        const fileName = file.name.toLowerCase();
        const allowedExtensions = ['.fasta', '.fa', '.txt'];
        const fileExtension = '.' + fileName.split('.').pop();
        
        if (allowedExtensions.includes(fileExtension)) {
            const fileInput = document.getElementById('inputFile');
            fileInput.files = files;
            // Manually trigger the change event
            const changeEvent = new Event('change', { bubbles: true });
            fileInput.dispatchEvent(changeEvent);
        } else {
            showNotification('Please upload a FASTA or TXT file', 'warning');
        }
    }
}

// Display file information
function displayFileInfo(file) {
    const uploadArea = document.getElementById('fileUploadArea');
    
    if (uploadArea) {
        // Hide the upload content and show file info
        const uploadContent = uploadArea.querySelector('.upload-content');
        if (uploadContent) {
            uploadContent.style.display = 'none';
        }
        
        // Create or update file info display inside the upload area
        let fileInfo = uploadArea.querySelector('.file-info');
        if (!fileInfo) {
            fileInfo = document.createElement('div');
            fileInfo.className = 'file-info';
            uploadArea.appendChild(fileInfo);
        }
        
        const fileSize = formatFileSize(file.size);
        const fileExtension = file.name.split('.').pop().toLowerCase();
        
        fileInfo.innerHTML = `
            <div class="file-info-content">
                <i class="fas fa-file-${fileExtension === 'txt' ? 'alt' : 'code'}"></i>
                <div class="file-details">
                    <div class="file-name">${file.name}</div>
                    <div class="file-size">${fileSize}</div>
                </div>
                <button class="btn-remove-file" onclick="removeGeneralFile()">
                    <i class="fas fa-times"></i>
                </button>
            </div>
        `;
        fileInfo.style.display = 'block';
    }
}

// Remove general file
function removeGeneralFile() {
    const fileInput = document.getElementById('inputFile');
    const uploadArea = document.getElementById('fileUploadArea');
    
    if (fileInput) {
        fileInput.value = '';
    }
    
    if (uploadArea) {
        // Hide file info and show upload content
        const fileInfo = uploadArea.querySelector('.file-info');
        if (fileInfo) {
            fileInfo.style.display = 'none';
        }
        
        const uploadContent = uploadArea.querySelector('.upload-content');
        if (uploadContent) {
            uploadContent.style.display = 'block';
        }
    }
}

// Format file size
function formatFileSize(bytes) {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}

// Run analysis
async function runAnalysis() {
    if (!currentModel) {
        showNotification('Please select a model first', 'warning');
        return;
    }
    
    // Declare variables in the correct scope
    let inputFile, inputText;
    
    // For RNAmigos2, skip general input validation as it has its own validation
    if (currentModel.id !== 'rnamigos2') {
        // For other models, use general input validation
        inputFile = document.getElementById('inputFile').files[0];
        inputText = document.getElementById('inputText').value.trim();

        if (!inputFile && !inputText) {
            showNotification('Please provide input data (file or text)', 'warning');
            return;
        }
    }
    
    try {
        showLoading(true);
        
        // Clear previous results before starting new analysis
        clearResults();
        
        const formData = new FormData();
        if (inputFile) {
            formData.append('file', inputFile);
        }
        
        // Handle BPFold differently
        if (currentModel.id === 'bpfold') {
            const response = await runBPFoldAnalysis(inputFile, inputText);
            const result = await response.json();
            
            if (result.success) {
                displayResults(result);
                addToHistory(currentModel, inputFile ? inputFile.name : inputText, result);
                showNotification('Analysis completed!', 'success');
            } else {
                throw new Error(result.error);
            }
        } else if (currentModel.id === 'ufold') {
            const response = await runUFoldAnalysis(inputFile, inputText);
            const result = await response.json();
            
            if (result.success) {
                displayResults(result);
                addToHistory(currentModel, inputFile ? inputFile.name : inputText, result);
                showNotification('Analysis completed!', 'success');
            } else {
                throw new Error(result.error);
            }
        } else if (currentModel.id === 'mxfold2') {
            const response = await runMXFold2Analysis(inputFile, inputText);
            const result = await response.json();
            
            if (result.success) {
                displayResults(result);
                addToHistory(currentModel, inputFile ? inputFile.name : inputText, result);
                showNotification('Analysis completed!', 'success');
            } else {
                throw new Error(result.error);
            }
        } else if (currentModel.id === 'rnamigos2') {
            const response = await runRNAmigos2Analysis();
            const result = await response.json();
            
            if (result.success) {
                displayResults(result);
                addToHistory(currentModel, 'RNAmigos2 Analysis', result);
                showNotification('Analysis completed!', 'success');
            } else {
                throw new Error(result.error);
            }
        } else if (currentModel.id === 'rnaformer') {
            const response = await runRNAformerAnalysis(inputFile, inputText);
            const result = await response.json();
            
            if (result.success) {
                displayResults(result);
                addToHistory(currentModel, inputFile ? inputFile.name : inputText, result);
                showNotification('Analysis completed!', 'success');
            } else {
                throw new Error(result.error);
            }
        } else {
            // For models other than BPFold, show a message that they are not yet implemented
            const result = {
                success: true,
                result: {
                    model_type: currentModel.type,
                    message: `${currentModel.name} model is not yet implemented. This is a placeholder result.`,
                    status: 'not_implemented',
                    input_processed: inputFile ? inputFile.name : inputText.substring(0, 100) + (inputText.length > 100 ? '...' : ''),
                    confidence: 0.0
                }
            };
            
            displayResults(result);
            addToHistory(currentModel, inputFile ? inputFile.name : inputText, result);
            showNotification(`${currentModel.name} model is not yet implemented`, 'warning');
        }
        
    } catch (error) {

        showNotification(`Analysis failed: ${error.message}`, 'error');
    } finally {
        showLoading(false);
    }
}

// Clear previous results
function clearResults() {
    const resultContent = document.getElementById('resultContent');
    const downloadActions = document.getElementById('downloadActions');
    
    if (resultContent) {
        resultContent.innerHTML = `
            <div class="no-results-placeholder">
                <i class="fas fa-chart-line"></i>
                <p>No results yet. Run an analysis to see results here.</p>
            </div>
        `;
    }
    
    // Hide download button
    if (downloadActions) {
        downloadActions.style.display = 'none';
    }
    
    // Clear global results
    window.currentBPFoldResults = null;
}

// Display results
function displayResults(result) {
    const resultContent = document.getElementById('resultContent');
    
    // Check for result data (different models use different field names)
    if (!result.result && !result.results) {
        resultContent.innerHTML = '<div class="alert alert-warning">No result data</div>';
        showResultSection(); // Always show result section
        return;
    }
    
    let html = '';
    
    // Select appropriate result display method based on current model ID
    if (currentModel.id === 'bpfold') {
        html = displayBPFoldResults(result.results);
    } else if (currentModel.id === 'ufold') {
        html = displayUFoldResults(result.results);
    } else if (currentModel.id === 'mxfold2') {
        html = displayMXFold2Results(result.results);
    } else if (currentModel.id === 'rnamigos2') {
        html = displayRNAmigos2Results(result.results);
    } else if (currentModel.id === 'rnaformer') {
        html = displayRNAformerResults(result.results);
    } else {
        html = displayDefaultResults(result.result);
    }
    
    resultContent.innerHTML = html;
    showResultSection(); // Always show result section after displaying results
}

// Display MFold results

// Display RNA-MPNN results
function displayRNAMPNNResults(result) {
    if (result.error) {
        return `<div class="alert alert-danger">${result.error}</div>`;
    }
    
    return `
        <div class="result-grid">
            <div class="result-item">
                <h6><i class="fas fa-cube"></i>Structure Type</h6>
                <div class="result-value">${result.structure_type}</div>
            </div>
            <div class="result-item">
                <h6><i class="fas fa-chart-line"></i>Confidence</h6>
                <div class="result-value">${(result.confidence_score * 100).toFixed(1)}%</div>
            </div>
            <div class="result-item">
                <h6><i class="fas fa-dna"></i>Structure</h6>
                <div class="result-value">${result.secondary_structure}</div>
            </div>
            <div class="result-item">
                <h6><i class="fas fa-link"></i>Tertiary Contacts</h6>
                <div class="result-value">${result.tertiary_contacts}</div>
            </div>
            <div class="result-item">
                <h6><i class="fas fa-ruler"></i>RMSD</h6>
                <div class="result-value">${result.structural_metrics.rmsd} Å</div>
            </div>
            <div class="result-item">
                <h6><i class="fas fa-exclamation-triangle"></i>Clash Score</h6>
                <div class="result-value">${result.structural_metrics.clash_score}</div>
            </div>
            <div class="result-item">
                <h6><i class="fas fa-shapes"></i>Geometry Score</h6>
                <div class="result-value">${result.structural_metrics.geometry_score}</div>
            </div>
            <div class="result-item">
                <h6><i class="fas fa-star"></i>Quality Assessment</h6>
                <div class="result-value">${result.quality_assessment}</div>
            </div>
            <div class="result-item" style="grid-column: 1 / -1;">
                <h6><i class="fas fa-dna"></i>Predicted Motifs</h6>
                <div class="result-value">${result.predicted_motifs.join(', ')}</div>
            </div>
        </div>
    `;
}

// Display default results
function displayDefaultResults(result) {
    // Filter out empty values before displaying
    const filteredResult = filterEmptyValues(result);
    
    return `
        <div class="result-grid">
            <div class="result-item" style="grid-column: 1 / -1;">
                <h6><i class="fas fa-info-circle"></i>Analysis Results</h6>
                <div class="result-value">
                    <pre>${JSON.stringify(filteredResult, null, 2)}</pre>
                </div>
            </div>
        </div>
    `;
}

// Display RNAmigos2 results
function displayRNAmigos2Results(results) {
    if (results.error) {
        return `<div class="alert alert-danger">${results.error}</div>`;
    }
    
    const interactions = results.interactions || [];
    const summary = results.summary || {};
    
    if (interactions.length === 0) {
        return `<div class="alert alert-warning">No interaction predictions found</div>`;
    }
    
    // Store results globally for download functionality
    window.currentRNAmigos2Results = results;
    
    let html = '<div class="rnamigos2-results">';
    
    // Add summary information similar to other models
    html += `
        <div class="result-item">
            <h6><i class="fas fa-flask"></i>RNA-Ligand Interaction Predictions</h6>
            <div class="sequence-info">
                <div class="sequence-info-stats">
                    <div class="sequence-length">Total Ligands: ${summary.total_ligands || interactions.length}</div>
                    <div class="sequence-length">Best Score: ${(summary.best_score || 0).toFixed(3)}</div>
                    <div class="sequence-length">Average Score: ${(summary.average_score || 0).toFixed(3)}</div>
                </div>
            </div>
        </div>
    `;
    
    // Add interactions table
    const tableRows = interactions.map((interaction, index) => {
        const score = interaction.score || 0;
        let scoreClass = 'score-low';
        if (score > 0.7) scoreClass = 'score-high';
        else if (score > 0.4) scoreClass = 'score-medium';
        
        return `
            <tr>
                <td>${index + 1}</td>
                <td class="smiles-cell">${interaction.smiles || 'N/A'}</td>
                <td class="score-cell ${scoreClass}">${score.toFixed(3)}</td>
            </tr>
        `;
    }).join('');
    
    html += `
        <div class="result-item">
            <h6><i class="fas fa-table"></i>Interaction Scores</h6>
            <div class="structure-result">
                <div class="interactions-table">
                    <table>
                        <thead>
                            <tr>
                                <th>Rank</th>
                                <th>SMILES</th>
                                <th>Score</th>
                            </tr>
                        </thead>
                        <tbody>
                            ${tableRows}
                        </tbody>
                    </table>
                </div>
            </div>
        </div>
    `;
    
    html += '</div>';
    
    // Show download button
    const downloadActions = document.getElementById('downloadActions');
    if (downloadActions) {
        downloadActions.style.display = 'flex';
    }
    
    return html;
}

// Display RNAformer results
function displayRNAformerResults(results) {
    if (!results || results.length === 0) {
        return '<div class="alert alert-warning">No results available</div>';
    }
    
    // Store results globally for download functionality
    window.currentRNAformerResults = results;
    
    let html = '<div class="rnaformer-results">';
    
    results.forEach((result, index) => {
        // Get dot-bracket notation from result data (same structure as MXFold2)
        const dotBracket = result.dot_bracket || '';
        const sequence = result.sequence || '';
        const length = result.length || sequence.length;
        
        html += `
            <div class="result-item">
                <h6><i class="fas fa-dna"></i>Sequence ${index + 1}</h6>
                <div class="sequence-info">
                    <div class="sequence-text">${sequence}</div>
                    <div class="sequence-info-stats">
                        <div class="sequence-length">Length: ${length} nucleotides</div>
                    </div>
                </div>
                <div class="structure-result">
                    <h6><i class="fas fa-project-diagram"></i>Secondary Structure</h6>
                    <div class="structure-display">
                        <pre class="structure-text">${dotBracket ? `Dot-Bracket Notation:\n${dotBracket}` : 'No structure data available'}</pre>
                    </div>
                </div>
            </div>
        `;
    });
    
    html += '</div>';
    
    // Show download button
    const downloadActions = document.getElementById('downloadActions');
    if (downloadActions) {
        downloadActions.style.display = 'flex';
    }
    
    return html;
}

// Add to history
function addToHistory(model, input, result) {
    const historyItem = {
        id: Date.now(),
        timestamp: new Date().toLocaleString(),
        model: model.name,
        input: input,
        result: result.result || result.results || result
    };
    
    analysisHistory.unshift(historyItem);
    
    if (analysisHistory.length > 10) {
        analysisHistory = analysisHistory.slice(0, 10);
    }
}

// Show history
function showHistory() {
    const historyContent = document.getElementById('historyContent');
    
    if (analysisHistory.length === 0) {
        historyContent.innerHTML = '<p class="text-muted">No analysis history</p>';
        return;
    }
    
    let html = '<div class="table-responsive"><table class="table table-hover">';
    html += '<thead><tr><th>Time</th><th>Model</th><th>Input</th><th>Action</th></tr></thead><tbody>';
    
    analysisHistory.forEach(item => {
        html += `
            <tr>
                <td>${item.timestamp}</td>
                <td>${item.model}</td>
                <td>${item.input.length > 30 ? item.input.substring(0, 30) + '...' : item.input}</td>
                <td>
                    <button class="btn btn-sm btn-outline-primary" onclick="viewHistoryResult(${item.id})">
                        View Result
                    </button>
                </td>
            </tr>
        `;
    });
    
    html += '</tbody></table></div>';
    historyContent.innerHTML = html;
    
    // Use animation function instead of direct DOM manipulation
    showHistorySection();
}

// View history result
function viewHistoryResult(historyId) {
    const historyItem = analysisHistory.find(item => item.id === historyId);
    if (historyItem) {
        const result = {
            success: true,
            result: historyItem.result
        };
        displayResults(result);
        // Use animation function instead of direct DOM manipulation
        showResultSection();
        document.getElementById('resultSection').scrollIntoView({ behavior: 'smooth' });
    }
}

// Clear inputs
function clearInputs() {
    document.getElementById('inputFile').value = '';
    document.getElementById('inputText').value = '';
    const proteinInput = document.getElementById('proteinInputText');
    if (proteinInput) {
        proteinInput.value = '';
    }
    
    // Clear file info using the new logic
    const uploadArea = document.getElementById('fileUploadArea');
    if (uploadArea) {
        const fileInfo = uploadArea.querySelector('.file-info');
        if (fileInfo) {
            fileInfo.style.display = 'none';
        }
        
        const uploadContent = uploadArea.querySelector('.upload-content');
        if (uploadContent) {
            uploadContent.style.display = 'block';
        }
    }
    
    showNotification('Inputs cleared', 'info');
}

// Clear history
function clearHistory() {
    if (confirm('Are you sure you want to clear all history records?')) {
        analysisHistory = [];
        // Return to input section after clearing history
        showInputSection();
        showNotification('History cleared', 'info');
    }
}

// Show/hide loading indicator
function showLoading(show) {
    const loadingOverlay = document.getElementById('loadingOverlay');
    if (loadingOverlay) {
        loadingOverlay.style.display = show ? 'flex' : 'none';
    }
}

// Show notification
function showNotification(message, type = 'info') {
    const container = document.getElementById('notificationContainer');
    
    const notification = document.createElement('div');
    notification.className = `notification ${type}`;
    notification.innerHTML = `
        <div class="d-flex justify-content-between align-items-center">
            <span>${message}</span>
            <button type="button" class="btn-close" onclick="this.parentElement.parentElement.remove()"></button>
        </div>
    `;
    
    container.appendChild(notification);
    
    // Auto-remove after 3 seconds
    setTimeout(() => {
        if (notification.parentNode) {
            notification.remove();
        }
    }, 3000);
}

// Utility functions
function getStatusDisplay(status) {
    const statusMap = {
        'available': 'Available',
        'loading': 'Loading',
        'error': 'Error'
    };
    return statusMap[status] || status;
}

// Update model links (GitHub and Paper)
function updateModelLinks(currentModel) {
    const modelLinks = document.getElementById('modelLinks');
    const githubLink = document.getElementById('githubLink');
    const paperLink = document.getElementById('paperLink');
    
    if (!modelLinks || !githubLink || !paperLink) return;
    
    // Show/hide GitHub link
    if (currentModel.github_url && currentModel.github_url !== 'https://github.com/example/mfold') {
        githubLink.href = currentModel.github_url;
        githubLink.style.display = 'inline-flex';
    } else {
        githubLink.style.display = 'none';
    }
    
    // Show/hide Paper link
    if (currentModel.paper_url && currentModel.paper_url !== 'https://doi.org/10.1000/example') {
        paperLink.href = currentModel.paper_url;
        paperLink.style.display = 'inline-flex';
    } else {
        paperLink.style.display = 'none';
    }
    
    // Show links container if any link is visible
    const hasVisibleLinks = githubLink.style.display !== 'none' || paperLink.style.display !== 'none';
    modelLinks.style.display = hasVisibleLinks ? 'block' : 'none';
}

// Update model architecture
function updateModelArchitecture(currentModel) {
    const modelArchitecture = document.getElementById('modelArchitecture');
    const architectureImage = document.getElementById('architectureImage');
    const architecturePlaceholder = document.getElementById('architecturePlaceholder');
    
    if (!modelArchitecture || !architectureImage || !architecturePlaceholder) return;
    
    // Check if model has valid architecture image
    if (currentModel.architecture_image && 
        currentModel.architecture_image.trim() !== '' &&
        !currentModel.architecture_image.includes('example') &&
        !currentModel.architecture_image.includes('placeholder')) {
        
        // Set image source
        architectureImage.src = currentModel.architecture_image;
        architectureImage.style.display = 'block';
        architecturePlaceholder.style.display = 'none';
        
        // Show architecture section
        modelArchitecture.style.display = 'block';
    } else {
        // Hide entire architecture section when no valid image
        modelArchitecture.style.display = 'none';
    }
}

// Display AlphaFold3 results
function displayAlphaFold3Results(result) {
    if (result.error) {
        return `<div class="alert alert-danger">${result.error}</div>`;
    }
    
    return `
        <div class="result-grid">
            <div class="result-item">
                <h6><i class="fas fa-cube"></i>Structure</h6>
                <div class="result-value">${result.tertiary_structure || 'Generated'}</div>
            </div>
            <div class="result-item">
                <h6><i class="fas fa-chart-line"></i>Confidence</h6>
                <div class="result-value">${(result.confidence_score * 100).toFixed(1)}%</div>
            </div>
            <div class="result-item">
                <h6><i class="fas fa-ruler"></i>RMSD</h6>
                <div class="result-value">${result.structural_metrics?.rmsd || 'N/A'} Å</div>
            </div>
            <div class="result-item">
                <h6><i class="fas fa-star"></i>Quality Score</h6>
                <div class="result-value">${result.quality_score || 'N/A'}</div>
            </div>
            <div class="result-item">
                <h6><i class="fas fa-download"></i>Structure Files</h6>
                <div class="result-value">
                    <a href="#" class="btn btn-sm btn-primary">Download PDB</a>
                    <a href="#" class="btn btn-sm btn-outline-primary">Download CIF</a>
                </div>
            </div>
        </div>
    `;
}

// Display RDesign results
function displayRDesignResults(result) {
    if (result.error) {
        return `<div class="alert alert-danger">${result.error}</div>`;
    }
    
    return `
        <div class="result-grid">
            <div class="result-item">
                <h6><i class="fas fa-dna"></i>Designed Sequence</h6>
                <div class="result-value">${result.designed_sequence || 'N/A'}</div>
            </div>
            <div class="result-item">
                <h6><i class="fas fa-chart-line"></i>Design Quality</h6>
                <div class="result-value">${(result.design_quality * 100).toFixed(1)}%</div>
            </div>
            <div class="result-item">
                <h6><i class="fas fa-cube"></i>Target Structure</h6>
                <div class="result-value">${result.target_structure || 'N/A'}</div>
            </div>
            <div class="result-item">
                <h6><i class="fas fa-check-circle"></i>Sequence Validation</h6>
                <div class="result-value">${result.sequence_validation || 'Passed'}</div>
            </div>
            <div class="result-item">
                <h6><i class="fas fa-download"></i>Output Files</h6>
                <div class="result-value">
                    <a href="#" class="btn btn-sm btn-primary">Download FASTA</a>
                    <a href="#" class="btn btn-sm btn-outline-primary">Download Structure</a>
                </div>
            </div>
        </div>
    `;
}

// Display GRADN results
function displayGRADNResults(result) {
    if (result.error) {
        return `<div class="alert alert-danger">${result.error}</div>`;
    }
    
    return `
        <div class="result-grid">
            <div class="result-item">
                <h6><i class="fas fa-magic"></i>Generated Sequence</h6>
                <div class="result-value">${result.generated_sequence || 'N/A'}</div>
            </div>
            <div class="result-item">
                <h6><i class="fas fa-chart-line"></i>Generation Quality</h6>
                <div class="result-value">${(result.generation_quality * 100).toFixed(1)}%</div>
            </div>
            <div class="result-item">
                <h6><i class="fas fa-random"></i>Diversity Score</h6>
                <div class="result-value">${result.diversity_score || 'N/A'}</div>
            </div>
            <div class="result-item">
                <h6><i class="fas fa-check-circle"></i>Sequence Validity</h6>
                <div class="result-value">${result.sequence_validity || 'Passed'}</div>
            </div>
            <div class="result-item">
                <h6><i class="fas fa-download"></i>Output Files</h6>
                <div class="result-value">
                    <a href="#" class="btn btn-sm btn-primary">Download FASTA</a>
                    <a href="#" class="btn btn-sm btn-outline-primary">Batch Download</a>
                </div>
            </div>
        </div>
    `;
}

// Global functions
window.selectModel = selectModel;
window.runAnalysis = runAnalysis;
window.showHistory = showHistory;
window.viewHistoryResult = viewHistoryResult;
window.clearInputs = clearInputs;
window.clearHistory = clearHistory;
window.toggleTheme = toggleTheme;
window.toggleAIAssistant = toggleAIAssistant;
window.sendAIMessage = sendAIMessage;
window.clearAIChat = clearAIChat;
window.toggleCategoryDropdown = toggleCategoryDropdown;

// AI Assistant Functions
let aiChatHistory = [];
let isAIAssistantOpen = false;

// Toggle AI Assistant sidebar
function toggleAIAssistant() {
    const aiSidebar = document.getElementById('aiSidebar');
    const aiStatusIndicator = document.getElementById('aiStatusIndicator');
    const aiStatusText = document.getElementById('aiStatusText');
    
    if (isAIAssistantOpen) {
        aiSidebar.classList.remove('active');
        isAIAssistantOpen = false;
        // Remove click outside listener
        document.removeEventListener('click', handleClickOutside);
    } else {
        aiSidebar.classList.add('active');
        isAIAssistantOpen = true;
        
        // Check AI service status
        checkAIStatus();
        
        // Focus on input
        setTimeout(() => {
            document.getElementById('aiMessageInput').focus();
        }, 300);
        
        // Add click outside listener
        setTimeout(() => {
            document.addEventListener('click', handleClickOutside);
        }, 100);
    }
}

// Handle clicks outside AI sidebar to close it
function handleClickOutside(event) {
    const aiSidebar = document.getElementById('aiSidebar');
    const aiAssistantToggle = document.getElementById('aiAssistantToggle');
    
    if (isAIAssistantOpen && 
        !aiSidebar.contains(event.target) && 
        !aiAssistantToggle.contains(event.target)) {
        toggleAIAssistant();
    }
}

// Check AI service status
async function checkAIStatus() {
    try {
        // Set connecting state with correct yellow color
        setStatusIndicator('connecting');
        
        const response = await fetch('/api/copilot/status');
        if (response.ok) {
            const data = await response.json();
            if (data.success) {
                // Check if RAG system is building
                if (data.assistant_info && data.assistant_info.rag_system) {
                    const ragSystem = data.assistant_info.rag_system;
                    // Only show building if explicitly marked as building, not just when no documents
                    if (ragSystem.enabled && ragSystem.is_building === true) {
                        setStatusIndicator('building');
                        return;
                    }
                }
                
                // Default to ready state
                setStatusIndicator('ready');
            } else {
                throw new Error(data.message || 'Service unavailable');
            }
        } else {
            throw new Error('Service unavailable');
        }
    } catch (error) {

        setStatusIndicator('error');
    }
}

// Helper function to set status indicator with proper class management
function setStatusIndicator(status) {
    const aiStatusIndicator = document.getElementById('aiStatusIndicator');
    const aiStatusText = document.getElementById('aiStatusText');
    
    if (!aiStatusIndicator || !aiStatusText) {

        return;
    }
    
    // Remove all status classes first
    aiStatusIndicator.classList.remove('connecting', 'error', 'building');
    
    // Add the appropriate class and set text
    switch(status) {
        case 'connecting':
            aiStatusIndicator.classList.add('connecting');
            aiStatusText.textContent = 'Checking...';
            break;
        case 'ready':
            aiStatusText.textContent = 'Ready';
            break;
        case 'building':
            aiStatusIndicator.classList.add('building');
            aiStatusText.textContent = 'Building Vector DB...';
            break;
        case 'error':
            aiStatusIndicator.classList.add('error');
            aiStatusText.textContent = 'Error';
            break;
    }
}

// Send AI message
async function sendAIMessage() {
    const messageInput = document.getElementById('aiMessageInput');
    const message = messageInput.value.trim();
    
    if (!message) return;
    
    // Check if AI is already responding
    if (isAIResponding) {
        // Stop the current response

        stopAIResponse();
        return;
    }

    // Add user message to chat
    addMessageToChat('user', message);
    messageInput.value = '';
    
    // Reset textarea height after clearing
    autoResizeTextarea(messageInput);
    
    // Show typing indicator
    showTypingIndicator();
    
    // Set AI responding state
    isAIResponding = true;
    shouldStopStreaming = false; // Reset stop flag
    updateSendButton();
    
    // Create abort controller for cancellation
    currentAbortController = new AbortController();
    
    try {
        const response = await fetch('/api/copilot/chat', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                message: message,
                context: getCurrentContext(),
                stream: true  // Use streaming for real-time output
            }),
            signal: currentAbortController.signal
        });
        
        if (response.ok) {
            // Remove typing indicator
            removeTypingIndicator();
            
            // Add AI message container for streaming
            const aiMessageDiv = document.createElement('div');
            aiMessageDiv.className = 'ai-message ai-assistant';
            
            const avatar = document.createElement('div');
            avatar.className = 'message-avatar';
            avatar.innerHTML = '<i class="fas fa-robot"></i>';
            
            const messageContent = document.createElement('div');
            messageContent.className = 'message-content';
            
            // Create markdown container for streaming content
            const markdownContainer = document.createElement('div');
            markdownContainer.className = 'markdown-content';
            messageContent.appendChild(markdownContainer);
            
            aiMessageDiv.appendChild(avatar);
            aiMessageDiv.appendChild(messageContent);
            
            const chatMessages = document.getElementById('aiChatMessages');
            chatMessages.appendChild(aiMessageDiv);
            chatMessages.scrollTop = chatMessages.scrollHeight;
            
            // Process streaming response
            const reader = response.body.getReader();
            const decoder = new TextDecoder();
            let fullContent = '';

            // Set up abort listener
            let isAborted = false;
            if (currentAbortController) {
                currentAbortController.signal.addEventListener('abort', () => {

                    isAborted = true;
                    reader.cancel();
                });
            }
            
            while (true) {
                // Check if request was aborted
                if (shouldStopStreaming || isAborted || (currentAbortController && currentAbortController.signal.aborted)) {

                    reader.cancel();
                    break;
                }
                
                // Use Promise.race to handle both reading and aborting
                const readPromise = reader.read();
                const abortPromise = new Promise((resolve) => {
                    if (currentAbortController) {
                        const checkAbort = () => {
                            if (shouldStopStreaming || currentAbortController.signal.aborted || isAborted) {
                                resolve({ aborted: true });
                            }
                        };
                        currentAbortController.signal.addEventListener('abort', checkAbort);
                        // Also check immediately
                        checkAbort();
                    }
                });
                
                const result = await Promise.race([readPromise, abortPromise]);
                
                if (result.aborted || shouldStopStreaming) {

                    reader.cancel();
                    break;
                }
                
                const { done, value } = result;
                
                if (done) {

                    break;
                }
                
                const chunk = decoder.decode(value);

                const lines = chunk.split('\n');
                
                for (const line of lines) {
                    // Check if aborted before processing each line
                    if (isAborted || (currentAbortController && currentAbortController.signal.aborted)) {

                        break;
                    }
                    
                    if (line.startsWith('data: ')) {
                        try {
                            const data = JSON.parse(line.slice(6));

                            if (data.type === 'token') {
                                // Check if aborted before processing token
                                if (isAborted || (currentAbortController && currentAbortController.signal.aborted)) {

                                    break;
                                }
                                
                                // Add character to content and render markdown
                                fullContent += data.content;
                                const renderedMarkdown = marked.parse(fullContent);
                                markdownContainer.innerHTML = renderedMarkdown;
                                
                                // Highlight code blocks
                                if (window.Prism) {
                                    Prism.highlightAllUnder(markdownContainer);
                                }

                                // Scroll to bottom
                                chatMessages.scrollTop = chatMessages.scrollHeight;
                            } else if (data.type === 'complete') {
                                // Streaming complete

                                // Add to history
                                aiChatHistory.push({
                                    sender: 'assistant',
                                    content: fullContent,
                                    timestamp: new Date().toISOString()
                                });
                                return; // Exit the function when complete
                            } else if (data.type === 'error') {
                                throw new Error(data.message);
                            }
                        } catch (e) {

                        }
                    }
                }
            }
        } else {
            throw new Error('Request failed');
        }
    } catch (error) {

        removeTypingIndicator();
        
        // Check if it was aborted by user
        if (error.name === 'AbortError') {
            addMessageToChat('assistant', 'Response stopped by user.');
        } else {
            addMessageToChat('assistant', 'Sorry, I encountered an error. Please try again later.');
        }
    } finally {
        // Reset AI responding state
        isAIResponding = false;
        shouldStopStreaming = false; // Reset stop flag
        updateSendButton();
        currentAbortController = null;
    }
}

// Add message to chat
function addMessageToChat(sender, content) {
    const chatMessages = document.getElementById('aiChatMessages');
    const messageDiv = document.createElement('div');
    messageDiv.className = `ai-message ai-${sender}`;
    
    const avatar = document.createElement('div');
    avatar.className = 'message-avatar';
    
    if (sender === 'user') {
        avatar.innerHTML = '<i class="fas fa-user"></i>';
    } else {
        avatar.innerHTML = '<i class="fas fa-robot"></i>';
    }
    
    const messageContent = document.createElement('div');
    messageContent.className = 'message-content';
    
    if (sender === 'assistant') {
        // For AI assistant, render markdown content immediately
        const renderedMarkdown = marked.parse(content);
        messageContent.innerHTML = `<div class="markdown-content">${renderedMarkdown}</div>`;
        
        // Highlight code blocks
        if (window.Prism) {
            Prism.highlightAllUnder(messageContent);
        }
        
        messageDiv.appendChild(avatar);
        messageDiv.appendChild(messageContent);
        chatMessages.appendChild(messageDiv);
        
        // Scroll to bottom
        chatMessages.scrollTop = chatMessages.scrollHeight;
        
        // Add to history
        aiChatHistory.push({
            sender: sender,
            content: content,
            timestamp: new Date().toISOString()
        });
    } else {
        // For user messages, display immediately
        messageContent.innerHTML = `<p>${content}</p>`;
        
        messageDiv.appendChild(avatar);
        messageDiv.appendChild(messageContent);
        
        if (sender === 'user') {
            messageDiv.style.flexDirection = 'row-reverse';
        }
        
        chatMessages.appendChild(messageDiv);
        
        // Scroll to bottom
        chatMessages.scrollTop = chatMessages.scrollHeight;
        
        // Add to history immediately for user messages
        aiChatHistory.push({
            sender: sender,
            content: content,
            timestamp: new Date().toISOString()
        });
    }
}

// Show typing indicator
function showTypingIndicator() {
    const chatMessages = document.getElementById('aiChatMessages');
    const typingDiv = document.createElement('div');
    typingDiv.className = 'ai-message ai-assistant typing-indicator';
    typingDiv.id = 'typingIndicator';
    
    const avatar = document.createElement('div');
    avatar.className = 'message-avatar';
    avatar.innerHTML = '<i class="fas fa-robot"></i>';
    
    const messageContent = document.createElement('div');
    messageContent.className = 'message-content';
    messageContent.innerHTML = '<p><i class="fas fa-circle"></i><i class="fas fa-circle"></i><i class="fas fa-circle"></i></p>';
    
    typingDiv.appendChild(avatar);
    typingDiv.appendChild(messageContent);
    
    chatMessages.appendChild(typingDiv);
    chatMessages.scrollTop = chatMessages.scrollHeight;
}

// Remove typing indicator
function removeTypingIndicator() {
    const typingIndicator = document.getElementById('typingIndicator');
    if (typingIndicator) {
        typingIndicator.remove();
    }
}

// Get current context for AI
function getCurrentContext() {
    const context = {
        currentModel: currentModel ? currentModel.name : null,
        availableModels: availableModels.map(m => m.name),
        timestamp: new Date().toISOString()
    };
    
    return context;
}

// Clear AI chat
function clearAIChat() {
    const chatMessages = document.getElementById('aiChatMessages');
    
    // Keep only the welcome message
    const welcomeMessage = chatMessages.querySelector('.ai-message.ai-assistant');
    chatMessages.innerHTML = '';
    if (welcomeMessage) {
        chatMessages.appendChild(welcomeMessage);
    }
    
    // Clear history
    aiChatHistory = [];
}

// Handle Enter key in AI input and auto-resize
document.addEventListener('DOMContentLoaded', function() {
    const aiMessageInput = document.getElementById('aiMessageInput');
    if (aiMessageInput) {
        // Auto-resize functionality
        aiMessageInput.addEventListener('input', function() {
            autoResizeTextarea(this);
        });
        
        // Enter key handling
        aiMessageInput.addEventListener('keydown', function(e) {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                sendAIMessage();
            }
        });
        
        // Initialize height
        autoResizeTextarea(aiMessageInput);
    }
});

// Auto-resize textarea function
function autoResizeTextarea(textarea) {
    function adjustHeight() {
        textarea.style.height = 'auto';
        textarea.style.height = textarea.scrollHeight + 'px';
    }
    
    // Initial adjustment
    adjustHeight();
    
    // Adjust on input
    textarea.addEventListener('input', adjustHeight);
    
    // Adjust on paste
    textarea.addEventListener('paste', () => {
        setTimeout(adjustHeight, 10);
    });
}

// Add typing indicator styles
const typingStyles = `
    .typing-indicator .message-content p {
        display: flex;
        align-items: center;
        gap: 4px;
    }
    
    .typing-indicator .message-content i {
        font-size: 8px;
        animation: typing 1.4s infinite ease-in-out;
    }
    
    .typing-indicator .message-content i:nth-child(1) { animation-delay: -0.32s; }
    .typing-indicator .message-content i:nth-child(2) { animation-delay: -0.16s; }
    
    @keyframes typing {
        0%, 80%, 100% { opacity: 0.3; }
        40% { opacity: 1; }
    }
`;

// Inject typing indicator styles
const styleSheet = document.createElement('style');
styleSheet.textContent = typingStyles;
document.head.appendChild(styleSheet);

// Typewriter effect function for AI responses
function typewriterEffect(element, text, onComplete) {
    let index = 0;
    const speed = 30; // Speed in milliseconds per character
    
    function typeNextChar() {
        if (index < text.length) {
            element.textContent += text[index];
            index++;
            
            // Scroll to bottom as text is being typed
            const chatMessages = document.getElementById('aiChatMessages');
            if (chatMessages) {
                chatMessages.scrollTop = chatMessages.scrollHeight;
            }
            
            setTimeout(typeNextChar, speed);
        } else {
            // Typing complete
            if (onComplete && typeof onComplete === 'function') {
                onComplete();
            }
        }
    }
    
    // Start typing
    typeNextChar();
}

// Typewriter effect with Markdown rendering
function typewriterEffectWithMarkdown(element, text, onComplete) {
    let index = 0;
    const speed = 30; // Speed in milliseconds per character
    let currentText = '';
    
    function typeNextChar() {
        if (index < text.length) {
            currentText += text[index];
            index++;
            
            // Render markdown as we type
            try {
                const renderedMarkdown = marked.parse(currentText);
                element.innerHTML = `<div class="markdown-content">${renderedMarkdown}</div>`;
                
                // Highlight code blocks
                if (window.Prism) {
                    Prism.highlightAllUnder(element);
                }
            } catch (error) {
                // Fallback to plain text if markdown parsing fails
                element.textContent = currentText;
            }
            
            // Scroll to bottom as text is being typed
            const chatMessages = document.getElementById('aiChatMessages');
            if (chatMessages) {
                chatMessages.scrollTop = chatMessages.scrollHeight;
            }
            
            setTimeout(typeNextChar, speed);
        } else {
            // Typing complete
            if (onComplete && typeof onComplete === 'function') {
                onComplete();
            }
        }
    }
    
    // Start typing
    typeNextChar();
}

// Category dropdown management
let expandedCategories = new Set();

// Initialize category dropdowns
function initializeCategoryDropdowns() {
    // Check if any category has active models and expand them
    expandedCategories.clear();
    
    // Initially hide all category models
    Object.keys(availableModels.reduce((cats, model) => {
        const category = model.category || 'other';
        cats[category] = true;
        return cats;
    }, {})).forEach(categoryKey => {
        const categoryModels = document.getElementById(`category-models-${categoryKey}`);
        if (categoryModels) {
            categoryModels.style.display = 'none';
            categoryModels.style.maxHeight = '0';
            categoryModels.style.opacity = '0';
            categoryModels.style.transform = 'translateY(-10px)';
        }
    });
    
    // After a short delay, check for active model and expand its category
    setTimeout(() => {
        expandActiveModelCategory();
    }, 100);
}

// Expand the category that contains the active model
function expandActiveModelCategory() {
    if (!currentModel) return;
    
    const activeCategory = currentModel.category || 'other';
    const categoryModels = document.getElementById(`category-models-${activeCategory}`);
    const dropdownIcon = document.getElementById(`dropdown-icon-${activeCategory}`);
    
    if (categoryModels && dropdownIcon) {
        // Expand the category with animation
        categoryModels.style.display = 'block';
        
        // Force reflow to ensure display: block is applied before animation
        categoryModels.offsetHeight;
        
        categoryModels.style.maxHeight = '1000px';
        categoryModels.style.opacity = '1';
        categoryModels.style.transform = 'translateY(0)';
        
        dropdownIcon.classList.remove('fa-chevron-down');
        dropdownIcon.classList.add('fa-chevron-up');
        expandedCategories.add(activeCategory);

    }
}

// Toggle category dropdown
function toggleCategoryDropdown(categoryKey) {
    const categoryModels = document.getElementById(`category-models-${categoryKey}`);
    const dropdownIcon = document.getElementById(`dropdown-icon-${categoryKey}`);
    
    if (!categoryModels || !dropdownIcon) {
        return;
    }
    
    const isExpanded = expandedCategories.has(categoryKey);
    
    if (isExpanded) {
        // Check if this category has an active model
        const hasActiveModel = availableModels.some(model => 
            (model.category || 'other') === categoryKey && 
            model.id === (currentModel ? currentModel.id : null)
        );
        
        if (hasActiveModel) {
            // Don't allow closing if there's an active model
            return;
        }
        
        // Close the dropdown with animation
        categoryModels.style.maxHeight = '0';
        categoryModels.style.opacity = '0';
        categoryModels.style.transform = 'translateY(-10px)';
        
        setTimeout(() => {
            categoryModels.style.display = 'none';
        }, 300);
        
        dropdownIcon.classList.remove('fa-chevron-up');
        dropdownIcon.classList.add('fa-chevron-down');
        expandedCategories.delete(categoryKey);
    } else {
        // Close all other categories first, but keep categories with active models
        expandedCategories.forEach(expandedCategory => {
            if (expandedCategory !== categoryKey) {
                // Check if this category has an active model
                const hasActiveModel = availableModels.some(model => 
                    (model.category || 'other') === expandedCategory && 
                    model.id === (currentModel ? currentModel.id : null)
                );
                
                // Only close if there's no active model in this category
                if (!hasActiveModel) {
                    const otherCategoryModels = document.getElementById(`category-models-${expandedCategory}`);
                    const otherDropdownIcon = document.getElementById(`dropdown-icon-${expandedCategory}`);
                    
                    if (otherCategoryModels && otherDropdownIcon) {
                        otherCategoryModels.style.maxHeight = '0';
                        otherCategoryModels.style.opacity = '0';
                        otherCategoryModels.style.transform = 'translateY(-10px)';
                        
                        setTimeout(() => {
                            otherCategoryModels.style.display = 'none';
                        }, 300);
                        
                        otherDropdownIcon.classList.remove('fa-chevron-up');
                        otherDropdownIcon.classList.add('fa-chevron-down');
                        expandedCategories.delete(expandedCategory);
                    }
                }
            }
        });
        
        // Open this category with animation
        categoryModels.style.display = 'block';
        
        // Force reflow to ensure display: block is applied before animation
        categoryModels.offsetHeight;
        
        categoryModels.style.maxHeight = '1000px';
        categoryModels.style.opacity = '1';
        categoryModels.style.transform = 'translateY(0)';
        
        dropdownIcon.classList.remove('fa-chevron-down');
        dropdownIcon.classList.add('fa-chevron-up');
        expandedCategories.add(categoryKey);
    }
}

// Auto-close other categories when a model is selected
function autoCloseOtherCategories(selectedModelId) {
    const selectedModel = availableModels.find(m => m.id === selectedModelId);
    if (!selectedModel) return;
    
    const selectedCategory = selectedModel.category || 'other';
    
    // Close all other categories with animation, but keep categories with active models
    Object.keys(availableModels.reduce((cats, model) => {
        const category = model.category || 'other';
        cats[category] = true;
        return cats;
    }, {})).forEach(categoryKey => {
        if (categoryKey !== selectedCategory) {
            // Check if this category has an active model
            const hasActiveModel = availableModels.some(model => 
                (model.category || 'other') === categoryKey && 
                model.id === (currentModel ? currentModel.id : null)
            );
            
            // Only close if there's no active model in this category
            if (!hasActiveModel) {
                const categoryModels = document.getElementById(`category-models-${categoryKey}`);
                const dropdownIcon = document.getElementById(`dropdown-icon-${categoryKey}`);
                
                if (categoryModels && dropdownIcon) {
                    categoryModels.style.maxHeight = '0';
                    categoryModels.style.opacity = '0';
                    categoryModels.style.transform = 'translateY(-10px)';
                    
                    setTimeout(() => {
                        categoryModels.style.display = 'none';
                    }, 300);
                    
                    dropdownIcon.classList.remove('fa-chevron-up');
                    dropdownIcon.classList.add('fa-chevron-down');
                    expandedCategories.delete(categoryKey);
                }
            }
        }
    });
    
    // Ensure the selected category is expanded with animation
    if (!expandedCategories.has(selectedCategory)) {
        const categoryModels = document.getElementById(`category-models-${selectedCategory}`);
        const dropdownIcon = document.getElementById(`dropdown-icon-${selectedCategory}`);
        
        if (categoryModels && dropdownIcon) {
            categoryModels.style.display = 'block';
            
            // Force reflow to ensure display: block is applied before animation
            categoryModels.offsetHeight;
            
            categoryModels.style.maxHeight = '1000px';
            categoryModels.style.opacity = '1';
            categoryModels.style.transform = 'translateY(0)';
            
            dropdownIcon.classList.remove('fa-chevron-down');
            dropdownIcon.classList.add('fa-chevron-up');
            expandedCategories.add(selectedCategory);
        }
    }
}

// Utility function to clean up text content
function cleanTextContent(text) {
    if (!text) return '';
    
    // Remove consecutive empty lines (3 or more newlines become 2)
    let cleaned = text.replace(/\n\s*\n\s*\n+/g, '\n\n');
    
    // Remove leading and trailing whitespace
    cleaned = cleaned.trim();
    
    return cleaned;
}

// Utility function to filter empty values from object
function filterEmptyValues(obj) {
    if (!obj || typeof obj !== 'object') {
        return {};
    }
    
    const filtered = {};
    for (const [key, value] of Object.entries(obj)) {
        if (value !== null && value !== undefined && value !== '' && 
            (typeof value !== 'string' || value.trim() !== '')) {
            filtered[key] = value;
        }
    }
    return filtered;
}

// UFold specific functions
async function runUFoldAnalysis(inputFile, inputText) {
    // Get predict_nc option from checkbox (similar to BPFold)
    const ignoreNonCanonical = document.getElementById('ignoreNonCanonical');
    const predictNc = ignoreNonCanonical ? !ignoreNonCanonical.checked : false; // UFold uses opposite logic
    
    if (inputFile) {
        const formData = new FormData();
        formData.append('file', inputFile);
        formData.append('predict_nc', predictNc.toString());
        
        return fetch('/api/ufold/predict/file', {
            method: 'POST',
            body: formData
        });
    } else if (inputText && inputText.trim()) {
        // Convert text input to sequences array
        const sequences = inputText.split('\n').filter(line => line.trim() && !line.startsWith('>'));
        
        if (sequences.length === 0) {
            throw new Error('No valid sequences found in input text');
        }
        
        return fetch('/api/ufold/predict', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                sequences: sequences,
                predict_nc: predictNc
            })
        });
    } else {
        throw new Error('No input data provided');
    }
}

// MXFold2 specific functions
async function runMXFold2Analysis(inputFile, inputText) {
    if (inputFile) {
        const formData = new FormData();
        formData.append('file', inputFile);
        
        return fetch('/api/mxfold2/predict/file', {
            method: 'POST',
            body: formData
        });
    } else if (inputText && inputText.trim()) {
        // Convert text input to sequences array
        const sequences = inputText.split('\n').filter(line => line.trim() && !line.startsWith('>'));
        
        if (sequences.length === 0) {
            throw new Error('No valid sequences found in input text');
        }
        
        return fetch('/api/mxfold2/predict', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                sequences: sequences
            })
        });
    } else {
        throw new Error('No input data provided');
    }
}

function displayUFoldResults(results) {
    if (!results || results.length === 0) {
        return '<div class="alert alert-warning">No results available</div>';
    }
    
    // Store results globally for download functionality
    window.currentUFoldResults = results;
    
    let html = '<div class="ufold-results">';
    
    results.forEach((result, index) => {
        // Get dot-bracket notation from result data
        const dotBracket = result.data || '';
        
        html += `
            <div class="result-item">
                <h6><i class="fas fa-dna"></i>Sequence ${index + 1}</h6>
                <div class="sequence-info">
                    <div class="sequence-text">${result.sequence}</div>
                    <div class="sequence-info-stats">
                        <div class="sequence-length">Length: ${result.sequence.length} nucleotides</div>
                    </div>
                </div>
                <div class="structure-result">
                    <h6><i class="fas fa-project-diagram"></i>Secondary Structure</h6>
                    <div class="structure-display">
                        <pre class="structure-text">${dotBracket ? `Dot-Bracket Notation:\n${dotBracket}` : 'No structure data available'}</pre>
                    </div>
                </div>
            </div>
        `;
    });
    
    html += '</div>';
    
    // Show download button
    const downloadActions = document.getElementById('downloadActions');
    if (downloadActions) {
        downloadActions.style.display = 'flex';
    }
    
    return html;
}

function displayMXFold2Results(results) {
    if (!results || results.length === 0) {
        return '<div class="alert alert-warning">No results available</div>';
    }
    
    // Store results globally for download functionality
    window.currentMXFold2Results = results;
    
    let html = '<div class="mxfold2-results">';
    
    results.forEach((result, index) => {
        // Get dot-bracket notation and energy from result data
        const dotBracket = result.data || '';
        const energy = result.energy || null;
        
        html += `
            <div class="result-item">
                <h6><i class="fas fa-dna"></i>Sequence ${index + 1}</h6>
                <div class="sequence-info">
                    <div class="sequence-text">${result.sequence}</div>
                    <div class="sequence-info-stats">
                        <div class="sequence-length">Length: ${result.sequence.length} nucleotides</div>
                        ${energy !== null ? `<div class="energy-score">Energy: ${energy.toFixed(2)} kcal/mol</div>` : ''}
                    </div>
                </div>
                <div class="structure-result">
                    <h6><i class="fas fa-project-diagram"></i>Secondary Structure</h6>
                    <div class="structure-display">
                        <pre class="structure-text">${dotBracket ? `Dot-Bracket Notation:\n${dotBracket}` : 'No structure data available'}</pre>
                    </div>
                </div>
            </div>
        `;
    });
    
    html += '</div>';
    
    // Show download button
    const downloadActions = document.getElementById('downloadActions');
    if (downloadActions) {
        downloadActions.style.display = 'flex';
    }
    
    return html;
}

// BPFold specific functions
async function runBPFoldAnalysis(inputFile, inputText) {
    // Get ignore_nc option from checkbox
    const ignoreNonCanonical = document.getElementById('ignoreNonCanonical');
    const ignoreNc = ignoreNonCanonical ? ignoreNonCanonical.checked : false;
    
    if (inputFile) {
        const formData = new FormData();
        formData.append('file', inputFile);
        formData.append('output_format', 'csv');
        formData.append('ignore_nc', ignoreNc.toString());
        
        return fetch('/api/bpfold/predict/file', {
            method: 'POST',
            body: formData
        });
    } else if (inputText && inputText.trim()) {
        // Convert text input to sequences array
        const sequences = inputText.split('\n').filter(line => line.trim() && !line.startsWith('>'));
        
        if (sequences.length === 0) {
            throw new Error('No valid sequences found in input text');
        }
        
        return fetch('/api/bpfold/predict', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                sequences: sequences,
                output_format: 'csv',
                ignore_nc: ignoreNc
            })
        });
    } else {
        throw new Error('No input data provided');
    }
}

// Display BPFold results
function displayBPFoldResults(results) {
    if (!results || results.length === 0) {
        return '<div class="alert alert-warning">No results available</div>';
    }
    
    // Store results globally for download functionality
    window.currentBPFoldResults = results;
    
    let html = '<div class="bpfold-results">';
    
    results.forEach((result, index) => {
        // Parse CSV data for better display
        let structureData = result.data;
        let confidence = '';
        let dotBracket = '';
        
        if (result.format === 'csv') {
            // Parse CSV data with proper CSV parsing
            // Simple CSV parser that handles quoted fields
            const parseCSVLine = (line) => {
                const result = [];
                let current = '';
                let inQuotes = false;
                
                for (let i = 0; i < line.length; i++) {
                    const char = line[i];
                    if (char === '"') {
                        inQuotes = !inQuotes;
                    } else if (char === ',' && !inQuotes) {
                        result.push(current.trim());
                        current = '';
                    } else {
                        current += char;
                    }
                }
                result.push(current.trim());
                return result;
            };
            
            const parts = parseCSVLine(result.data);
            
            if (parts.length >= 4) {
                const seqName = parts[0];
                const sequence = parts[1];
                const connects = parts[2];
                confidence = parts[3];
                const connectsNc = parts[4] || '';
                dotBracket = parts[5] || '';
                const dotBracketNc = parts[6] || '';
                const connectsMix = parts[7] || '';
                const dotBracketMix = parts[8] || '';
                
                // Build structure-focused data (exclude sequence and confidence)
                // Only include non-empty fields to avoid empty sections
                const structureSections = [];
                
                // Add Dot-Bracket Notation if available
                if (dotBracket && dotBracket.trim()) {
                    structureSections.push(`Dot-Bracket Notation:\n${dotBracket}`);
                }
                
                // Add Base Pair Connections if available
                if (connects && connects.trim()) {
                    structureSections.push(`Base Pair Connections:\n${connects}`);
                }
                
                // Add Non-Canonical Base Pairs if available
                if (connectsNc && connectsNc.trim() || dotBracketNc && dotBracketNc.trim()) {
                    const ncSections = [];
                    if (connectsNc && connectsNc.trim()) {
                        ncSections.push(`Connections: ${connectsNc}`);
                    }
                    if (dotBracketNc && dotBracketNc.trim()) {
                        ncSections.push(`Notation: ${dotBracketNc}`);
                    }
                    if (ncSections.length > 0) {
                        structureSections.push(`Non-Canonical Base Pairs:\n${ncSections.join('\n')}`);
                    }
                }
                
                // Add Mixed Base Pairs if available
                if (connectsMix && connectsMix.trim() || dotBracketMix && dotBracketMix.trim()) {
                    const mixSections = [];
                    if (connectsMix && connectsMix.trim()) {
                        mixSections.push(`Connections: ${connectsMix}`);
                    }
                    if (dotBracketMix && dotBracketMix.trim()) {
                        mixSections.push(`Notation: ${dotBracketMix}`);
                    }
                    if (mixSections.length > 0) {
                        structureSections.push(`Mixed Base Pairs:\n${mixSections.join('\n')}`);
                    }
                }
                
                // Join sections with proper spacing, avoiding consecutive empty lines
                structureData = structureSections.join('\n\n');
                
                // Clean up any consecutive empty lines using utility function
                structureData = cleanTextContent(structureData);
            } else {
                // Fallback: show raw data if parsing fails
                structureData = `Raw CSV Data:\n${result.data}`;
            }
        }
        
        html += `
            <div class="result-item">
                <h6><i class="fas fa-dna"></i>Sequence ${index + 1}</h6>
                <div class="sequence-info">
                    <div class="sequence-text">${result.sequence}</div>
                    <div class="sequence-info-stats">
                        <div class="sequence-length">Length: ${result.sequence.length} nucleotides</div>
                        ${confidence && confidence.trim() ? `<div class="confidence-score">Confidence: ${confidence}</div>` : ''}
                    </div>
                </div>
                <div class="structure-result">
                    <h6><i class="fas fa-project-diagram"></i>Secondary Structure</h6>
                    <div class="structure-display">
                        <pre class="structure-text">${structureData}</pre>
                    </div>
                </div>
            </div>
        `;
    });
    
    html += '</div>';
    
    // Show download button
    const downloadActions = document.getElementById('downloadActions');
    if (downloadActions) {
        downloadActions.style.display = 'flex';
    }
    
    return html;
}

// Download all results based on current model
function downloadAllResults() {
    if (currentModel) {
        if (currentModel.id === 'bpfold') {
            downloadAllBPFoldResults();
        } else if (currentModel.id === 'ufold') {
            downloadAllUFoldResults();
        } else if (currentModel.id === 'mxfold2') {
            downloadAllMXFold2Results();
        } else if (currentModel.id === 'rnaformer') {
            downloadAllRNAformerResults();
        } else if (currentModel.id === 'rnamigos2') {
            downloadAllRNAmigos2Results();
        } else {
            alert('Download not supported for this model');
        }
    } else {
        alert('No model selected');
    }
}

// Download all RNAmigos2 results
function downloadAllRNAmigos2Results() {
    // Get current results from the global variable
    if (window.currentRNAmigos2Results && window.currentRNAmigos2Results.interactions) {
        const results = window.currentRNAmigos2Results;
        const interactions = results.interactions || [];
        const summary = results.summary || {};
        
        // Create CSV content
        let csvContent = 'Rank,SMILES,Score\n';
        
        interactions.forEach((interaction, index) => {
            const rank = index + 1;
            const smiles = (interaction.smiles || 'N/A').replace(/"/g, '""'); // Escape quotes
            const score = (interaction.score || 0).toFixed(3);
            csvContent += `${rank},"${smiles}",${score}\n`;
        });
        
        // Add summary information as comments at the end
        csvContent += `\n# Summary\n`;
        csvContent += `# Total Ligands,${summary.total_ligands || interactions.length}\n`;
        csvContent += `# Best Score,${(summary.best_score || 0).toFixed(3)}\n`;
        csvContent += `# Average Score,${(summary.average_score || 0).toFixed(3)}\n`;
        csvContent += `# Worst Score,${(summary.worst_score || 0).toFixed(3)}\n`;
        
        // Create and download the file
        const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = 'rnamigos2_results.csv';
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        window.URL.revokeObjectURL(url);
        
        showNotification('CSV file downloaded successfully!', 'success');
    } else {
        showNotification('No results available for download', 'warning');
    }
}

// Download all RNAformer results
async function downloadAllRNAformerResults() {
    // Get current results from the global variable
    if (window.currentRNAformerResults && window.currentRNAformerResults.length > 0) {
        try {
            showNotification('Generating CT files...', 'info');
            
            const results = window.currentRNAformerResults;
            
            // Send results to backend for CT file generation
            const response = await fetch('/api/rnaformer/download_ct', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ results: results })
            });
            
            if (response.ok) {
                // Get the file from response
                const blob = await response.blob();
                const url = window.URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.href = url;
                
                // Set filename based on number of sequences
                if (results.length > 1) {
                    a.download = 'rnaformer_structures.zip';
                } else {
                    a.download = `rnaformer_structure_${results[0].length}bp.ct`;
                }
                
                document.body.appendChild(a);
                a.click();
                document.body.removeChild(a);
                window.URL.revokeObjectURL(url);
                
                showNotification('CT files downloaded successfully!', 'success');
            } else {
                const errorData = await response.json();
                throw new Error(errorData.error || 'Download failed');
            }
        } catch (error) {
            console.error('Download error:', error);
            showNotification(`Download failed: ${error.message}`, 'error');
        }
    } else {
        showNotification('No results available for download', 'warning');
    }
}

// Download all UFold results
function downloadAllUFoldResults() {
    // Get current results from the global variable
    if (window.currentUFoldResults && window.currentUFoldResults.length > 0) {
        const results = window.currentUFoldResults;
        
        // Create download data
        const downloadData = {
            results: results,
            format: 'ct'
        };
        
        // Call download API
        fetch('/api/ufold/download/ct', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(downloadData)
        })
        .then(response => {
            if (response.ok) {
                return response.blob();
            } else {
                throw new Error('Download failed');
            }
        })
        .then(blob => {
            // Create download link
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = 'ufold_results.ct';
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            window.URL.revokeObjectURL(url);
        })
        .catch(error => {

            alert('Download failed: ' + error.message);
        });
    } else {
        alert('No results available for download');
    }
}

async function downloadAllMXFold2Results() {
    // Get current results from the global variable
    if (window.currentMXFold2Results && window.currentMXFold2Results.length > 0) {
        try {
            showNotification('Generating CT files...', 'info');
            
            const results = window.currentMXFold2Results;
            
            // Send results to backend for CT file generation
            const response = await fetch('/api/mxfold2/download_ct', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ results: results })
            });
            
            if (response.ok) {
                // Get the file from response
                const blob = await response.blob();
                const url = window.URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.href = url;
                
                // Set filename based on number of sequences
                if (results.length > 1) {
                    a.download = 'mxfold2_structures.zip';
                } else {
                    a.download = `mxfold2_structure_${results[0].sequence.length}bp.ct`;
                }
                
                document.body.appendChild(a);
                a.click();
                document.body.removeChild(a);
                window.URL.revokeObjectURL(url);
                
                showNotification('CT files downloaded successfully!', 'success');
            } else {
                const errorData = await response.json();
                throw new Error(errorData.error || 'Download failed');
            }
        } catch (error) {
            console.error('Download error:', error);
            showNotification(`Download failed: ${error.message}`, 'error');
        }
    } else {
        showNotification('No results available for download', 'warning');
    }
}

function downloadAllBPFoldResults() {
    // Get current results from the global variable
    if (window.currentBPFoldResults && window.currentBPFoldResults.length > 0) {
        const results = window.currentBPFoldResults;
        
        // Create download data
        const downloadData = {
            results: results,
            format: 'ct'
        };
        
        // Call download API
        fetch('/api/bpfold/download/ct', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(downloadData)
        })
        .then(response => {
            if (response.ok) {
                return response.blob();
            }
            throw new Error('Download failed');
        })
        .then(blob => {
            // Create download link
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.style.display = 'none';
            a.href = url;
            a.download = `bpfold_results.ct`;
            document.body.appendChild(a);
            a.click();
            window.URL.revokeObjectURL(url);
            document.body.removeChild(a);
            
            showNotification('CT file downloaded successfully!', 'success');
        })
        .catch(error => {

            showNotification('Download failed: ' + error.message, 'error');
        });
    } else {
        showNotification('No results available for download', 'warning');
    }
}

// BPFold model setup
async function setupBPFold() {
    try {
        showLoading(true);
        const response = await fetch('/api/bpfold/setup', {
            method: 'POST'
        });
        
        const result = await response.json();
        
        if (result.success) {
            showNotification('BPFold model setup completed!', 'success');
        } else {
            showNotification(`BPFold setup failed: ${result.error}`, 'error');
        }
    } catch (error) {

        showNotification(`BPFold setup failed: ${error.message}`, 'error');
    } finally {
        showLoading(false);
    }
}

// Check BPFold status
async function checkBPFoldStatus() {
    try {
        const response = await fetch('/api/bpfold/status');
        const result = await response.json();
        
        if (result.success) {
            return result.status === 'ready';
        }
        return false;
    } catch (error) {

        return false;
    }
}

function setupFileUpload(fileInput, uploadArea, fileInfo) {
    // Click to upload
    uploadArea.addEventListener('click', () => {
        fileInput.click();
    });
    
    // File selection
    fileInput.addEventListener('change', (e) => {
        const file = e.target.files[0];
        if (file) {
            displayFileInfo(file, fileInfo);
        }
    });
    
    // Drag and drop
    uploadArea.addEventListener('dragover', (e) => {
        e.preventDefault();
        uploadArea.classList.add('dragover');
    });
    
    uploadArea.addEventListener('dragleave', () => {
        uploadArea.classList.remove('dragover');
    });
    
    uploadArea.addEventListener('drop', (e) => {
        e.preventDefault();
        uploadArea.classList.remove('dragover');
        
        const files = e.dataTransfer.files;
        if (files.length > 0) {
            const file = files[0];
            // Check file type
            const allowedTypes = ['.fasta', '.fa', '.txt'];
            const fileExtension = '.' + file.name.split('.').pop().toLowerCase();
            
            if (allowedTypes.includes(fileExtension)) {
                fileInput.files = files;
                displayFileInfo(file, fileInfo);
            } else {
                showNotification('Please upload a FASTA or TXT file', 'warning');
            }
        }
    });
}


// Remove file
function removeFile(button) {
    const fileInfo = button.closest('.file-info');
    const fileInput = fileInfo.previousElementSibling.querySelector('input[type="file"]');
    
    if (fileInput) {
        fileInput.value = '';
    }
    
    fileInfo.style.display = 'none';
    fileInfo.innerHTML = '';
}

// RNAmigos2 Analysis Functions
async function runRNAmigos2Analysis() {
    // Get input data
    const cifFileInput = document.getElementById('rnamigos2FileInput');
    const residuesElement = document.getElementById('rnamigos2Residues');
    const smilesFileInput = document.getElementById('rnamigos2SmilesFileInput');
    const smilesTextElement = document.getElementById('rnamigos2SmilesText');
    
    // Validate inputs
    if (!cifFileInput || !residuesElement || !smilesFileInput || !smilesTextElement) {
        throw new Error('RNAmigos2 input elements not found. Please refresh the page and try again.');
    }
    
    const cifFile = cifFileInput.files[0];
    const residuesText = residuesElement.value.trim();
    const smilesFile = smilesFileInput.files[0];
    const smilesText = smilesTextElement.value.trim();
    
    // Validate inputs
    if (!cifFile) {
        throw new Error('Please provide a CIF or mmCIF file');
    }
    
    if (!smilesFile && !smilesText) {
        throw new Error('Please provide either a SMILES file or paste SMILES strings');
    }
    
    if (!residuesText) {
        throw new Error('Please provide binding site residues');
    }
    
    // Prepare data
    const cifContent = await readFileAsText(cifFile);
    let smilesList = [];
    
    if (smilesFile) {
        const smilesContent = await readFileAsText(smilesFile);
        smilesList = smilesContent.split('\n').filter(line => line.trim());
    } else {
        smilesList = smilesText.split('\n').filter(line => line.trim());
    }
    
    const residueList = parseResidues(residuesText);
    
    // Prepare request data
    const requestData = {
        cif_content: cifContent,
        residue_list: residueList,
        smiles_list: smilesList
    };
    
    // Send request
    const response = await fetch('/api/rnamigos2/predict', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify(requestData)
    });
    
    return response;
}

// Run RNAformer analysis
async function runRNAformerAnalysis(inputFile, inputText) {
    // Prepare sequences
    let sequences = [];
    
    if (inputFile) {
        const content = await readFileAsText(inputFile);
        sequences = parseFastaFile(content);
    } else {
        // Split by newlines and filter empty lines
        sequences = inputText.split('\n').filter(line => line.trim());
    }
    
    if (sequences.length === 0) {
        throw new Error('No valid RNA sequences found');
    }
    
    // Prepare request data
    const requestData = {
        sequences: sequences
    };
    
    // Send request
    const response = await fetch('/api/rnaformer/predict', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify(requestData)
    });
    
    return response;
}

// Parse FASTA file content
function parseFastaFile(content) {
    const sequences = [];
    let currentSequence = '';
    
    for (const line of content.split('\n')) {
        const trimmedLine = line.trim();
        if (trimmedLine.startsWith('>')) {
            // Header line
            if (currentSequence) {
                sequences.push(currentSequence);
                currentSequence = '';
            }
        } else if (trimmedLine) {
            // Sequence line
            currentSequence += trimmedLine;
        }
    }
    
    // Add last sequence
    if (currentSequence) {
        sequences.push(currentSequence);
    }
    
    return sequences;
}

// Parse residue identifiers from text input
function parseResidues(residuesText) {
    const residues = [];
    const lines = residuesText.split('\n');
    
    for (const line of lines) {
        const trimmedLine = line.trim();
        if (trimmedLine) {
            // Split by comma if present
            const parts = trimmedLine.split(',');
            for (const part of parts) {
                const residue = part.trim();
                if (residue) {
                    residues.push(residue);
                }
            }
        }
    }
    
    return residues;
}

// Read file as text
function readFileAsText(file) {
    return new Promise((resolve, reject) => {
        const reader = new FileReader();
        reader.onload = (e) => resolve(e.target.result);
        reader.onerror = (e) => reject(e);
        reader.readAsText(file);
    });
}

// Initialize RNAmigos2 file uploads
function initializeRNAmigos2FileUploads() {
    // CIF file upload
    const cifFileUpload = document.getElementById('rnamigos2FileUpload');
    const cifFileInput = document.getElementById('rnamigos2FileInput');
    
    if (cifFileUpload && cifFileInput) {
        cifFileUpload.addEventListener('click', () => cifFileInput.click());
        cifFileInput.addEventListener('change', (e) => {
            if (e.target.files.length > 0) {
                displayRNAmigos2FileInfo(e.target.files[0], 'cif');
            }
        });
        
        // Drag and drop for CIF files
        cifFileUpload.addEventListener('dragover', (e) => {
            e.preventDefault();
            cifFileUpload.classList.add('dragover');
        });
        
        cifFileUpload.addEventListener('dragleave', () => {
            cifFileUpload.classList.remove('dragover');
        });
        
        cifFileUpload.addEventListener('drop', (e) => {
            e.preventDefault();
            cifFileUpload.classList.remove('dragover');
            
            const files = e.dataTransfer.files;
            if (files.length > 0) {
                const file = files[0];
                // Check if it's a CIF file
                const fileName = file.name.toLowerCase();
                if (fileName.endsWith('.cif') || fileName.endsWith('.mmcif')) {
                    cifFileInput.files = files;
                    displayRNAmigos2FileInfo(file, 'cif');
                } else {
                    showNotification('Please upload a CIF or mmCIF file', 'warning');
                }
            }
        });
    }
    
    // SMILES file upload
    const smilesFileUpload = document.getElementById('rnamigos2SmilesFileUpload');
    const smilesFileInput = document.getElementById('rnamigos2SmilesFileInput');
    
    if (smilesFileUpload && smilesFileInput) {
        smilesFileUpload.addEventListener('click', () => smilesFileInput.click());
        smilesFileInput.addEventListener('change', (e) => {
            if (e.target.files.length > 0) {
                displayRNAmigos2FileInfo(e.target.files[0], 'smiles');
            }
        });
        
        // Drag and drop for SMILES files
        smilesFileUpload.addEventListener('dragover', (e) => {
            e.preventDefault();
            smilesFileUpload.classList.add('dragover');
        });
        
        smilesFileUpload.addEventListener('dragleave', () => {
            smilesFileUpload.classList.remove('dragover');
        });
        
        smilesFileUpload.addEventListener('drop', (e) => {
            e.preventDefault();
            smilesFileUpload.classList.remove('dragover');
            
            const files = e.dataTransfer.files;
            if (files.length > 0) {
                const file = files[0];
                // Check if it's a text file
                const fileName = file.name.toLowerCase();
                if (fileName.endsWith('.txt')) {
                    smilesFileInput.files = files;
                    displayRNAmigos2FileInfo(file, 'smiles');
                } else {
                    showNotification('Please upload a TXT file', 'warning');
                }
            }
        });
    }
    
    // Auto-resize textareas
    const residuesTextarea = document.getElementById('rnamigos2Residues');
    const smilesTextarea = document.getElementById('rnamigos2SmilesText');
    
    if (residuesTextarea) {
        autoResizeTextarea(residuesTextarea);
    }
    
    if (smilesTextarea) {
        autoResizeTextarea(smilesTextarea);
    }
}

// Display RNAmigos2 file information
function displayRNAmigos2FileInfo(file, type) {
    const fileSize = formatFileSize(file.size);
    const fileExtension = file.name.split('.').pop().toLowerCase();
    
    let container;
    if (type === 'cif') {
        container = document.getElementById('rnamigos2FileUpload');
    } else if (type === 'smiles') {
        container = document.getElementById('rnamigos2SmilesFileUpload');
    }
    
    if (container) {
        // Hide the upload content and show file info
        const uploadContent = container.querySelector('.upload-content');
        if (uploadContent) {
            uploadContent.style.display = 'none';
        }
        
        // Create or update file info display
        let fileInfo = container.querySelector('.file-info');
        if (!fileInfo) {
            fileInfo = document.createElement('div');
            fileInfo.className = 'file-info';
            container.appendChild(fileInfo);
        }
        
        fileInfo.innerHTML = `
            <div class="file-info-content">
                <i class="fas fa-file-${fileExtension === 'txt' ? 'alt' : 'code'}"></i>
                <div class="file-details">
                    <div class="file-name">${file.name}</div>
                    <div class="file-size">${fileSize}</div>
                </div>
                <button class="btn-remove-file" onclick="removeRNAmigos2File('${type}')">
                    <i class="fas fa-times"></i>
                </button>
            </div>
        `;
        fileInfo.style.display = 'block';
    }
}

// Remove RNAmigos2 file
function removeRNAmigos2File(type) {
    let fileInput, container;
    
    if (type === 'cif') {
        fileInput = document.getElementById('rnamigos2FileInput');
        container = document.getElementById('rnamigos2FileUpload');
    } else if (type === 'smiles') {
        fileInput = document.getElementById('rnamigos2SmilesFileInput');
        container = document.getElementById('rnamigos2SmilesFileUpload');
    }
    
    if (fileInput) {
        fileInput.value = '';
    }
    
    if (container) {
        // Hide file info and show upload content
        const fileInfo = container.querySelector('.file-info');
        if (fileInfo) {
            fileInfo.style.display = 'none';
        }
        
        const uploadContent = container.querySelector('.upload-content');
        if (uploadContent) {
            uploadContent.style.display = 'block';
        }
    }
}
