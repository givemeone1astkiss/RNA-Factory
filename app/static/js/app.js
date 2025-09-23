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
    
    // Reset scroll position to top on page load/refresh
    window.scrollTo(0, 0);
});

// Show loading page with simplified animation
function showLoadingPage() {
    const loadingPage = document.getElementById('loadingPage');
    
    // Disable body scrolling when loading page is shown
    document.body.classList.add('loading');
    
    // Simple loading animation with random duration
    const minDuration = 2000; // Minimum 2 seconds
    const maxDuration = 4000; // Maximum 4 seconds
    const duration = Math.random() * (maxDuration - minDuration) + minDuration;
    
    setTimeout(() => {
        loadingPage.classList.add('fade-out');
        setTimeout(() => {
            loadingPage.style.display = 'none';
            // Re-enable body scrolling when loading page is hidden
            document.body.classList.remove('loading');
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
        // All file uploads now handled by standard-input-area
        
        // Initialize general input area height synchronization
        // Height management now handled by standard-input-area
        
        // Initialize standard input areas (only for visible elements)
        setTimeout(() => {
            // Structure Prediction RNA Sequences (always visible) - single block mode
            initializeSingleBlockInput('rnaSequencesUnifiedInput', 'inputText', 'inputFile', 'rnaSequencesPlaceholder');
        }, 500);
    } catch (error) {
        showNotification('Application initialization failed', 'error');
    }
}

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
        // Load models from API
        const response = await fetch('/api/models');
        
        if (!response.ok) {
            throw new Error(`Failed to load models from API: ${response.status} ${response.statusText}`);
        }
        
        const data = await response.json();
        if (!data.success || !data.models) {
            throw new Error('Invalid response format from API');
        }
        
        availableModels = data.models;

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
    
}

// Clear input areas when switching models
function clearInputAreas() {
    // inputText and inputFile are now handled by resetAllStandardInputAreas
    
    // rnaSequencesFileUpload area is now handled by resetAllStandardInputAreas
    
    // Clear RNAmigos2 specific inputs (non-standard-input-area elements only)
    const rnamigos2Input = document.getElementById('rnamigos2Input');
    if (rnamigos2Input) {
        // Note: rnamigos2Residues now uses standard-input-area single-block mode
        // It will be handled by resetAllStandardInputAreas()
    }
    
    
    // Clear Mol2Aptamer specific inputs (parameters only, input areas handled by standard-input-area)
    const mol2aptamerInput = document.getElementById('mol2aptamerInput');
    if (mol2aptamerInput) {
        // Reset parameters to default values
        document.getElementById('mol2aptamerNumSequences').value = '10';
        document.getElementById('mol2aptamerMaxLength').value = '50';
        document.getElementById('mol2aptamerTemperature').value = '1.0';
        document.getElementById('mol2aptamerTopK').value = '50';
        document.getElementById('mol2aptamerTopP').value = '0.9';
        document.getElementById('mol2aptamerStrategy').value = 'greedy';
    }
    
    // Clear RNAFlow specific inputs (parameters only, input areas handled by standard-input-area)
    const rnaflowInput = document.getElementById('rnaflowInput');
    if (rnaflowInput) {
        // Reset parameters to default values
        document.getElementById('rnaflowRnaLength').value = '20';
        document.getElementById('rnaflowNumSamples').value = '3';
    }
    
    // Clear Reformer specific inputs (parameters only, input areas handled by standard-input-area)
    const reformerInput = document.getElementById('reformerInput');
    if (reformerInput) {
        // Reset parameters to default values
        document.getElementById('reformerRbpName').value = 'U2AF2';
        document.getElementById('reformerCellLine').value = 'HepG2';
    }
    
    // Clear CoPRA specific inputs (parameters only, input areas handled by standard-input-area)
    const copraInput = document.getElementById('copraInput');
    if (copraInput) {
        // Reset parameters to default values
        document.getElementById('copraConfidenceThreshold').value = '0.7';
    }
    
    // Clear RiboDiffusion specific inputs (parameters only, input areas handled by standard-input-area)
    const ribodiffusionInput = document.getElementById('ribodiffusionInput');
    if (ribodiffusionInput) {
        // Reset parameters to default values
        document.getElementById('ribodiffusionNumSamples').value = '1';
        document.getElementById('ribodiffusionSamplingSteps').value = '50';
        document.getElementById('ribodiffusionCondScale').value = '-1.0';
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
    
    // Reset all standard-input-area components
    resetAllStandardInputAreas();
}

// Clear temp folder for RNA-FrameFlow when switching models
function clearTempFolder() {
    // Send request to clear temp folder
    fetch('/api/rnaframeflow/clear-temp', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        }
    })
    .then(response => {
        if (response.ok) {
            console.log('Temp folder cleared successfully');
        } else {
            console.warn('Failed to clear temp folder:', response.status);
        }
    })
    .catch(error => {
        console.warn('Error clearing temp folder:', error);
    });
}

// Reset all standard-input-area components to initial state
function resetAllStandardInputAreas() {
    // Reset RNAmigos2 CIF file upload (now uses standard single block mode)
    const rnamigos2FileUpload = document.getElementById('rnamigos2FileUpload');
    const rnamigos2FileInput = document.getElementById('rnamigos2FileInput');
    const rnamigos2CifContent = document.getElementById('rnamigos2CifContent');
    const rnamigos2Placeholder = document.getElementById('rnamigos2Placeholder');
    
    if (rnamigos2FileUpload && rnamigos2FileInput && rnamigos2CifContent && rnamigos2Placeholder) {
        // Clear file input
        rnamigos2FileInput.value = '';
        
        // Clear textarea
        rnamigos2CifContent.value = '';
        rnamigos2CifContent.style.display = 'none';
        
        // Show placeholder
        rnamigos2Placeholder.style.display = 'flex';
        
        // Clear stored file content
        rnamigos2FileUpload.removeAttribute('data-file-content');
        
        // Remove file info
        const fileInfo = rnamigos2FileUpload.querySelector('.file-info-content');
        if (fileInfo) {
            fileInfo.style.display = 'none';
        }
    }
    
    // Reset RiboDiffusion PDB file upload (now uses standard single block mode)
    const ribodiffusionPdbInputArea = document.getElementById('ribodiffusionPdbInputArea');
    const ribodiffusionPdbFileInput = document.getElementById('ribodiffusionPdbFileInput');
    const ribodiffusionPdbContent = document.getElementById('ribodiffusionPdbContent');
    const ribodiffusionPdbPlaceholder = document.getElementById('ribodiffusionPdbPlaceholder');
    
    if (ribodiffusionPdbInputArea && ribodiffusionPdbFileInput && ribodiffusionPdbContent && ribodiffusionPdbPlaceholder) {
        // Clear file input
        ribodiffusionPdbFileInput.value = '';
        
        // Clear textarea
        ribodiffusionPdbContent.value = '';
        ribodiffusionPdbContent.style.display = 'none';
        
        // Show placeholder
        ribodiffusionPdbPlaceholder.style.display = 'flex';
        
        // Clear stored file content
        ribodiffusionPdbInputArea.removeAttribute('data-file-content');
        
        // Remove file info
        const fileInfo = ribodiffusionPdbInputArea.querySelector('.file-info-content');
        if (fileInfo) {
            fileInfo.style.display = 'none';
        }
    }
    
    // Reset single block input areas
    const singleBlockAreas = document.querySelectorAll('.standard-input-area.single-block');
    singleBlockAreas.forEach(area => {
        const unifiedInput = area.querySelector('.unified-input-area');
        const textarea = area.querySelector('textarea');
        const fileInput = area.querySelector('input[type="file"]');
        const placeholder = area.querySelector('.input-placeholder');
        
        if (unifiedInput && textarea && fileInput && placeholder) {
            // Clear file input
            fileInput.value = '';
            
            // Clear stored file content
            unifiedInput.removeAttribute('data-file-content');
            
            // Remove file info
            const fileInfo = unifiedInput.querySelector('.file-info-content');
            if (fileInfo) {
                fileInfo.remove();
            }
            
            // Show placeholder
            placeholder.style.display = 'block';
            
            // Hide textarea
            textarea.style.display = 'none';
            textarea.value = '';
            
            // Re-initialize the single block input area
            const unifiedInputId = unifiedInput.id;
            const textareaId = textarea.id;
            const fileInputId = fileInput.id;
            const placeholderId = placeholder.id;
            
            setTimeout(() => {
                initializeSingleBlockInput(unifiedInputId, textareaId, fileInputId, placeholderId);
            }, 50);
        }
    });
    
    // Reset traditional standard-input-area containers (if any remain)
    const standardInputAreas = document.querySelectorAll('.standard-input-area:not(.single-block)');
    standardInputAreas.forEach(area => {
        const fileUpload = area.querySelector('.file-upload-area');
        const textarea = area.querySelector('textarea');
        const fileInput = area.querySelector('input[type="file"]');
        
        if (fileUpload && textarea && fileInput) {
            // Reset file input
            fileInput.value = '';
            
            // Hide file info and show input placeholder
            const fileInfo = fileUpload.querySelector('.file-info-content');
            if (fileInfo) {
                fileInfo.style.display = 'none';
            }
            
            const inputPlaceholder = fileUpload.querySelector('.input-placeholder');
            if (inputPlaceholder) {
                inputPlaceholder.style.display = 'flex';
            }
            
            // Clear stored file content
            fileUpload.removeAttribute('data-file-content');
            
            // Reset textarea
            textarea.value = '';
            textarea.disabled = false;
            textarea.style.cursor = '';
            textarea.style.opacity = '';
            
            // Reset placeholder
            const originalPlaceholder = textarea.getAttribute('data-original-placeholder');
            if (originalPlaceholder) {
                textarea.placeholder = originalPlaceholder;
            }
            
            // Reset file upload area state
            fileUpload.style.pointerEvents = '';
            fileUpload.style.opacity = '';
            fileUpload.style.cursor = '';
            fileUpload.removeAttribute('data-disabled');
            
            // Re-initialize the standard input area after reset
            const containerId = area.id;
            const textareaId = textarea.id;
            const fileInputId = fileInput.id;
            const fileUploadId = fileUpload.id;
            
            // Note: Traditional standard-input-area re-initialization removed
            // All input areas now use single-block mode
        }
    });
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
    
    // Clear temp folder for RNA-FrameFlow when switching models
    clearTempFolder();
    
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
    const mol2aptamerInput = document.getElementById('mol2aptamerInput');
    const rnaflowInput = document.getElementById('rnaflowInput');
    const rnaframeflowInput = document.getElementById('rnaframeflowInput');
    const reformerInput = document.getElementById('reformerInput');
    const copraInput = document.getElementById('copraInput');
    const ribodiffusionInput = document.getElementById('ribodiffusionInput');
    const fileAcceptInfo = document.getElementById('fileAcceptInfo');
    
    // Get general input areas by ID
    const rnaSequencesInput = document.getElementById('rnaSequencesInput');
    
    if (!fileAcceptInfo) return;
    
    // Hide all model-specific inputs first
    if (bpfoldOptions) bpfoldOptions.style.display = 'none';
    if (rnamigos2Input) rnamigos2Input.style.display = 'none';
    if (mol2aptamerInput) mol2aptamerInput.style.display = 'none';
    if (rnaflowInput) rnaflowInput.style.display = 'none';
    if (rnaframeflowInput) rnaframeflowInput.style.display = 'none';
    if (reformerInput) reformerInput.style.display = 'none';
    if (copraInput) copraInput.style.display = 'none';
    if (ribodiffusionInput) ribodiffusionInput.style.display = 'none';
    
    // Show general input areas by default
    if (rnaSequencesInput) rnaSequencesInput.style.display = 'flex';
    
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
        if (rnaSequencesInput) rnaSequencesInput.style.display = 'none';
        fileAcceptInfo.textContent = 'Supports mmCIF, SMILES formats';
        
        // Initialize RNAmigos2 input areas when model is selected
        setTimeout(() => {
            // CIF file input area (now uses single block mode)
            initializeSingleBlockInput('rnamigos2UnifiedInput', 'rnamigos2CifContent', 'rnamigos2FileInput', 'rnamigos2Placeholder');
            
            // SMILES input area (uses single block mode)
            initializeSingleBlockInput('rnamigos2SmilesUnifiedInput', 'rnamigos2SmilesText', 'rnamigos2SmilesFileInput', 'rnamigos2SmilesPlaceholder');
            
            // Binding Site Residues input area (uses single block mode)
            initializeSingleBlockInput('rnamigos2ResiduesUnifiedInput', 'rnamigos2Residues', 'rnamigos2ResiduesFileInput', 'rnamigos2ResiduesPlaceholder');
        }, 100);
    } else if (currentModel.id === 'rnaformer') {
        // RNAformer model uses general input interface (same as MXFold2)
        fileAcceptInfo.textContent = 'Supports FASTA, TXT formats';
    } else if (currentModel.id === 'mol2aptamer') {
        // Mol2Aptamer model has specific input interface
        if (mol2aptamerInput) mol2aptamerInput.style.display = 'flex';
        // Hide general input areas for Mol2Aptamer
        if (rnaSequencesInput) rnaSequencesInput.style.display = 'none';
        fileAcceptInfo.textContent = 'Supports SMILES format';
        
        // Initialize Mol2Aptamer single block input area when model is selected
        setTimeout(() => {
            initializeSingleBlockInput('mol2aptamerSmilesUnifiedInput', 'mol2aptamerSmiles', 'mol2aptamerSmilesFileInput', 'mol2aptamerSmilesPlaceholder');
        }, 100);
    } else if (currentModel.id === 'rnaflow') {
        // RNAFlow model has specific input interface
        if (rnaflowInput) {
            rnaflowInput.style.display = 'flex';
        }
        // Hide general input areas for RNAFlow
        if (rnaSequencesInput) rnaSequencesInput.style.display = 'none';
        fileAcceptInfo.textContent = 'Supports protein sequence input and RNA design parameters';
        
        // Initialize RNAFlow single block input area when model is selected
        setTimeout(() => {
            initializeSingleBlockInput('rnaflowProteinUnifiedInput', 'rnaflowProteinSequence', 'rnaflowProteinFileInput', 'rnaflowProteinPlaceholder');
        }, 100);
    } else if (currentModel.id === 'rnaframeflow') {
        // RNA-FrameFlow model has specific input interface
        const rnaframeflowInput = document.getElementById('rnaframeflowInput');
        if (rnaframeflowInput) {
            rnaframeflowInput.style.display = 'flex';
        }
        // Hide general input areas for RNA-FrameFlow
        if (rnaSequencesInput) rnaSequencesInput.style.display = 'none';
        fileAcceptInfo.textContent = 'Supports parameter input';
    } else if (currentModel.id === 'reformer') {
        // Reformer model has specific input interface
        if (reformerInput) {
            reformerInput.style.display = 'flex';
        }
        // Hide general input areas for Reformer
        if (rnaSequencesInput) rnaSequencesInput.style.display = 'none';
        fileAcceptInfo.textContent = 'Supports RNA sequence input and RBP prediction parameters';
        
        // Initialize Reformer single block input area when model is selected
        setTimeout(() => {
            initializeSingleBlockInput('reformerSequenceUnifiedInput', 'reformerSequence', 'reformerSequenceFileInput', 'reformerSequencePlaceholder');
            
            // Add event listener for RBP selection change
            const rbpSelect = document.getElementById('reformerRbpName');
            if (rbpSelect) {
                rbpSelect.addEventListener('change', updateReformerCellLineOptions);
                // Initialize cell line options
                updateReformerCellLineOptions();
            }
        }, 100);
    } else if (currentModel.id === 'copra') {
        // CoPRA model has specific input interface
        if (copraInput) {
            copraInput.style.display = 'flex';
        }
        // Hide general input areas for CoPRA
        if (rnaSequencesInput) rnaSequencesInput.style.display = 'none';
        fileAcceptInfo.textContent = 'Supports protein and RNA sequence input';
        
        // Initialize CoPRA single block input areas when model is selected
        setTimeout(() => {
            initializeSingleBlockInput('copraProteinUnifiedInput', 'copraProteinSequence', 'copraProteinFileInput', 'copraProteinPlaceholder');
            initializeSingleBlockInput('copraRnaUnifiedInput', 'copraRnaSequence', 'copraRnaFileInput', 'copraRnaPlaceholder');
        }, 100);
    } else if (currentModel.id === 'ribodiffusion') {
        // RiboDiffusion model has specific input interface
        if (ribodiffusionInput) {
            ribodiffusionInput.style.display = 'flex';
        }
        // Hide general input areas for RiboDiffusion
        if (rnaSequencesInput) rnaSequencesInput.style.display = 'none';
        fileAcceptInfo.textContent = 'Supports PDB format';
        
        // Initialize RiboDiffusion single block input areas when model is selected
        setTimeout(() => {
            initializeSingleBlockInput('ribodiffusionPdbUnifiedInput', 'ribodiffusionPdbContent', 'ribodiffusionPdbFileInput', 'ribodiffusionPdbPlaceholder');
        }, 100);
    } else {
        // Other models (BPFold, UFold, MXFold2, RNAformer)
        fileAcceptInfo.textContent = 'Supports FASTA, TXT formats';
        
        // Height management now handled by standard-input-area
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
    
    // Sync heights after file info display
    // Height management now handled by standard-input-area
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
    
    // Sync heights after file removal
    // Height management now handled by standard-input-area
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
    
    // For RNAmigos2, Mol2Aptamer, RNAFlow, RNA-FrameFlow, Reformer, CoPRA, and RiboDiffusion, skip general input validation as they have their own validation
    if (currentModel.id !== 'rnamigos2' && currentModel.id !== 'mol2aptamer' && currentModel.id !== 'rnaflow' && currentModel.id !== 'rnaframeflow' && currentModel.id !== 'reformer' && currentModel.id !== 'copra' && currentModel.id !== 'ribodiffusion') {
        // For other models, use general input validation
        inputFile = document.getElementById('inputFile').files[0];
        inputText = document.getElementById('inputText').value.trim();
        
        // For BPFold, also check standard-input-area for file content
        if (currentModel.id === 'bpfold') {
            const fileUpload = document.getElementById('rnaSequencesFileUpload');
            if (fileUpload && fileUpload.hasAttribute('data-file-content')) {
                const fileContent = fileUpload.getAttribute('data-file-content').trim();
                if (fileContent && !inputText) {
                    inputText = fileContent;
                }
            }
        }

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
        } else if (currentModel.id === 'mol2aptamer') {
            const response = await runMol2AptamerAnalysis();
            const result = await response.json();
            
            if (result.success) {
                displayResults(result);
                addToHistory(currentModel, 'Mol2Aptamer Analysis', result);
                showNotification('Analysis completed!', 'success');
            } else {
                throw new Error(result.error);
            }
        } else if (currentModel.id === 'rnaflow') {
            const response = await runRNAFlowAnalysis();
            const result = await response.json();
            
            if (result.success) {
                displayResults(result);
                addToHistory(currentModel, 'RNAFlow Analysis', result);
                showNotification('Analysis completed!', 'success');
            } else {
                throw new Error(result.error);
            }
        } else if (currentModel.id === 'rnaframeflow') {
            const response = await runRNAFrameFlowAnalysis();
            const result = await response.json();
            
            if (result.success) {
                displayResults(result);
                addToHistory(currentModel, 'RNA-FrameFlow Analysis', result);
                showNotification('Analysis completed!', 'success');
            } else {
                throw new Error(result.error);
            }
        } else if (currentModel.id === 'reformer') {
            const result = await runReformerAnalysis();
            
            if (result.success) {
                displayResults(result);
                addToHistory(currentModel, 'Reformer Analysis', result);
                showNotification('Analysis completed!', 'success');
            } else {
                throw new Error(result.error);
            }
        } else if (currentModel.id === 'copra') {
            const result = await runCoPRAAnalysis();
            
            if (result.success) {
                displayResults(result);
                addToHistory(currentModel, 'CoPRA Analysis', result);
                showNotification('Analysis completed!', 'success');
            } else {
                throw new Error(result.error);
            }
        } else if (currentModel.id === 'ribodiffusion') {
            const result = await runRiboDiffusionAnalysis();
            
            if (result.success) {
                displayResults(result);
                addToHistory(currentModel, 'RiboDiffusion Analysis', result);
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
    // Skip this check for Reformer and RiboDiffusion models as they have different data structures
    if (currentModel.id !== 'reformer' && currentModel.id !== 'ribodiffusion' && !result.result && !result.results) {
        resultContent.innerHTML = '<div class="alert alert-warning">No result data</div>';
        showResultSection(); // Always show result section
        return;
    }
    
    // Special check for RiboDiffusion
    if (currentModel.id === 'ribodiffusion' && !result.data) {
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
    } else if (currentModel.id === 'mol2aptamer') {
        html = displayMol2AptamerResults(result);
    } else if (currentModel.id === 'rnaflow') {
        html = displayRNAFlowResults(result);
    } else if (currentModel.id === 'rnaframeflow') {
        html = displayRNAFrameFlowResults(result);
    } else if (currentModel.id === 'reformer') {
        html = displayReformerResults(result);
        // Show download button for Reformer
        const downloadActions = document.getElementById('downloadActions');
        if (downloadActions) {
            downloadActions.style.display = 'flex';
        }
    } else if (currentModel.id === 'copra') {
        html = displayCoPRAResults(result);
    } else if (currentModel.id === 'ribodiffusion') {
        html = displayRiboDiffusionResults(result);
        // Show download button for RiboDiffusion
        const downloadActions = document.getElementById('downloadActions');
        if (downloadActions) {
            downloadActions.style.display = 'flex';
        }
    } else {
        html = displayDefaultResults(result.result);
    }
    
    resultContent.innerHTML = html;
    showResultSection(); // Always show result section after displaying results
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
    
    // Calculate score statistics
    const scores = interactions.map(interaction => interaction.score || 0);
    const bestScore = Math.max(...scores);
    const worstScore = Math.min(...scores);
    const avgScore = (scores.reduce((sum, score) => sum + score, 0) / scores.length).toFixed(3);
    
    let html = '<div class="rnamigos2-results">';
    
    // Summary information in BPFold style (rounded color blocks)
    html += `
        <div class="result-item">
            <h6><i class="fas fa-flask"></i>Design Results</h6>
            <div class="sequence-info">
                <div class="sequence-info-stats">
                    <div class="sequence-length">Best Score: ${bestScore.toFixed(3)}</div>
                    <div class="sequence-length">Worst Score: ${worstScore.toFixed(3)}</div>
                    <div class="sequence-length">Average Score: ${avgScore}</div>
                    <div class="sequence-length">Total Ligands: ${interactions.length}</div>
                </div>
            </div>
        </div>
    `;
    
    // Add interactions table with centered text
    const tableRows = interactions.map((interaction, index) => {
        const score = interaction.score || 0;
        let scoreClass = 'score-low';
        if (score > 0.7) scoreClass = 'score-high';
        else if (score > 0.4) scoreClass = 'score-medium';
        
        return `
            <tr>
                <td class="text-center">${index + 1}</td>
                <td class="smiles-cell text-center">${interaction.smiles || 'N/A'}</td>
                <td class="score-cell ${scoreClass} text-center">${score.toFixed(3)}</td>
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
                                <th class="text-center">Rank</th>
                                <th class="text-center">SMILES</th>
                                <th class="text-center">Score</th>
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

// Auto-resize textarea function (simplified for general use)
function autoResizeTextarea(textarea) {
    if (!textarea) return;
    
    // Check if this is a standard input area textarea
    const isStandardInputArea = textarea.closest('.standard-input-area');
    
    if (isStandardInputArea) {
        // Standard input areas handle their own height management
        // Don't interfere with the standard input area logic
        return;
    }
    
    // Check if this is a general textarea
    const isGeneralTextarea = textarea.closest('#rnaSequencesInput');
    if (isGeneralTextarea) {
        // Height management now handled by standard-input-area
        return;
    }
    
    // For other textareas (including AI input), use the original logic
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
        const dotBracket = result.structure || '';
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
        } else if (currentModel.id === 'mol2aptamer') {
            downloadAllMol2AptamerResults();
        } else if (currentModel.id === 'rnaflow') {
            downloadAllRNAFlowResults();
        } else if (currentModel.id === 'rnaframeflow') {
            downloadAllRNAFrameFlowResults();
        } else if (currentModel.id === 'reformer') {
            downloadAllReformerResults();
        } else if (currentModel.id === 'ribodiffusion') {
            downloadAllRiboDiffusionResults();
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

// Download all Mol2Aptamer results
function downloadAllMol2AptamerResults() {
    // Get current results from the global variable
    if (window.currentMol2AptamerResults && window.currentMol2AptamerResults.results) {
        const results = window.currentMol2AptamerResults;
        const aptamers = results.results || [];
        
        // Create CSV content
        let csvContent = 'Rank,Aptamer Sequence,Length,ΔG (kcal/mol)\n';
        
        aptamers.forEach((aptamer, index) => {
            const rank = index + 1;
            const sequence = (aptamer.sequence || 'N/A').replace(/"/g, '""'); // Escape quotes
            const length = aptamer.sequence ? aptamer.sequence.length : 0;
            const deltaG = (aptamer.delta_g || 0).toFixed(2);
            csvContent += `${rank},"${sequence}",${length},${deltaG}\n`;
        });
        
        // Add summary information as comments at the end
        if (aptamers.length > 0) {
            const deltaGs = aptamers.map(apt => apt.delta_g || 0);
            const bestDeltaG = Math.min(...deltaGs);
            const worstDeltaG = Math.max(...deltaGs);
            const avgDeltaG = (deltaGs.reduce((sum, dg) => sum + dg, 0) / deltaGs.length).toFixed(2);
            
            // Calculate nucleotide composition
            const allSequences = aptamers.map(apt => apt.sequence).join('');
            const totalNucleotides = allSequences.length;
            const nucleotideCounts = {
                'A': (allSequences.match(/A/g) || []).length,
                'C': (allSequences.match(/C/g) || []).length,
                'G': (allSequences.match(/G/g) || []).length,
                'U': (allSequences.match(/U/g) || []).length
            };
            
            const nucleotidePercentages = {};
            Object.keys(nucleotideCounts).forEach(nuc => {
                nucleotidePercentages[nuc] = totalNucleotides > 0 ? (nucleotideCounts[nuc] / totalNucleotides * 100).toFixed(1) : '0.0';
            });
            
            csvContent += `\n# Summary\n`;
            csvContent += `# Best ΔG,${bestDeltaG.toFixed(2)}\n`;
            csvContent += `# Worst ΔG,${worstDeltaG.toFixed(2)}\n`;
            csvContent += `# Average ΔG,${avgDeltaG}\n`;
            csvContent += `# Total Aptamers,${aptamers.length}\n`;
            csvContent += `# Nucleotide Distribution A,${nucleotidePercentages.A}%\n`;
            csvContent += `# Nucleotide Distribution C,${nucleotidePercentages.C}%\n`;
            csvContent += `# Nucleotide Distribution G,${nucleotidePercentages.G}%\n`;
            csvContent += `# Nucleotide Distribution U,${nucleotidePercentages.U}%\n`;
        }
        
        // Create and download the file
        const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = 'mol2aptamer_results.csv';
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        window.URL.revokeObjectURL(url);
        
        showNotification('Mol2Aptamer results downloaded successfully!', 'success');
    } else {
        showNotification('No Mol2Aptamer results available for download', 'warning');
    }
}

// Download all RNAFlow results
function downloadAllRNAFlowResults() {
    // Get current results from the global variable
    if (window.currentRNAFlowResults && window.currentRNAFlowResults.results) {
        const results = window.currentRNAFlowResults;
        const rnaDesigns = results.results || [];
        
        // Create CSV content
        let csvContent = 'Rank,RNA Sequence,Length,Confidence (%)\n';
        
        rnaDesigns.forEach((design, index) => {
            const rank = index + 1;
            const sequence = (design.sequence || 'N/A').replace(/"/g, '""'); // Escape quotes
            const length = design.sequence ? design.sequence.length : 0;
            const confidence = ((design.confidence || 0.8) * 100).toFixed(1);
            csvContent += `${rank},"${sequence}",${length},${confidence}\n`;
        });
        
        // Add summary information as comments at the end
        if (rnaDesigns.length > 0) {
            const confidences = rnaDesigns.map(design => design.confidence || 0.8);
            const maxConfidence = Math.max(...confidences);
            const minConfidence = Math.min(...confidences);
            const avgConfidence = (confidences.reduce((sum, conf) => sum + conf, 0) / confidences.length).toFixed(3);
            
            // Calculate nucleotide composition
            const allSequences = rnaDesigns.map(design => design.sequence).join('');
            const totalNucleotides = allSequences.length;
            const nucleotideCounts = {
                'A': (allSequences.match(/A/g) || []).length,
                'C': (allSequences.match(/C/g) || []).length,
                'G': (allSequences.match(/G/g) || []).length,
                'U': (allSequences.match(/U/g) || []).length
            };
            
            const nucleotidePercentages = {};
            Object.keys(nucleotideCounts).forEach(nuc => {
                nucleotidePercentages[nuc] = totalNucleotides > 0 ? (nucleotideCounts[nuc] / totalNucleotides * 100).toFixed(1) : '0.0';
            });
            
            csvContent += `\n# Summary\n`;
            csvContent += `# Highest Confidence,${(maxConfidence * 100).toFixed(1)}%\n`;
            csvContent += `# Lowest Confidence,${(minConfidence * 100).toFixed(1)}%\n`;
            csvContent += `# Average Confidence,${(avgConfidence * 100).toFixed(1)}%\n`;
            csvContent += `# Total Designs,${rnaDesigns.length}\n`;
            csvContent += `# Nucleotide Distribution A,${nucleotidePercentages.A}%\n`;
            csvContent += `# Nucleotide Distribution C,${nucleotidePercentages.C}%\n`;
            csvContent += `# Nucleotide Distribution G,${nucleotidePercentages.G}%\n`;
            csvContent += `# Nucleotide Distribution U,${nucleotidePercentages.U}%\n`;
        }
        
        // Create and download the file
        const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = 'rnaflow_results.csv';
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        window.URL.revokeObjectURL(url);
        
        showNotification('RNAFlow results downloaded successfully!', 'success');
    } else {
        showNotification('No RNAFlow results available for download', 'warning');
    }
}

// Download all RNA-FrameFlow results
function downloadAllRNAFrameFlowResults() {
    if (window.currentRNAFrameFlowResults && window.currentRNAFrameFlowResults.result) {
        const results = window.currentRNAFrameFlowResults.result;
        const structures = results.structures || [];
        
        if (structures.length === 0) {
            showNotification('No RNA-FrameFlow results available for download', 'warning');
            return;
        }
        
        // Create a ZIP file containing PDB files
        const zip = new JSZip();
        
        // Create CSV content for structure information
        let csvContent = 'Rank,Structure_ID,Length,Confidence\n';
        structures.forEach((structure, index) => {
            csvContent += `${index + 1},Structure_${index + 1},${structure.length},${(structure.confidence * 100).toFixed(1)}%\n`;
        });
        
        // Add CSV to ZIP
        zip.file('rnaframeflow_structures.csv', csvContent);
        
        // Download PDB files and trajectory files from server and add to ZIP
        const downloadPromises = structures.map((structure, index) => {
            if (structure.pdb_file_path) {
                const filename = structure.pdb_filename || `na_sample_${index}.pdb`;
                
                // Build correct download URL
                // pdb_file_path format: /path/to/temp/samples/length_25/na_sample_0.pdb
                // Need to extract: length_25/na_sample_0.pdb
                const pathParts = structure.pdb_file_path.split('/');
                const samplesIndex = pathParts.indexOf('samples');
                if (samplesIndex !== -1 && samplesIndex + 2 < pathParts.length) {
                    const relativePath = pathParts.slice(samplesIndex + 1).join('/');
                    const downloadUrl = `/api/rnaframeflow/download/${relativePath}`;
                    
                    console.log(`Downloading PDB file: ${downloadUrl}`);
                    
                    // Download main PDB file
                    const mainPdbPromise = fetch(downloadUrl)
                        .then(response => {
                            if (!response.ok) {
                                throw new Error(`Failed to download ${filename}: ${response.status}`);
                            }
                            return response.text();
                        })
                        .then(content => {
                            console.log(`Successfully downloaded ${filename}, size: ${content.length} bytes`);
                            // Use actual PDB filename instead of index
                            const actualFilename = structure.pdb_filename || `na_sample_${index}.pdb`;
                            zip.file(actualFilename, content);
                        })
                        .catch(error => {
                            console.error(`Error downloading ${filename}:`, error);
                            // If download fails, try using pdb_content
                            if (structure.pdb_content) {
                                console.log(`Falling back to pdb_content for ${filename}`);
                                const actualFilename = structure.pdb_filename || `na_sample_${index}.pdb`;
                                zip.file(actualFilename, structure.pdb_content);
                            }
                        });
                    
                    // Download trajectory file
                    const trajFilename = filename.replace('.pdb', '_traj.pdb');
                    const trajDownloadUrl = downloadUrl.replace('.pdb', '_traj.pdb');
                    
                    console.log(`Downloading trajectory file: ${trajDownloadUrl}`);
                    
                    const trajPdbPromise = fetch(trajDownloadUrl)
                        .then(response => {
                            if (!response.ok) {
                                console.warn(`Trajectory file not found: ${trajFilename}`);
                                return null; // Trajectory file may not exist, this is normal
                            }
                            return response.text();
                        })
                        .then(content => {
                            if (content) {
                                console.log(`Successfully downloaded ${trajFilename}, size: ${content.length} bytes`);
                                zip.file(trajFilename, content);
                            }
                        })
                        .catch(error => {
                            console.warn(`Error downloading trajectory file ${trajFilename}:`, error);
                            // Trajectory file download failure does not affect main functionality
                        });
                    
                    // Wait for both files to download
                    return Promise.all([mainPdbPromise, trajPdbPromise]);
                } else {
                    console.error(`Invalid pdb_file_path format: ${structure.pdb_file_path}`);
                    // Fallback to using pdb_content
                    if (structure.pdb_content) {
                        const actualFilename = structure.pdb_filename || `na_sample_${index}.pdb`;
                        zip.file(actualFilename, structure.pdb_content);
                    }
                    return Promise.resolve();
                }
            } else if (structure.pdb_content) {
                // Fallback to using pdb_content
                console.log(`Using pdb_content for structure ${index + 1}`);
                const actualFilename = structure.pdb_filename || `na_sample_${index}.pdb`;
                zip.file(actualFilename, structure.pdb_content);
                return Promise.resolve();
            }
            return Promise.resolve();
        });
        
        // Wait for all downloads to complete
        Promise.all(downloadPromises).then(() => {
            // Generate and download ZIP file
            zip.generateAsync({type: 'blob'}).then(function(content) {
                const url = window.URL.createObjectURL(content);
                const a = document.createElement('a');
                a.href = url;
                a.download = 'rnaframeflow_structures.zip';
                document.body.appendChild(a);
                a.click();
                document.body.removeChild(a);
                window.URL.revokeObjectURL(url);
                
                showNotification('RNA-FrameFlow structures downloaded successfully!', 'success');
            }).catch(function(error) {
                console.error('Error creating ZIP file:', error);
                showNotification('Error creating download file', 'error');
            });
        }).catch(error => {
            console.error('Error downloading PDB files:', error);
            showNotification('Error downloading structure files', 'error');
        });
        
    } else {
        showNotification('No RNA-FrameFlow results available for download', 'warning');
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

// RNAmigos2 Analysis Functions
async function runRNAmigos2Analysis() {
    // Get input data
    const cifFileInput = document.getElementById('rnamigos2FileInput');
    const cifContentElement = document.getElementById('rnamigos2CifContent');
    const residuesElement = document.getElementById('rnamigos2Residues');
    const smilesFileInput = document.getElementById('rnamigos2SmilesFileInput');
    const smilesTextElement = document.getElementById('rnamigos2SmilesText');
    
    // Validate inputs
    if (!cifFileInput || !cifContentElement || !residuesElement || !smilesFileInput || !smilesTextElement) {
        throw new Error('RNAmigos2 input elements not found. Please refresh the page and try again.');
    }
    
    const cifFile = cifFileInput.files[0];
    let cifContent = cifContentElement.value.trim();
    let residuesText = residuesElement.value.trim();
    
    // If no residues in textarea, check if file was uploaded
    if (!residuesText) {
        const unifiedInput = document.getElementById('rnamigos2ResiduesUnifiedInput');
        if (unifiedInput && unifiedInput.hasAttribute('data-file-content')) {
            residuesText = unifiedInput.getAttribute('data-file-content').trim();
        }
    }
    const smilesFile = smilesFileInput.files[0];
    let smilesText = smilesTextElement.value.trim();
    
    // If no CIF content in textarea, check if file was uploaded
    if (!cifContent) {
        const unifiedInput = document.getElementById('rnamigos2UnifiedInput');
        if (unifiedInput && unifiedInput.hasAttribute('data-file-content')) {
            cifContent = unifiedInput.getAttribute('data-file-content').trim();
        }
    }
    
    // If no SMILES in textarea, check if file was uploaded
    if (!smilesText) {
        const unifiedInput = document.getElementById('rnamigos2SmilesUnifiedInput');
        if (unifiedInput && unifiedInput.hasAttribute('data-file-content')) {
            smilesText = unifiedInput.getAttribute('data-file-content').trim();
        }
    }
    
    // Validate inputs
    if (!cifFile && !cifContent) {
        throw new Error('Please provide a CIF or mmCIF file or paste the content');
    }
    
    if (!smilesFile && !smilesText) {
        throw new Error('Please provide either a SMILES file or paste SMILES strings');
    }
    
    if (!residuesText) {
        throw new Error('Please provide binding site residues');
    }
    
    // Prepare data
    let finalCifContent = cifContent;
    if (cifFile && !cifContent) {
        finalCifContent = await readFileAsText(cifFile);
    }
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
        cif_content: finalCifContent,
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
    
    // Heights are managed by standard input area
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


// Run Mol2Aptamer analysis
async function runMol2AptamerAnalysis() {
    // Get input data
    const smilesElement = document.getElementById('mol2aptamerSmiles');
    const numSequencesElement = document.getElementById('mol2aptamerNumSequences');
    const maxLengthElement = document.getElementById('mol2aptamerMaxLength');
    const temperatureElement = document.getElementById('mol2aptamerTemperature');
    const topKElement = document.getElementById('mol2aptamerTopK');
    const topPElement = document.getElementById('mol2aptamerTopP');
    const strategyElement = document.getElementById('mol2aptamerStrategy');
    
    // Validate inputs
    if (!smilesElement || !numSequencesElement || !maxLengthElement || 
        !temperatureElement || !topKElement || !topPElement || !strategyElement) {
        throw new Error('Mol2Aptamer input elements not found. Please refresh the page and try again.');
    }
    
    let smiles = smilesElement.value.trim();
    
    // If no SMILES in textarea, check if file was uploaded
    if (!smiles) {
        const fileUpload = document.getElementById('mol2aptamerSmilesFileUpload');
        if (fileUpload && fileUpload.hasAttribute('data-file-content')) {
            smiles = fileUpload.getAttribute('data-file-content').trim();
        }
    }
    
    const numSequences = parseInt(numSequencesElement.value);
    const maxLength = parseInt(maxLengthElement.value);
    const temperature = parseFloat(temperatureElement.value);
    const topK = parseInt(topKElement.value);
    const topP = parseFloat(topPElement.value);
    const strategy = strategyElement.value;
    
    
    // Validate that SMILES is provided
    if (!smiles) {
        throw new Error('Please provide a SMILES string (either by typing or uploading a file)');
    }
    
    // Validate parameters
    if (numSequences < 1 || numSequences > 100) {
        throw new Error('Number of sequences must be between 1 and 100');
    }
    
    if (maxLength < 10 || maxLength > 200) {
        throw new Error('Max length must be between 10 and 200');
    }
    
    if (temperature < 0.1 || temperature > 2.0) {
        throw new Error('Temperature must be between 0.1 and 2.0');
    }
    
    if (topK < 1 || topK > 100) {
        throw new Error('Top-K must be between 1 and 100');
    }
    
    if (topP < 0.1 || topP > 1.0) {
        throw new Error('Top-P must be between 0.1 and 1.0');
    }
    
    // Prepare request data
    const requestData = {
        smiles: smiles,
        num_sequences: numSequences,
        max_length: maxLength,
        temperature: temperature,
        top_k: topK,
        top_p: topP,
        strategy: strategy
    };
    
    // Make API call
    const response = await fetch('/api/mol2aptamer/predict', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify(requestData)
    });
    
    if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.error || 'Mol2Aptamer analysis failed');
    }
    
    return response;
}

// Display RNA-FrameFlow results
function displayRNAFrameFlowResults(results) {
    if (!results || !results.result || !results.result.structures || results.result.structures.length === 0) {
        return '<div class="alert alert-warning">No 3D structures generated</div>';
    }
    
    // Store results globally for download functionality
    window.currentRNAFrameFlowResults = results;
    
    // Get structures data
    let structures = results.result.structures || [];
    const statistics = results.result.statistics || {};
    
    // Sort structures by confidence (highest to lowest)
    structures = structures.sort((a, b) => (b.confidence || 0.8) - (a.confidence || 0.8));
    
    // Calculate confidence statistics
    const confidences = structures.map(struct => struct.confidence || 0.8);
    const maxConfidence = Math.max(...confidences);
    const minConfidence = Math.min(...confidences);
    const avgConfidence = (confidences.reduce((sum, conf) => sum + conf, 0) / confidences.length).toFixed(3);
    
    let html = '<div class="rnaframeflow-results">';
    
    // Summary information in BPFold style (rounded color blocks)
    html += `
        <div class="result-item">
            <h6><i class="fas fa-dna"></i>Design Results</h6>
            <div class="sequence-info">
                <div class="sequence-info-stats">
                    <div class="extend-info">Highest Confidence: ${(maxConfidence * 100).toFixed(1)}%</div>
                    <div class="extend-info">Lowest Confidence: ${(minConfidence * 100).toFixed(1)}%</div>
                    <div class="extend-info">Average Confidence: ${(avgConfidence * 100).toFixed(1)}%</div>
            </div>
            </div>
        </div>
    `;
    
    // Structure results table
    const tableRows = structures.map((structure, index) => {
        const confidence = structure.confidence || 0.8;
        let scoreClass = 'score-low';
        if (confidence > 0.7) scoreClass = 'score-high';
        else if (confidence > 0.4) scoreClass = 'score-medium';
        
        // Use actual PDB filename, fallback to default format if not available
        const structureId = structure.pdb_filename || `na_sample_${index}.pdb`;
        
        return `
            <tr>
                <td class="text-center">${index + 1}</td>
                <td class="sequence-cell text-center">${structureId}</td>
                <td class="score-cell ${scoreClass} text-center">${(confidence * 100).toFixed(1)}%</td>
            </tr>
        `;
    }).join('');
        
        html += `
            <div class="result-item">
            <h6><i class="fas fa-table"></i>Generated 3D Structures</h6>
            <div class="structure-result">
                <div class="interactions-table">
                    <table>
                        <thead>
                            <tr>
                                <th>Rank</th>
                                <th>Structure ID</th>
                                <th>Confidence</th>
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
}// Display Mol2Aptamer results
function displayMol2AptamerResults(results) {
    if (!results || !results.results || results.results.length === 0) {
        return '<div class="alert alert-warning">No aptamer sequences generated</div>';
    }
    
    // Store results globally for download functionality
    window.currentMol2AptamerResults = results;
    
    const aptamers = results.results;
    
    // Calculate ΔG statistics
    const deltaGs = aptamers.map(apt => apt.delta_g || 0);
    const bestDeltaG = Math.min(...deltaGs); // Most negative (best)
    const worstDeltaG = Math.max(...deltaGs); // Least negative (worst)
    const avgDeltaG = (deltaGs.reduce((sum, dg) => sum + dg, 0) / deltaGs.length).toFixed(2);
    
    // Calculate nucleotide composition (in one line)
    const allSequences = aptamers.map(apt => apt.sequence).join('');
    const totalNucleotides = allSequences.length;
    const nucleotideCounts = {
        'A': (allSequences.match(/A/g) || []).length,
        'C': (allSequences.match(/C/g) || []).length,
        'G': (allSequences.match(/G/g) || []).length,
        'U': (allSequences.match(/U/g) || []).length
    };
    
    const nucleotidePercentages = {};
    Object.keys(nucleotideCounts).forEach(nuc => {
        nucleotidePercentages[nuc] = totalNucleotides > 0 ? (nucleotideCounts[nuc] / totalNucleotides * 100).toFixed(1) : '0.0';
    });
    
    const nucleotideDistribution = `A: ${nucleotidePercentages.A}% C: ${nucleotidePercentages.C}% G: ${nucleotidePercentages.G}% U: ${nucleotidePercentages.U}%`;
    
    let html = '<div class="mol2aptamer-results">';
    
    // Summary information in BPFold style (rounded color blocks)
    html += `
        <div class="result-item">
            <h6><i class="fas fa-dna"></i>Design Results</h6>
            <div class="sequence-info">
                <div class="sequence-info-stats">
                    <div class="sequence-length">Best ΔG: ${bestDeltaG.toFixed(2)} kcal/mol</div>
                    <div class="sequence-length">Worst ΔG: ${worstDeltaG.toFixed(2)} kcal/mol</div>
                    <div class="sequence-length">Average ΔG: ${avgDeltaG} kcal/mol</div>
                    <div class="sequence-length">Nucleotide Distribution: ${nucleotideDistribution}</div>
                </div>
            </div>
            </div>
        `;
    
    // Design results table in RNAmigos2 style
    const tableRows = aptamers.map((aptamer, index) => {
        const deltaG = aptamer.delta_g || 0;
        let scoreClass = 'score-low';
        if (deltaG < -2.0) scoreClass = 'score-high';
        else if (deltaG < -1.0) scoreClass = 'score-medium';
        
        return `
            <tr>
                <td class="text-center">${index + 1}</td>
                <td class="sequence-cell text-center">${aptamer.sequence}</td>
                <td class="length-cell text-center">${aptamer.sequence.length}</td>
                <td class="score-cell ${scoreClass} text-center">${deltaG.toFixed(2)} kcal/mol</td>
            </tr>
        `;
    }).join('');
    
    html += `
        <div class="result-item">
            <h6><i class="fas fa-table"></i>Generated Aptamer Sequences</h6>
            <div class="structure-result">
                <div class="interactions-table">
                    <table>
                        <thead>
                            <tr>
                                <th>Rank</th>
                                <th>Aptamer Sequence</th>
                                <th>Length</th>
                                <th>ΔG</th>
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


// Copy text to clipboard
function copyToClipboard(text) {
    navigator.clipboard.writeText(text).then(() => {
        showNotification('Copied to clipboard!', 'success');
    }).catch(err => {
        showNotification('Failed to copy to clipboard', 'error');
    });
}

// RNAFlow Analysis Functions
async function runRNAFlowAnalysis() {
    // Get input data
    const proteinSequenceElement = document.getElementById('rnaflowProteinSequence');
    const rnaLengthElement = document.getElementById('rnaflowRnaLength');
    const numSamplesElement = document.getElementById('rnaflowNumSamples');
    
    // Validate inputs
    if (!proteinSequenceElement || !rnaLengthElement || !numSamplesElement) {
        throw new Error('RNAFlow input elements not found. Please refresh the page and try again.');
    }
    
    let proteinSequence = proteinSequenceElement.value.trim();
    
    // If no protein sequence in textarea, check if file was uploaded
    if (!proteinSequence) {
        const fileUpload = document.getElementById('rnaflowProteinFileUpload');
        if (fileUpload && fileUpload.hasAttribute('data-file-content')) {
            proteinSequence = fileUpload.getAttribute('data-file-content').trim();
        }
    }
    
    const rnaLength = parseInt(rnaLengthElement.value);
    const numSamples = parseInt(numSamplesElement.value);
    
    // Validate that protein sequence is provided
    if (!proteinSequence) {
        throw new Error('Please provide a protein sequence');
    }
    
    // Validate parameters
    if (rnaLength < 5 || rnaLength > 200) {
        throw new Error('RNA length must be between 5 and 200');
    }
    
    if (numSamples < 1 || numSamples > 10) {
        throw new Error('Number of samples must be between 1 and 10');
    }
    
    // Prepare request data
    const requestData = {
        protein_sequence: proteinSequence,
        rna_length: rnaLength,
        num_samples: numSamples,
        protein_coordinates: [] // For now, empty coordinates
    };
    
    // Make API call
    const response = await fetch('/api/rnaflow/design', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify(requestData)
    });
    
    if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.error || 'RNAFlow analysis failed');
    }
    
    return response;
}

// Display RNAFlow results
function displayRNAFlowResults(results) {
    if (!results || !results.results || results.results.length === 0) {
        return '<div class="alert alert-warning">No RNA designs generated</div>';
    }
    
    // Store results globally for download functionality
    window.currentRNAFlowResults = results;
    
    const rnaDesigns = results.results;
    
    // Calculate confidence statistics
    const confidences = rnaDesigns.map(design => design.confidence || 0.8);
    const maxConfidence = Math.max(...confidences);
    const minConfidence = Math.min(...confidences);
    const avgConfidence = (confidences.reduce((sum, conf) => sum + conf, 0) / confidences.length).toFixed(3);
    
    // Calculate nucleotide composition (in one line)
    const allSequences = rnaDesigns.map(design => design.sequence).join('');
    const totalNucleotides = allSequences.length;
    const nucleotideCounts = {
        'A': (allSequences.match(/A/g) || []).length,
        'C': (allSequences.match(/C/g) || []).length,
        'G': (allSequences.match(/G/g) || []).length,
        'U': (allSequences.match(/U/g) || []).length
    };
    
    const nucleotidePercentages = {};
    Object.keys(nucleotideCounts).forEach(nuc => {
        nucleotidePercentages[nuc] = totalNucleotides > 0 ? (nucleotideCounts[nuc] / totalNucleotides * 100).toFixed(1) : '0.0';
    });
    
    const nucleotideDistribution = `A: ${nucleotidePercentages.A}% C: ${nucleotidePercentages.C}% G: ${nucleotidePercentages.G}% U: ${nucleotidePercentages.U}%`;
    
    let html = '<div class="rnaflow-results">';
    
    // Summary information in BPFold style (rounded color blocks)
    html += `
        <div class="result-item">
            <h6><i class="fas fa-dna"></i>Design Results</h6>
            <div class="sequence-info">
                <div class="sequence-info-stats">
                    <div class="sequence-length">Highest Confidence: ${(maxConfidence * 100).toFixed(1)}%</div>
                    <div class="sequence-length">Lowest Confidence: ${(minConfidence * 100).toFixed(1)}%</div>
                    <div class="sequence-length">Average Confidence: ${(avgConfidence * 100).toFixed(1)}%</div>
                    <div class="sequence-length">Nucleotide Distribution: ${nucleotideDistribution}</div>
            </div>
            </div>
        </div>
    `;
    
    // Design results table in RNAmigos2 style
    const tableRows = rnaDesigns.map((design, index) => {
        const confidence = design.confidence || 0.8;
        let scoreClass = 'score-low';
        if (confidence > 0.7) scoreClass = 'score-high';
        else if (confidence > 0.4) scoreClass = 'score-medium';
        
        return `
            <tr>
                <td class="text-center">${index + 1}</td>
                <td class="sequence-cell text-center">${design.sequence}</td>
                <td class="length-cell text-center">${design.sequence.length}</td>
                <td class="score-cell ${scoreClass} text-center">${(confidence * 100).toFixed(1)}%</td>
            </tr>
        `;
    }).join('');
        
        html += `
            <div class="result-item">
            <h6><i class="fas fa-table"></i>Generated RNA Sequences</h6>
            <div class="structure-result">
                <div class="interactions-table">
                    <table>
                        <thead>
                            <tr>
                                <th>Rank</th>
                                <th>RNA Sequence</th>
                                <th>Length</th>
                                <th>Confidence</th>
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

// Standard Input Area - Universal input area management

// Initialize single block unified input area
function initializeSingleBlockInput(unifiedInputId, textareaId, fileInputId, placeholderId) {
    const unifiedInput = document.getElementById(unifiedInputId);
    const textarea = textareaId ? document.getElementById(textareaId) : null;
    const fileInput = document.getElementById(fileInputId);
    const placeholder = document.getElementById(placeholderId);
    
    if (!unifiedInput || !fileInput || !placeholder) {
        return;
    }
    
    // Check if already initialized to prevent duplicate event listeners
    if (unifiedInput.hasAttribute('data-initialized')) {
        return;
    }
    
    // Mark as initialized
    unifiedInput.setAttribute('data-initialized', 'true');
    
    // Click handler for unified input area
    unifiedInput.addEventListener('click', (e) => {
        e.preventDefault();
        e.stopPropagation();
        
        // Check if file info is displayed (file is uploaded)
        const fileInfo = unifiedInput.querySelector('.file-info-content');
        if (fileInfo && fileInfo.style.display !== 'none') {
            // File is uploaded, don't allow new input
            return;
        }
        
        if (textarea) {
            // Show textarea and focus
            placeholder.style.display = 'none';
            textarea.style.display = 'block';
            textarea.focus();
        } else {
            // Only file upload - trigger file input
            fileInput.click();
        }
    });
    
    // Textarea blur handler - hide if empty (only if textarea exists)
    if (textarea) {
        textarea.addEventListener('blur', () => {
            if (textarea.value.trim() === '') {
                textarea.style.display = 'none';
                placeholder.style.display = 'block';
            }
        });
        
        // Textarea input handler - auto resize
        textarea.addEventListener('input', () => {
            autoResizeTextarea(textarea);
        });
    }
    
    // Drag and drop handlers
    unifiedInput.addEventListener('dragover', (e) => {
        e.preventDefault();
        unifiedInput.classList.add('dragover');
    });
    
    unifiedInput.addEventListener('dragleave', (e) => {
        e.preventDefault();
        unifiedInput.classList.remove('dragover');
    });
    
    unifiedInput.addEventListener('drop', (e) => {
        e.preventDefault();
        unifiedInput.classList.remove('dragover');
        
        const files = e.dataTransfer.files;
        if (files.length > 0) {
            handleSingleBlockFileUpload(files[0], unifiedInputId, textareaId, fileInputId, placeholderId);
        }
    });
    
    // File input change handler
    fileInput.addEventListener('change', (e) => {
        if (e.target.files.length > 0) {
            handleSingleBlockFileUpload(e.target.files[0], unifiedInputId, textareaId, fileInputId, placeholderId);
        }
    });
}

// Handle file upload for single block input
function handleSingleBlockFileUpload(file, unifiedInputId, textareaId, fileInputId, placeholderId) {
    const unifiedInput = document.getElementById(unifiedInputId);
    const textarea = textareaId ? document.getElementById(textareaId) : null;
    const fileInput = document.getElementById(fileInputId);
    const placeholder = document.getElementById(placeholderId);
    
    if (!unifiedInput || !fileInput || !placeholder) {
        return;
    }
    
    // Read file content
    const reader = new FileReader();
    reader.onload = function(e) {
        const fileContent = e.target.result;
        
        // Store file content
        unifiedInput.setAttribute('data-file-content', fileContent);
        
        // Hide placeholder and textarea (if exists)
        placeholder.style.display = 'none';
        if (textarea) {
            textarea.style.display = 'none';
        }
        
        // Display file info
        displaySingleBlockFileInfo(file, unifiedInputId);
    };
    
    reader.onerror = function() {
        showNotification('Error reading file', 'error');
    };
    
    reader.readAsText(file);
}

// Display file info for single block input
function displaySingleBlockFileInfo(file, unifiedInputId) {
    const unifiedInput = document.getElementById(unifiedInputId);
    if (!unifiedInput) {
        return;
    }
    
    // Remove existing file info if any
    const existingFileInfo = unifiedInput.querySelector('.file-info-content');
    if (existingFileInfo) {
        existingFileInfo.remove();
    }
    
    // Create file info element
    const fileInfo = document.createElement('div');
    fileInfo.className = 'file-info-content';
    fileInfo.style.display = 'flex';
    
    // Use appropriate icon
    const fileExtension = file.name.split('.').pop().toLowerCase();
    const iconClass = fileExtension === 'txt' ? 'fa-file-alt' : 'fa-file-code';
    
        fileInfo.innerHTML = `
            <div class="file-details">
            <i class="fas ${iconClass}"></i>
            <div>
                    <div class="file-name">${file.name}</div>
                <div class="file-size">${formatFileSize(file.size)}</div>
                </div>
        </div>
        <button class="btn-remove-file" onclick="event.stopPropagation(); removeSingleBlockFile('${unifiedInputId}')">
                    <i class="fas fa-times"></i>
                </button>
    `;
    
    unifiedInput.appendChild(fileInfo);
}

// Remove file from single block input
function removeSingleBlockFile(unifiedInputId) {
    const unifiedInput = document.getElementById(unifiedInputId);
    if (!unifiedInput) {
        return;
    }
    
    // Get related elements
    const textarea = unifiedInput.querySelector('textarea');
    const fileInput = unifiedInput.querySelector('input[type="file"]');
    const placeholder = unifiedInput.querySelector('.input-placeholder');
    const fileInfo = unifiedInput.querySelector('.file-info-content');
    
    // Clear file input
    if (fileInput) {
        fileInput.value = '';
    }
    
    // Clear stored file content
    unifiedInput.removeAttribute('data-file-content');
    
    // Remove file info
    if (fileInfo) {
        fileInfo.remove();
    }
    
    // Show placeholder
    if (placeholder) {
        placeholder.style.display = 'block';
    }
    
    // Hide textarea
    if (textarea) {
        textarea.style.display = 'none';
        textarea.value = '';
    }
}

// Standard Input Area - Universal input area management

// Display RNAmigos2 CIF file info
function displayRNAmigos2CifFileInfo(file) {
    const fileUpload = document.getElementById('rnamigos2FileUpload');
    if (!fileUpload) return;
    
    const inputPlaceholder = fileUpload.querySelector('.input-placeholder');
    let fileInfo = fileUpload.querySelector('.file-info-content');
    
    // Hide input placeholder
    if (inputPlaceholder) inputPlaceholder.style.display = 'none';
    
    // Remove existing file info if any
    if (fileInfo) {
        fileInfo.remove();
    }
    
    // Create and add new file info
    const newFileInfo = createRNAmigos2CifFileInfoElement(file);
    fileUpload.appendChild(newFileInfo);
}

// Create RNAmigos2 CIF file info element
function createRNAmigos2CifFileInfoElement(file) {
    const fileInfo = document.createElement('div');
    fileInfo.className = 'file-info-content';
    fileInfo.style.display = 'flex';
    
    // Use the same icon logic as other file uploads
    const fileExtension = file.name.split('.').pop().toLowerCase();
    const iconClass = fileExtension === 'cif' || fileExtension === 'mmcif' ? 'fa-file-code' : 'fa-file-alt';
    
    fileInfo.innerHTML = `
        <i class="fas ${iconClass}"></i>
        <div class="file-details">
            <div class="file-name">${file.name}</div>
            <div class="file-size">${formatFileSize(file.size)}</div>
        </div>
        <button class="btn-remove-file" onclick="event.stopPropagation(); removeRNAmigos2CifFile()">
            <i class="fas fa-times"></i>
        </button>
    `;
    
    return fileInfo;
}

// Remove RNAmigos2 CIF file
function removeRNAmigos2CifFile() {
    const fileUpload = document.getElementById('rnamigos2FileUpload');
    const fileInput = document.getElementById('rnamigos2FileInput');
    
    if (!fileUpload || !fileInput) return;
    
    // Clear file input
    fileInput.value = '';
    
    // Hide file info and show upload content
    const fileInfo = fileUpload.querySelector('.file-info-content');
    if (fileInfo) {
        fileInfo.style.display = 'none';
    }
    
    const inputPlaceholder = fileUpload.querySelector('.input-placeholder');
    if (uploadContent) {
        uploadContent.style.display = 'flex';
    }
    
    // Clear stored file content
    fileUpload.removeAttribute('data-file-content');
}


// Check and toggle file upload area based on textarea content
function checkAndToggleFileUpload() {
    const standardInputAreas = document.querySelectorAll('.standard-input-area');
    
    standardInputAreas.forEach(area => {
        const textarea = area.querySelector('textarea');
        const fileUpload = area.querySelector('.file-upload-area');
        
        if (textarea && fileUpload) {
            const hasContent = textarea.value.trim().length > 0;
            
            if (hasContent) {
                // Disable file upload area when textarea has content
                fileUpload.style.pointerEvents = 'none';
                fileUpload.style.opacity = '0.6';
                fileUpload.style.cursor = 'not-allowed';
                fileUpload.setAttribute('data-disabled', 'true');
            } else {
                // Enable file upload area when textarea is empty
                fileUpload.style.pointerEvents = '';
                fileUpload.style.opacity = '';
                fileUpload.style.cursor = '';
                fileUpload.removeAttribute('data-disabled');
            }
        }
    });
}

// RNA-FrameFlow Analysis Function
async function runRNAFrameFlowAnalysis() {
    // Get input parameters
    const sequenceLength = document.getElementById('rnaframeflowSequenceLength').value;
    const numSequences = document.getElementById('rnaframeflowNumSequences').value;
    
    // Validate inputs
    if (!sequenceLength || !numSequences) {
        throw new Error('Please provide all required parameters');
    }
    
    const sequenceLengthNum = parseInt(sequenceLength);
    const numSequencesNum = parseInt(numSequences);
    
    if (isNaN(sequenceLengthNum) || sequenceLengthNum < 10 || sequenceLengthNum > 200) {
        throw new Error('Sequence length must be between 10 and 200');
    }
    
    if (isNaN(numSequencesNum) || numSequencesNum < 1 || numSequencesNum > 20) {
        throw new Error('Number of sequences must be between 1 and 20');
    }
    
    // Get additional parameters
    const temperature = document.getElementById('rnaframeflowTemperature').value;
    const randomSeed = document.getElementById('rnaframeflowSeed').value;
    const numTimesteps = document.getElementById('rnaframeflowNumTimesteps').value;
    const minT = document.getElementById('rnaframeflowMinT').value;
    const expRate = document.getElementById('rnaframeflowExpRate').value;
    const selfCondition = document.getElementById('rnaframeflowSelfCondition').value;
    
    const temperatureNum = parseFloat(temperature);
    const randomSeedNum = randomSeed ? parseInt(randomSeed) : null;
    const numTimestepsNum = parseInt(numTimesteps);
    const minTNum = parseFloat(minT);
    const expRateNum = parseInt(expRate);
    const selfConditionBool = selfCondition === 'true';
    const overwriteBool = true; // Always overwrite
    
    // Validate additional parameters
    if (isNaN(temperatureNum) || temperatureNum < 0.1 || temperatureNum > 2.0) {
        throw new Error('Temperature must be between 0.1 and 2.0');
    }
    
    if (isNaN(numTimestepsNum) || numTimestepsNum < 10 || numTimestepsNum > 200) {
        throw new Error('Sampling timesteps must be between 10 and 200');
    }
    
    if (isNaN(minTNum) || minTNum < 0.001 || minTNum > 0.1) {
        throw new Error('Minimum time must be between 0.001 and 0.1');
    }
    
    if (isNaN(expRateNum) || expRateNum < 1 || expRateNum > 50) {
        throw new Error('Exponential rate must be between 1 and 50');
    }
    
    // Prepare request data
    const requestData = {
        sequence_length: sequenceLengthNum,
        num_sequences: numSequencesNum,
        temperature: temperatureNum,
        random_seed: randomSeedNum,
        num_timesteps: numTimestepsNum,
        min_t: minTNum,
        exp_rate: expRateNum,
        self_condition: selfConditionBool,
        overwrite: overwriteBool
    };
    
    // Make API call
    const response = await fetch('/api/rnaframeflow/design', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify(requestData)
    });
    
    if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.error || `HTTP error! status: ${response.status}`);
    }
    
    return response;
}

// Handle RNAmigos2 CIF file upload
function handleRNAmigos2CifFileUpload(file) {
    const fileUpload = document.getElementById('rnamigos2FileUpload');
    const fileInput = document.getElementById('rnamigos2FileInput');
    
    if (!fileUpload || !fileInput) return;
    
    // Read file content and store it for later use
    const reader = new FileReader();
    reader.onload = function(e) {
        const fileContent = e.target.result;
        // Store file content in a data attribute for later retrieval
        fileUpload.setAttribute('data-file-content', fileContent);
        
        // Display file info
        displayRNAmigos2CifFileInfo(file);
    };
    
    reader.onerror = function() {
        showNotification('Error reading file', 'error');
    };
    
    reader.readAsText(file);
}

// Display RNAmigos2 CIF file info
function displayRNAmigos2CifFileInfo(file) {
    const fileUpload = document.getElementById('rnamigos2FileUpload');
    if (!fileUpload) return;
    
    const inputPlaceholder = fileUpload.querySelector('.input-placeholder');
    let fileInfo = fileUpload.querySelector('.file-info-content');
    
    // Hide input placeholder
    if (inputPlaceholder) inputPlaceholder.style.display = 'none';
    
    // Remove existing file info if any
    if (fileInfo) {
        fileInfo.remove();
    }
    
    // Create and add new file info
    const newFileInfo = createRNAmigos2CifFileInfoElement(file);
    fileUpload.appendChild(newFileInfo);
}

// Create RNAmigos2 CIF file info element
function createRNAmigos2CifFileInfoElement(file) {
    const fileInfo = document.createElement('div');
    fileInfo.className = 'file-info-content';
    fileInfo.style.display = 'flex';
    
    // Use the same icon logic as other file uploads
    const fileExtension = file.name.split('.').pop().toLowerCase();
    const iconClass = fileExtension === 'cif' || fileExtension === 'mmcif' ? 'fa-file-code' : 'fa-file-alt';
    
    fileInfo.innerHTML = `
        <i class="fas ${iconClass}"></i>
        <div class="file-details">
            <div class="file-name">${file.name}</div>
            <div class="file-size">${formatFileSize(file.size)}</div>
                    </div>
        <button class="btn-remove-file" onclick="event.stopPropagation(); removeRNAmigos2CifFile()">
            <i class="fas fa-times"></i>
        </button>
    `;
    
    return fileInfo;
}

// Remove RNAmigos2 CIF file
function removeRNAmigos2CifFile() {
    const fileUpload = document.getElementById('rnamigos2FileUpload');
    const fileInput = document.getElementById('rnamigos2FileInput');
    
    if (!fileUpload || !fileInput) return;
    
    // Clear file input
    fileInput.value = '';
    
    // Hide file info and show upload content
    const fileInfo = fileUpload.querySelector('.file-info-content');
    if (fileInfo) {
        fileInfo.style.display = 'none';
    }
    
    const inputPlaceholder = fileUpload.querySelector('.input-placeholder');
    if (uploadContent) {
        uploadContent.style.display = 'flex';
    }
    
    // Clear stored file content
    fileUpload.removeAttribute('data-file-content');
}


// Check and toggle file upload area based on textarea content
function checkAndToggleFileUpload() {
    const standardInputAreas = document.querySelectorAll('.standard-input-area');
    
    standardInputAreas.forEach(area => {
        const textarea = area.querySelector('textarea');
        const fileUpload = area.querySelector('.file-upload-area');
        
        if (textarea && fileUpload) {
            const hasContent = textarea.value.trim().length > 0;
            
            if (hasContent) {
                // Disable file upload area when textarea has content
                fileUpload.style.pointerEvents = 'none';
                fileUpload.style.opacity = '0.6';
                fileUpload.style.cursor = 'not-allowed';
                fileUpload.setAttribute('data-disabled', 'true');
            } else {
                // Enable file upload area when textarea is empty
                fileUpload.style.pointerEvents = '';
                fileUpload.style.opacity = '';
                fileUpload.style.cursor = '';
                fileUpload.removeAttribute('data-disabled');
            }
        }
    });
}


// Reformer RBP-Cell Line combination data
const rbpCellLineCombinations = {
    "AARS": ["K562"],
    "AATF": ["K562"],
    "ABCF1": ["K562"],
    "AGGF1": ["HepG2", "K562"],
    "AKAP1": ["HepG2", "K562"],
    "AKAP8L": ["K562"],
    "APOBEC3C": ["K562"],
    "AQR": ["HepG2", "K562"],
    "BCCIP": ["HepG2"],
    "BCLAF1": ["HepG2"],
    "BUD13": ["HepG2", "K562"],
    "CDC40": ["HepG2"],
    "CPEB4": ["K562"],
    "CPSF6": ["K562"],
    "CSTF2": ["HepG2"],
    "CSTF2T": ["HepG2", "K562"],
    "DDX21": ["K562"],
    "DDX24": ["K562"],
    "DDX3X": ["HepG2", "K562"],
    "DDX42": ["K562"],
    "DDX51": ["K562"],
    "DDX52": ["HepG2", "K562"],
    "DDX55": ["HepG2", "K562"],
    "DDX59": ["HepG2"],
    "DDX6": ["HepG2", "K562"],
    "DGCR8": ["HepG2", "K562", "adrenal_gland"],
    "DHX30": ["HepG2", "K562"],
    "DKC1": ["HepG2"],
    "DROSHA": ["HepG2", "K562"],
    "EFTUD2": ["HepG2", "K562"],
    "EIF3D": ["HepG2"],
    "EIF3G": ["K562"],
    "EIF3H": ["HepG2"],
    "EIF4G2": ["K562"],
    "EWSR1": ["K562"],
    "EXOSC5": ["HepG2", "K562"],
    "FAM120A": ["HepG2", "K562"],
    "FASTKD2": ["HepG2", "K562"],
    "FKBP4": ["HepG2"],
    "FMR1": ["K562"],
    "FTO": ["HepG2", "K562"],
    "FUBP3": ["HepG2"],
    "FUS": ["HepG2", "K562"],
    "FXR1": ["K562"],
    "FXR2": ["HepG2", "K562"],
    "G3BP1": ["HepG2"],
    "GEMIN5": ["K562"],
    "GNL3": ["K562"],
    "GPKOW": ["K562"],
    "GRSF1": ["HepG2"],
    "GRWD1": ["HepG2", "K562"],
    "GTF2F1": ["HepG2", "K562"],
    "HLTF": ["HepG2", "K562"],
    "HNRNPA1": ["HepG2", "K562"],
    "HNRNPC": ["HepG2", "K562"],
    "HNRNPK": ["HepG2", "K562"],
    "HNRNPL": ["HepG2", "K562"],
    "HNRNPM": ["HepG2", "K562"],
    "HNRNPU": ["HepG2", "K562", "adrenal_gland"],
    "HNRNPUL1": ["HepG2", "K562"],
    "IGF2BP1": ["HepG2", "K562"],
    "IGF2BP2": ["K562"],
    "IGF2BP3": ["HepG2"],
    "ILF3": ["HepG2", "K562"],
    "KHDRBS1": ["K562"],
    "KHSRP": ["HepG2", "K562"],
    "LARP4": ["HepG2", "K562"],
    "LARP7": ["HepG2", "K562"],
    "LIN28B": ["HepG2", "K562"],
    "LSM11": ["HepG2", "K562"],
    "MATR3": ["HepG2", "K562"],
    "METAP2": ["K562"],
    "MTPAP": ["K562"],
    "NCBP2": ["HepG2", "K562"],
    "NIP7": ["HepG2"],
    "NIPBL": ["K562"],
    "NKRF": ["HepG2"],
    "NOL12": ["HepG2"],
    "NOLC1": ["HepG2", "K562"],
    "NONO": ["K562"],
    "NPM1": ["K562"],
    "NSUN2": ["K562"],
    "PABPC4": ["K562"],
    "PABPN1": ["HepG2"],
    "PCBP1": ["HepG2", "K562"],
    "PCBP2": ["HepG2"],
    "PHF6": ["K562"],
    "POLR2G": ["HepG2"],
    "PPIG": ["HepG2"],
    "PPIL4": ["K562"],
    "PRPF4": ["HepG2"],
    "PRPF8": ["HepG2", "K562"],
    "PTBP1": ["HepG2", "K562"],
    "PUM1": ["K562"],
    "PUM2": ["K562"],
    "PUS1": ["K562"],
    "QKI": ["HepG2", "K562"],
    "RBFOX2": ["HepG2", "K562"],
    "RBM15": ["HepG2", "K562"],
    "RBM22": ["HepG2", "K562"],
    "RBM5": ["HepG2"],
    "RPS11": ["K562"],
    "RPS3": ["HepG2", "K562"],
    "SAFB": ["HepG2", "K562"],
    "SAFB2": ["K562"],
    "SBDS": ["K562"],
    "SDAD1": ["HepG2", "K562"],
    "SERBP1": ["K562"],
    "SF3A3": ["HepG2"],
    "SF3B1": ["K562"],
    "SF3B4": ["HepG2", "K562"],
    "SFPQ": ["HepG2"],
    "SLBP": ["K562"],
    "SLTM": ["HepG2", "K562"],
    "SMNDC1": ["HepG2", "K562"],
    "SND1": ["HepG2", "K562"],
    "SRSF1": ["HepG2", "K562"],
    "SRSF7": ["HepG2", "K562"],
    "SRSF9": ["HepG2"],
    "SSB": ["HepG2", "K562"],
    "STAU2": ["HepG2"],
    "SUB1": ["HepG2"],
    "SUGP2": ["HepG2"],
    "SUPV3L1": ["HepG2", "K562"],
    "TAF15": ["HepG2", "K562"],
    "TARDBP": ["K562"],
    "TBRG4": ["HepG2", "K562"],
    "TIA1": ["HepG2", "K562"],
    "TIAL1": ["HepG2"],
    "TRA2A": ["HepG2", "K562"],
    "TROVE2": ["HepG2", "K562"],
    "U2AF1": ["HepG2", "K562"],
    "U2AF2": ["HepG2", "K562"],
    "UCHL5": ["HepG2", "K562"],
    "UPF1": ["HepG2", "K562"],
    "UTP18": ["HepG2", "K562"],
    "UTP3": ["K562"],
    "WDR3": ["K562"],
    "WDR43": ["HepG2", "K562"],
    "WRN": ["K562"],
    "XPO5": ["HepG2"],
    "XRCC6": ["HepG2", "K562"],
    "XRN2": ["HepG2", "K562"],
    "YBX3": ["HepG2", "K562"],
    "YWHAG": ["K562"],
    "ZC3H11A": ["HepG2", "K562"],
    "ZC3H8": ["K562"],
    "ZNF622": ["K562"],
    "ZNF800": ["HepG2", "K562"],
    "ZRANB2": ["K562"]
};

// Update Reformer cell line options
function updateReformerCellLineOptions() {
    const rbpSelect = document.getElementById('reformerRbpName');
    const cellLineSelect = document.getElementById('reformerCellLine');
    
    if (!rbpSelect || !cellLineSelect) return;
    
    const selectedRbp = rbpSelect.value;
    const supportedCellLines = rbpCellLineCombinations[selectedRbp] || [];
    
    // Clear existing options
    cellLineSelect.innerHTML = '';
    
    // Add supported cell line options
    supportedCellLines.forEach(cellLine => {
        const option = document.createElement('option');
        option.value = cellLine;
        option.textContent = cellLine === 'adrenal_gland' ? 'Adrenal Gland' : cellLine;
        cellLineSelect.appendChild(option);
    });
    
    // If no supported cell lines, add notice
    if (supportedCellLines.length === 0) {
        const option = document.createElement('option');
        option.value = '';
        option.textContent = 'No supported cell lines';
        option.disabled = true;
        cellLineSelect.appendChild(option);
    }
}

// Reformer Analysis Function
async function runReformerAnalysis() {
    // Get input sequence from standard-input-area
    const rnaSequenceInputArea = document.getElementById('reformerSequenceInputArea');
    const rnaSequenceTextarea = document.getElementById('reformerSequence');
    const rnaSequenceFileInput = document.getElementById('reformerSequenceFileInput');
    
    console.log('Reformer Analysis Debug:');
    console.log('rnaSequenceInputArea:', rnaSequenceInputArea);
    console.log('rnaSequenceTextarea:', rnaSequenceTextarea);
    console.log('rnaSequenceFileInput:', rnaSequenceFileInput);
    
    let sequence = rnaSequenceTextarea ? rnaSequenceTextarea.value.trim() : '';
    
    // Check if file content is available
    if (rnaSequenceInputArea && rnaSequenceInputArea.hasAttribute('data-file-content')) {
        const fileContent = rnaSequenceInputArea.getAttribute('data-file-content').trim();
        console.log('File content found:', fileContent ? 'Yes' : 'No');
        if (fileContent) {
            sequence = fileContent;
        }
    }
    
    console.log('Final sequence length:', sequence.length);
    console.log('Sequence preview:', sequence.substring(0, 50) + '...');
    
    // Validate input
    if (!sequence) {
        throw new Error('Please provide cDNA sequence');
    }
    
    // Get parameters
    const rbpName = document.getElementById('reformerRbpName').value;
    const cellLine = document.getElementById('reformerCellLine').value;
    
    // Validate RBP-cell line combination
    const supportedCellLines = rbpCellLineCombinations[rbpName] || [];
    if (!supportedCellLines.includes(cellLine)) {
        throw new Error(`Invalid combination: ${rbpName} does not support ${cellLine} cell line. Supported cell lines: ${supportedCellLines.join(', ')}`);
    }
    
    // Prepare request data
    const requestData = {
        sequence: sequence,
        rbp_name: rbpName,
        cell_line: cellLine
    };
    
    // Send request to API
    const response = await fetch('/api/reformer/predict', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify(requestData)
    });
    
    if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
    }
    
    // Parse the response and store for download functionality
    const result = await response.json();
    window.currentResult = result;
    
    return result;
}

// Display Reformer Results
function displayReformerResults(result) {
    if (!result.success) {
        return `<div class="error-message">Error: ${result.error}</div>`;
    }
    
    const bindingScores = result.binding_scores || [];
    const maxScore = result.max_score || 0;
    const meanScore = result.mean_score || 0;
    const sequenceLength = result.sequence_length || 0;
    const rbpName = result.rbp_name || 'Unknown';
    const cellLine = result.cell_line || 'Unknown';
    
    if (bindingScores.length === 0) {
        return `<div class="alert alert-warning">No binding affinity predictions found</div>`;
    }
    
    // Store results globally for download functionality
    window.currentResult = result;
    
    // Calculate score statistics
    const scores = bindingScores;
    const bestScore = Math.max(...scores);
    const worstScore = Math.min(...scores);
    const avgScore = (scores.reduce((sum, score) => sum + score, 0) / scores.length).toFixed(4);
    
    let html = '<div class="rnamigos2-results">';
    
    // Summary information in RNAmigos2 style (rounded color blocks)
    html += `
        <div class="result-item">
            <h6><i class="fas fa-dna"></i>Binding Affinity Prediction Results</h6>
            <div class="sequence-info">
                <div class="sequence-info-stats">
                    <div class="sequence-length">Max Score: ${maxScore.toFixed(4)}</div>
                    <div class="sequence-length">Mean Score: ${meanScore.toFixed(4)}</div>
                    <div class="sequence-length">Sequence Length: ${sequenceLength} bp</div>
                    <div class="sequence-length">RBP: ${rbpName}</div>
                    <div class="sequence-length">Cell Line: ${cellLine}</div>
                </div>
            </div>
        </div>
    `;
    
    // Add binding scores table with centered text (RNAmigos2 style)
    const tableRows = bindingScores.map((score, index) => {
        let scoreClass = 'score-low';
        if (score > 0.7) scoreClass = 'score-high';
        else if (score > 0.4) scoreClass = 'score-medium';
        
        return `
            <tr>
                <td class="text-center">${index + 1}</td>
                <td class="score-cell ${scoreClass} text-center">${score.toFixed(4)}</td>
                <td class="${scoreClass} text-center">${score > 0.7 ? 'High' : score > 0.4 ? 'Medium' : 'Low'}</td>
            </tr>
        `;
    });
    
    html += `
        <div class="result-item">
            <h6><i class="fas fa-chart-line"></i>Binding Scores by Position</h6>
            <div class="interactions-table">
                <table>
                    <thead>
                        <tr>
                            <th>Position</th>
                            <th>Binding Score</th>
                            <th>Score Level</th>
                        </tr>
                    </thead>
                    <tbody>
                        ${tableRows.join('')}
                    </tbody>
                </table>
            </div>
        </div>
    `;
    
    html += '</div>';
    
    return html;
}

// Display CoPRA Results
function displayCoPRAResults(result) {
    if (!result.success) {
        return `<div class="error-message">Error: ${result.error}</div>`;
    }
    
    const prediction = result.prediction || {};
    const bindingAffinity = prediction.binding_affinity || 0;
    const confidence = prediction.confidence || 0;
    const unit = prediction.unit || 'kcal/mol';
    
    // Store results globally for download functionality
    window.currentResult = result;
    
    let html = '<div class="rnamigos2-results">';
    
    // Summary information - only binding affinity and confidence
    html += `
        <div class="result-item">
            <h6><i class="fas fa-dna"></i>Binding Affinity Prediction Results</h6>
            <div class="sequence-info">
                <div class="sequence-info-stats">
                    <div class="sequence-length">Binding Affinity: ${bindingAffinity.toFixed(3)} ${unit}</div>
                    <div class="sequence-length">Confidence: ${(confidence * 100).toFixed(1)}%</div>
                </div>
            </div>
        </div>
    `;
    
    html += '</div>';
    
    return html;
}

// Run RiboDiffusion analysis
async function runRiboDiffusionAnalysis() {
    try {
        // Get PDB content from textarea
        const pdbContentElement = document.getElementById('ribodiffusionPdbContent');
        let pdbContent = pdbContentElement?.value.trim();
        
        // If no content in textarea, check if file was uploaded
        if (!pdbContent) {
            const unifiedInput = document.getElementById('ribodiffusionPdbUnifiedInput');
            const fileContent = unifiedInput?.getAttribute('data-file-content');
            if (fileContent) {
                pdbContent = fileContent.trim();
            }
        }
        
        // If still no content, check if file was selected directly
        let pdbFile = document.getElementById('ribodiffusionPdbFileInput')?.files[0];
        if (!pdbContent && !pdbFile) {
            return {
                success: false,
                error: 'PDB content or file is required for RiboDiffusion analysis'
            };
        }
        
        // If we have content but no file, create a file from content
        if (pdbContent && !pdbFile) {
            const blob = new Blob([pdbContent], { type: 'text/plain' });
            pdbFile = new File([blob], 'input.pdb', { type: 'text/plain' });
        }
        
        // Get parameters
        const numSamples = parseInt(document.getElementById('ribodiffusionNumSamples')?.value || '1');
        const samplingSteps = parseInt(document.getElementById('ribodiffusionSamplingSteps')?.value || '50');
        const condScale = parseFloat(document.getElementById('ribodiffusionCondScale')?.value || '-1.0');
        const dynamicThreshold = true; // Always set to true
        
        // Validate parameters
        if (numSamples < 1 || numSamples > 10) {
            return {
                success: false,
                error: 'Number of samples must be between 1 and 10'
            };
        }
        
        if (samplingSteps < 10 || samplingSteps > 1000) {
            return {
                success: false,
                error: 'Sampling steps must be between 10 and 1000'
            };
        }
        
        if (condScale < -1.0 || condScale > 2.0) {
            return {
                success: false,
                error: 'Conditional scale must be between -1.0 and 2.0'
            };
        }
        
        // Create FormData for file upload
        const formData = new FormData();
        formData.append('pdb_file', pdbFile);
        formData.append('num_samples', numSamples);
        formData.append('sampling_steps', samplingSteps);
        formData.append('cond_scale', condScale);
        formData.append('dynamic_threshold', dynamicThreshold);
        
        // Call RiboDiffusion API
        const response = await fetch('/api/ribodiffusion/inverse_fold', {
            method: 'POST',
            body: formData
        });
        
        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.error || `HTTP error! status: ${response.status}`);
        }
        
        const result = await response.json();
        
        if (!result.success) {
            throw new Error(result.error || 'RiboDiffusion analysis failed');
        }
        
        return result;
        
    } catch (error) {
        console.error('RiboDiffusion analysis error:', error);
        return {
            success: false,
            error: error.message || 'RiboDiffusion analysis failed'
        };
    }
}

// Display RiboDiffusion results
function displayRiboDiffusionResults(result) {
    if (!result.success) {
        return `<div class="error-message">Error: ${result.error}</div>`;
    }
    
    const data = result.data || {};
    const sequences = data.sequences || [];
    
    // Store results globally for download functionality
    window.currentRiboDiffusionResult = result;
    
    let html = '<div class="ribodiffusion-results">';
    
    // Display generated sequences in table format
    if (sequences.length > 0) {
        html += `
            <div class="result-item">
                <h6><i class="fas fa-list"></i>Generated RNA Sequences</h6>
                <div class="interactions-table">
                    <table>
                        <thead>
                            <tr>
                                <th>Sequence ID</th>
                                <th>Sequence Content</th>
                            </tr>
                        </thead>
                        <tbody>
        `;
        
        sequences.forEach((sequence, index) => {
            html += `
                <tr>
                    <td class="sequence-id-cell">Sequence ${index + 1}</td>
                    <td class="sequence-cell">${sequence}</td>
                </tr>
            `;
        });
        
        html += `
                        </tbody>
                    </table>
                </div>
            </div>
        `;
    }
    
    html += '</div>';
    
    return html;
}

// Download all RiboDiffusion results
function downloadAllRiboDiffusionResults() {
    // Get the current result data from the global result storage
    if (!window.currentRiboDiffusionResult || !window.currentRiboDiffusionResult.success) {
        showNotification('No RiboDiffusion results to download', 'warning');
        return;
    }
    
    const result = window.currentRiboDiffusionResult;
    const data = result.data || {};
    const sequences = data.sequences || [];
    
    if (sequences.length === 0) {
        showNotification('No sequences available for download', 'warning');
        return;
    }
    
    // Create CSV content
    let csvContent = 'Sequence ID,Sequence Content\n';
    
    sequences.forEach((sequence, index) => {
        const sequenceId = `Sequence ${index + 1}`;
        csvContent += `"${sequenceId}","${sequence}"\n`;
    });
    
    // Create and download the file
    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
    const link = document.createElement('a');
    const url = URL.createObjectURL(blob);
    link.setAttribute('href', url);
    link.setAttribute('download', 'ribodiffusion_sequences.csv');
    link.style.visibility = 'hidden';
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    
    showNotification('RiboDiffusion sequences downloaded successfully', 'success');
}

// Download all Reformer results
function downloadAllReformerResults() {
    // Get the current result data from the global result storage
    if (!window.currentResult || !window.currentResult.success) {
        showNotification('No results to download', 'warning');
        return;
    }
    
    const result = window.currentResult;
    const bindingScores = result.binding_scores || [];
    const maxScore = result.max_score || 0;
    const meanScore = result.mean_score || 0;
    const sequenceLength = result.sequence_length || 0;
    const rbpName = result.rbp_name || 'Unknown';
    const cellLine = result.cell_line || 'Unknown';
    
    // Create CSV content
    let csvContent = 'Reformer Binding Affinity Prediction Results\n';
    csvContent += `RBP: ${rbpName}\n`;
    csvContent += `Cell Line: ${cellLine}\n`;
    csvContent += `Sequence Length: ${sequenceLength} bp\n`;
    csvContent += `Max Binding Score: ${maxScore.toFixed(4)}\n`;
    csvContent += `Mean Binding Score: ${meanScore.toFixed(4)}\n`;
    csvContent += '\n';
    csvContent += 'Position,Binding_Score,Score_Level\n';
    
    // Add binding scores data
    for (let i = 0; i < bindingScores.length; i++) {
        const score = bindingScores[i];
        let scoreLevel = 'Low';
        if (score > 0.7) scoreLevel = 'High';
        else if (score > 0.4) scoreLevel = 'Medium';
        
        csvContent += `${i + 1},${score.toFixed(4)},${scoreLevel}\n`;
    }
    
    // Create and download CSV file
    const blob = new Blob([csvContent], { type: 'text/csv' });
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `reformer_${rbpName}_${cellLine}_binding_scores.csv`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    window.URL.revokeObjectURL(url);
    
    showNotification('Reformer results downloaded successfully!', 'success');
}

// Banner scroll effects
function initializeBannerScroll() {
    const bannerSection = document.getElementById('bannerSection');
    
    if (!bannerSection) return;
    
    let isScrolled = false;
    const scrollThreshold = 50; // 增加阈值，使切换更平滑
    
    function handleScroll() {
        const scrollTop = window.pageYOffset || document.documentElement.scrollTop;
        
        if (scrollTop > scrollThreshold && !isScrolled) {
            bannerSection.classList.add('scrolled');
            isScrolled = true;
        } else if (scrollTop <= scrollThreshold && isScrolled) {
            bannerSection.classList.remove('scrolled');
            isScrolled = false;
        }
    }
    
    // Throttle scroll event for better performance
    let ticking = false;
    function requestTick() {
        if (!ticking) {
            requestAnimationFrame(handleScroll);
            ticking = true;
        }
    }
    
    function onScroll() {
        ticking = false;
        requestTick();
    }
    
    // Add scroll listener
    window.addEventListener('scroll', onScroll, { passive: true });
    
    // Initial check
    handleScroll();
}

// GitHub button functionality
function openGitHub() {
    window.open('https://github.com/givemeone1astkiss/RNA-Factory', '_blank');
}

// CoPRA Analysis Functions
async function runCoPRAAnalysis() {
    try {
        // Get input data from CoPRA specific input areas
        const proteinSequence = document.getElementById('copraProteinSequence')?.value?.trim();
        const rnaSequence = document.getElementById('copraRnaSequence')?.value?.trim();
        
        if (!proteinSequence || !rnaSequence) {
            return {
                success: false,
                error: 'Both protein sequence and RNA sequence are required for CoPRA analysis'
            };
        }
        
        // Validate sequences
        if (!isValidProteinSequence(proteinSequence)) {
            return {
                success: false,
                error: 'Invalid protein sequence. Only standard amino acid codes (A, C, D, E, F, G, H, I, K, L, M, N, P, Q, R, S, T, V, W, Y) are allowed.'
            };
        }
        
        if (!isValidRnaSequence(rnaSequence)) {
            return {
                success: false,
                error: 'Invalid RNA sequence. Only A, U, G, C are allowed.'
            };
        }
        
        // Call CoPRA API
        const response = await fetch('/api/copra/predict', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                protein_sequence: proteinSequence,
                rna_sequence: rnaSequence
            })
        });
        
        const result = await response.json();
        
        if (result.success) {
            // Format result for display
            return {
                success: true,
                result: {
                    model_type: 'protein_rna_interaction',
                    binding_affinity: result.prediction.binding_affinity,
                    confidence: result.prediction.confidence,
                    unit: result.prediction.unit,
                    protein_sequence: result.input.protein_sequence,
                    rna_sequence: result.input.rna_sequence,
                    method: result.model,
                    metadata: result.metadata
                }
            };
        } else {
            return {
                success: false,
                error: result.error || 'CoPRA prediction failed'
            };
        }
        
    } catch (error) {
        return {
            success: false,
            error: `CoPRA analysis failed: ${error.message}`
        };
    }
}

// Validation functions
function isValidProteinSequence(sequence) {
    const validAA = /^[ACDEFGHIKLMNPQRSTVWY]+$/i;
    return validAA.test(sequence);
}

function isValidRnaSequence(sequence) {
    const validBases = /^[AUCG]+$/i;
    return validBases.test(sequence);
}

// Initialize banner scroll effects when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    initializeBannerScroll();
});

// Ensure scroll position is reset when page is fully loaded
window.addEventListener('load', function() {
    // Reset scroll position to top after all resources are loaded
    window.scrollTo(0, 0);
    
    // Also reset scroll position after a short delay to handle any dynamic content
    setTimeout(function() {
        window.scrollTo(0, 0);
    }, 100);
});
