document.addEventListener('DOMContentLoaded', function() {
    // Tab navigation functionality
    const tabButtons = document.querySelectorAll('.tab-btn');
    const tabContents = document.querySelectorAll('.tab-pane');
    
    tabButtons.forEach(button => {
        button.addEventListener('click', () => {
            // Remove active class from all buttons and contents
            tabButtons.forEach(btn => {
                btn.classList.remove('active');
                btn.classList.remove('text-purple-600');
                btn.classList.remove('border-purple-600');
                btn.classList.add('border-transparent');
            });
            
            tabContents.forEach(content => content.classList.add('hidden'));
            
            // Add active class to clicked button
            button.classList.add('active');
            button.classList.add('text-purple-600');
            button.classList.add('border-purple-600');
            button.classList.remove('border-transparent');
            
            // Show corresponding content
            const targetId = button.getAttribute('data-target');
            const targetContent = document.getElementById(targetId);
            targetContent.classList.remove('hidden');
        });
    });
    
    // Result tab navigation functionality (within hasil-content)
    const resultTabButtons = document.querySelectorAll('.result-tab-btn');
    const resultTabContents = document.querySelectorAll('.result-tab-pane');
    
    resultTabButtons.forEach(button => {
        button.addEventListener('click', () => {
            // Remove active class from all buttons and contents
            resultTabButtons.forEach(btn => {
                btn.classList.remove('active');
                btn.classList.remove('text-purple-600');
                btn.classList.remove('border-purple-600');
                btn.classList.add('border-transparent');
            });
            
            resultTabContents.forEach(content => content.classList.add('hidden'));
            
            // Add active class to clicked button
            button.classList.add('active');
            button.classList.add('text-purple-600');
            button.classList.add('border-purple-600');
            button.classList.remove('border-transparent');
            
            // Show corresponding content
            const targetId = button.getAttribute('data-target');
            const targetContent = document.getElementById(targetId);
            if (targetContent) {
                targetContent.classList.remove('hidden');
            }
        });
    });
    
    // File upload functionality
    const fileInput = document.getElementById('dataset-upload');
    const fileInfo = document.getElementById('file-info');
    const fileName = document.getElementById('file-name');
    const fileSize = document.getElementById('file-size');
    
    if (fileInput) {
        fileInput.addEventListener('change', () => {
            if (fileInput.files.length > 0) {
                const file = fileInput.files[0];
                fileName.textContent = file.name;
                
                // Format file size
                let size = file.size;
                let sizeDisplay = '';
                
                if (size < 1024) {
                    sizeDisplay = size + ' bytes';
                } else if (size < 1024 * 1024) {
                    sizeDisplay = (size / 1024).toFixed(2) + ' KB';
                } else {
                    sizeDisplay = (size / (1024 * 1024)).toFixed(2) + ' MB';
                }
                
                fileSize.textContent = sizeDisplay;
                fileInfo.classList.remove('hidden');
            } else {
                fileInfo.classList.add('hidden');
            }
        });
        
        // Handle drag and drop functionality
        const dropZone = document.querySelector('.file-upload-container');
        
        if (dropZone) {
            ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
                dropZone.addEventListener(eventName, preventDefaults, false);
            });
            
            function preventDefaults(e) {
                e.preventDefault();
                e.stopPropagation();
            }
            
            ['dragenter', 'dragover'].forEach(eventName => {
                dropZone.addEventListener(eventName, highlight, false);
            });
            
            ['dragleave', 'drop'].forEach(eventName => {
                dropZone.addEventListener(eventName, unhighlight, false);
            });
            
            function highlight() {
                dropZone.classList.add('border-purple-500');
                dropZone.classList.add('bg-purple-100');
            }
            
            function unhighlight() {
                dropZone.classList.remove('border-purple-500');
                dropZone.classList.remove('bg-purple-100');
            }
            
            dropZone.addEventListener('drop', handleDrop, false);
            
            function handleDrop(e) {
                const dt = e.dataTransfer;
                const files = dt.files;
                
                if (files.length > 0) {
                    fileInput.files = files;
                    
                    // Trigger change event manually
                    const event = new Event('change');
                    fileInput.dispatchEvent(event);
                }
            }
        }
    }
    
    // Handle optimal cluster checkbox
    const calculateOptimalCheckbox = document.getElementById('calculate-optimal');
    const clusterCountInput = document.getElementById('cluster-count');
    const findOptimalBtn = document.getElementById('find-optimal-btn');
    const optimalClusterResults = document.getElementById('optimal-cluster-results');
    const useOptimalClusterBtn = document.getElementById('use-optimal-cluster-btn');
    
    if (calculateOptimalCheckbox && clusterCountInput) {
        calculateOptimalCheckbox.addEventListener('change', () => {
            if (calculateOptimalCheckbox.checked) {
                clusterCountInput.disabled = true;
                clusterCountInput.classList.add('opacity-50');
                findOptimalBtn.disabled = true;
                findOptimalBtn.classList.add('opacity-50');
            } else {
                clusterCountInput.disabled = false;
                clusterCountInput.classList.remove('opacity-50');
                findOptimalBtn.disabled = false;
                findOptimalBtn.classList.remove('opacity-50');
            }
        });
    }
    
    // Find optimal cluster button click
    if (findOptimalBtn) {
        findOptimalBtn.addEventListener('click', () => {
            // Show loading state
            findOptimalBtn.innerHTML = '<svg class="animate-spin h-5 w-5" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24"><circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle><path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path></svg>';
            findOptimalBtn.disabled = true;
            
            // Simulate API call to calculate optimal cluster
            setTimeout(() => {
                // Reset button
                findOptimalBtn.innerHTML = '<svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 7h6m0 10v-3m-3 3h.01M9 17h.01M9 14h.01M12 14h.01M15 11h.01M12 11h.01M9 11h.01M7 21h10a2 2 0 002-2V5a2 2 0 00-2-2H7a2 2 0 00-2 2v14a2 2 0 002 2z"></path></svg>';
                findOptimalBtn.disabled = false;
                
                // Show results
                optimalClusterResults.classList.remove('hidden');
            }, 2000);
        });
    }
    
    // Use optimal cluster button click
    if (useOptimalClusterBtn && clusterCountInput) {
        useOptimalClusterBtn.addEventListener('click', () => {
            const optimalValue = document.getElementById('optimal-cluster-value');
            if (optimalValue) {
                clusterCountInput.value = optimalValue.textContent;
            }
        });
    }
    
    // Workflow progress simulation
    simulateWorkflowProgress();
    
    // Mock API functions - These would normally interact with your Flask backend
    
    // Function to fetch datasets
    function fetchDatasets() {
        // This is a mock function - in a real app you would fetch from your API
        console.log("Fetching datasets from server...");
        // In a real application, this would be an API call like:
        // fetch('/api/datasets').then(response => response.json()).then(data => {...})
        
        // Check if we need to show demo data for the UI
        const showDemoData = document.getElementById('demo-data');
        if (showDemoData && showDemoData.value === 'true') {
            // Populate dataset list with demo data
            populateDatasetList([
                { id: 1, name: 'Data SMA 2023', description: 'Dataset SMA Kota Surabaya 2023', uploaded_at: '12 Apr 2025', status: 'ready' },
                { id: 2, name: 'Data SMK 2023', description: 'Dataset SMK Kota Surabaya 2023', uploaded_at: '10 Apr 2025', status: 'ready' }
            ]);
            
            // Show configuration form
            document.getElementById('config-empty-state').classList.add('hidden');
            document.getElementById('clustering-config-form').classList.remove('hidden');
            
            // Populate dataset select dropdown
            const datasetSelect = document.getElementById('dataset-select');
            if (datasetSelect) {
                datasetSelect.innerHTML = `
                    <option value="">-- Pilih Dataset --</option>
                    <option value="1">Data SMA 2023</option>
                    <option value="2">Data SMK 2023</option>
                `;
            }
        }
    }
    
    // Function to populate dataset list
    function populateDatasetList(datasets) {
        const datasetList = document.getElementById('dataset-list');
        const datasetTableContainer = document.getElementById('dataset-table-container');
        
        if (datasetList && datasetTableContainer) {
            if (datasets && datasets.length > 0) {
                // Hide empty state, show table
                const emptyState = datasetList.closest('.py-12');
                if (emptyState) {
                    emptyState.classList.add('hidden');
                }
                datasetTableContainer.classList.remove('hidden');
                
                // Populate table
                datasetList.innerHTML = datasets.map(dataset => `
                    <tr>
                        <td class="px-6 py-4 whitespace-nowrap">
                            <div class="text-sm font-medium text-gray-900">${dataset.name}</div>
                        </td>
                        <td class="px-6 py-4 whitespace-nowrap">
                            <div class="text-sm text-gray-500">${dataset.description}</div>
                        </td>
                        <td class="px-6 py-4 whitespace-nowrap">
                            <div class="text-sm text-gray-500">${dataset.uploaded_at}</div>
                        </td>
                        <td class="px-6 py-4 whitespace-nowrap">
                            <span class="px-2 inline-flex text-xs leading-5 font-semibold rounded-full bg-green-100 text-green-800">
                                Siap digunakan
                            </span>
                        </td>
                        <td class="px-6 py-4 whitespace-nowrap text-right text-sm font-medium">
                            <a href="#" class="text-purple-600 hover:text-purple-900 mr-3">Lihat</a>
                            <a href="#" class="text-red-600 hover:text-red-900">Hapus</a>
                        </td>
                    </tr>
                `).join('');
            }
        }
    }
    
    // Function to fetch active processes
    function fetchActiveProcesses() {
        // This is a mock function - in a real app you would fetch from your API
        console.log("Fetching active processes from server...");
    }
    
    // Function to fetch completed results
    function fetchCompletedResults() {
        // This is a mock function - in a real app you would fetch from your API
        console.log("Fetching completed results from server...");
    }
    
    // Initialize data
    fetchDatasets();
    fetchActiveProcesses();
    fetchCompletedResults();
});

// Function to simulate workflow progress
function simulateWorkflowProgress() {
    // This function is for demonstration purposes only
    // In a real application, this would be replaced with actual progress tracking from the server
    
    // Example: If there's an active process being shown, animate its progress
    const activeProcessContainer = document.getElementById('active-process-container');
    
    if (activeProcessContainer && !activeProcessContainer.classList.contains('hidden')) {
        const progressLine = document.querySelector('.workflow-progress-filled');
        
        if (progressLine) {
            // Start with 0% progress
            let progress = 0;
            
            // Simulate progress updates
            const interval = setInterval(() => {
                progress += 1;
                progressLine.style.height = progress + '%';
                
                // Update step statuses based on progress
                updateStepStatuses(progress);
                
                // If progress reaches 100%, stop the simulation
                if (progress >= 100) {
                    clearInterval(interval);
                }
            }, 200);
        }
    }
}

// Function to update step statuses based on progress
function updateStepStatuses(progress) {
    const steps = document.querySelectorAll('.workflow-step');
    
    if (steps.length > 0) {
        const stepSize = 100 / steps.length;
        
        steps.forEach((step, index) => {
            const stepIcon = step.querySelector('.workflow-step-icon');
            const stepStatus = step.querySelector('span[class*="rounded-full"]');
            
            if (progress >= (index + 1) * stepSize) {
                // Step completed
                if (stepIcon) {
                    stepIcon.classList.remove('bg-gray-200', 'text-gray-500');
                    stepIcon.classList.remove('bg-purple-500', 'animate-pulse');
                    stepIcon.classList.add('bg-green-500', 'text-white');
                    
                    // Change content to checkmark
                    stepIcon.innerHTML = `<svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"></path></svg>`;
                }
                
                if (stepStatus) {
                    stepStatus.classList.remove('bg-gray-100', 'text-gray-800');
                    stepStatus.classList.remove('bg-yellow-100', 'text-yellow-800');
                    stepStatus.classList.add('bg-green-100', 'text-green-800');
                    stepStatus.textContent = 'Selesai';
                }
            } else if (progress >= index * stepSize) {
                // Step in progress
                if (stepIcon) {
                    stepIcon.classList.remove('bg-gray-200', 'text-gray-500');
                    stepIcon.classList.remove('bg-green-500', 'text-white');
                    stepIcon.classList.add('bg-purple-500', 'text-white', 'animate-pulse');
                    
                    // Change content to loading icon
                    stepIcon.innerHTML = `<svg class="w-6 h-6 animate-spin" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"></path></svg>`;
                }
                
                if (stepStatus) {
                    stepStatus.classList.remove('bg-gray-100', 'text-gray-800');
                    stepStatus.classList.remove('bg-green-100', 'text-green-800');
                    stepStatus.classList.add('bg-yellow-100', 'text-yellow-800');
                    stepStatus.textContent = 'Sedang Berjalan';
                }
            }
        });
    }
}

// Function to show an active process in the status container
function showActiveProcess(process) {
    const activeProcessContainer = document.getElementById('active-process-container');
    
    if (activeProcessContainer) {
        // Remove empty state
        const emptyState = activeProcessContainer.closest('.p-6').querySelector('.py-12');
        if (emptyState) {
            emptyState.classList.add('hidden');
        }
        
        // Show container
        activeProcessContainer.classList.remove('hidden');
        
        // Add process details
        activeProcessContainer.innerHTML = `
            <div class="bg-white p-4 rounded-lg border border-purple-200 mb-4">
                <div class="flex justify-between items-start">
                    <div>
                        <h3 class="font-medium text-lg text-gray-900">${process.name}</h3>
                        <p class="text-sm text-gray-500 mt-1">Dataset: ${process.dataset}, Jenjang: ${process.jenjang}, Skenario: ${process.skenario}</p>
                    </div>
                    <span class="px-2 py-1 text-xs rounded-full bg-yellow-100 text-yellow-800 animate-pulse">
                        Sedang Berjalan
                    </span>
                </div>
                
                <div class="mt-4">
                    <div class="flex justify-between text-sm text-gray-500 mb-1">
                        <span>Progress</span>
                        <span>${process.progress}%</span>
                    </div>
                    <div class="w-full bg-gray-200 rounded-full h-2.5">
                        <div class="bg-purple-600 h-2.5 rounded-full" style="width: ${process.progress}%"></div>
                    </div>
                </div>
                
                <div class="mt-4 text-sm text-gray-500">
                    <p><span class="font-medium">Status:</span> ${process.status}</p>
                    <p><span class="font-medium">Tahap saat ini:</span> ${process.current_step}</p>
                    <p><span class="font-medium">Mulai:</span> ${process.start_time}</p>
                    <p><span class="font-medium">Estimasi waktu selesai:</span> ${process.estimated_end_time}</p>
                </div>
                
                <div class="mt-4 flex justify-end">
                    <button type="button" class="px-3 py-1.5 bg-red-50 text-red-600 text-sm font-medium rounded hover:bg-red-100 transition-colors">
                        Batalkan
                    </button>
                </div>
            </div>
        `;
    }
}

// Function to populate results in the hasil-content tab
function populateResults(results) {
    const resultContainer = document.getElementById('result-container');
    
    if (resultContainer) {
        // Remove empty state
        const emptyState = resultContainer.closest('.p-6').querySelector('.py-12');
        if (emptyState) {
            emptyState.classList.add('hidden');
        }
        
        // Show container
        resultContainer.classList.remove('hidden');
        
        // Add results
        // This would be a complex HTML structure based on your results
        // For example:
        resultContainer.innerHTML = `
            <div class="flex justify-between items-start mb-6">
                <div>
                    <h3 class="text-xl font-bold text-gray-800">${results.name}</h3>
                    <p class="text-gray-600">Dataset: ${results.dataset}, Jenjang: ${results.jenjang}, Skenario: ${results.skenario}</p>
                </div>
                <select class="px-4 py-2 border border-gray-300 rounded-md focus:ring-purple-500 focus:border-purple-500">
                    <option value="latest">Klasterisasi SMA 2023 (Terbaru)</option>
                    <option value="1">Klasterisasi SMA 2023 - 12 Apr 2025</option>
                    <option value="2">Klasterisasi SMK 2023 - 10 Apr 2025</option>
                </select>
            </div>
            
            <!-- Cluster Summary Cards would go here -->
            
            <!-- Cluster Statistics Tab Navigation would go here -->
            
            <!-- Cluster Statistics Tab Content would go here -->
        `;
    }
}