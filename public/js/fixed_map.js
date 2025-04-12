document.addEventListener('DOMContentLoaded', function () {
    const mapFrame = document.getElementById('mapFrame');
    const smaButton = document.getElementById('smaButton');
    const smkButton = document.getElementById('smkButton');
    const cluster0Checkbox = document.getElementById('cluster0');
    const cluster1Checkbox = document.getElementById('cluster1');
    const cluster2Checkbox = document.getElementById('cluster2');
    const mapStatus = document.getElementById('mapStatus');
    const totalClusters = document.getElementById('totalClusters');
    
    let currentMapType = 'sma';

    // Function to update the map
    function updateMap() {
        // Gather selected clusters
        const selectedClusters = [];
        if (cluster0Checkbox.checked) selectedClusters.push('0');
        if (cluster1Checkbox.checked) selectedClusters.push('1');
        if (cluster2Checkbox.checked) selectedClusters.push('2');
        
        // Jika tidak ada cluster yang dipilih, pilih semua cluster
        if (selectedClusters.length === 0) {
            cluster0Checkbox.checked = true;
            cluster1Checkbox.checked = true;
            cluster2Checkbox.checked = true;
            selectedClusters.push('0', '1', '2');
        }
        
        // Update iframe src directly to avoid duplicating content
        const newSrc = `/api/map/${currentMapType}?clusters=${selectedClusters.join(',')}`;
        mapFrame.src = newSrc;
        
        // Update map status text
        if (mapStatus) {
            const typeText = currentMapType === 'sma' ? 'SMA' : 'SMK';
            let clusterText = '';
            
            if (selectedClusters.length === 3) {
                clusterText = 'seluruh klaster';
            } else if (selectedClusters.length === 1) {
                clusterText = `klaster ${selectedClusters[0]}`;
            } else {
                clusterText = `klaster ${selectedClusters.join(' dan ')}`;
            }
            
            mapStatus.textContent = `Menampilkan hasil klasterisasi ${typeText} untuk ${clusterText}`;
        }
        
        // Update statistik cluster
        fetchClusterCounts(selectedClusters);
    }

    // Event listeners for school type buttons
    if (smaButton) {
        smaButton.addEventListener('click', function() {
            if (currentMapType === 'sma') return;
            
            smaButton.classList.remove('bg-gray-200', 'text-gray-700');
            smaButton.classList.add('bg-blue-500', 'text-white');
            
            smkButton.classList.remove('bg-blue-500', 'text-white');
            smkButton.classList.add('bg-gray-200', 'text-gray-700');
            
            currentMapType = 'sma';
            updateMap();
        });
    }

    if (smkButton) {
        smkButton.addEventListener('click', function() {
            if (currentMapType === 'smk') return;
            
            smkButton.classList.remove('bg-gray-200', 'text-gray-700');
            smkButton.classList.add('bg-blue-500', 'text-white');
            
            smaButton.classList.remove('bg-blue-500', 'text-white');
            smaButton.classList.add('bg-gray-200', 'text-gray-700');
            
            currentMapType = 'smk';
            updateMap();
        });
    }

    // Event listeners for checkboxes
    if (cluster0Checkbox) cluster0Checkbox.addEventListener('change', updateMap);
    if (cluster1Checkbox) cluster1Checkbox.addEventListener('change', updateMap);
    if (cluster2Checkbox) cluster2Checkbox.addEventListener('change', updateMap);
    
    // Function to fetch updated cluster counts
    function fetchClusterCounts(selectedClusters) {
        // Get cluster counts
        fetch(`/api/cluster-counts/${currentMapType}?clusters=${selectedClusters.join(',')}`)
            .then(response => response.json())
            .then(data => {
                // Get count values
                const count0 = data['0'] || 0;
                const count1 = data['1'] || 0;
                const count2 = data['2'] || 0;
                const total = count0 + count1 + count2;
                
                // Update the count displays
                const count0Element = document.getElementById('count0');
                const count1Element = document.getElementById('count1');
                const count2Element = document.getElementById('count2');
                
                if (count0Element) count0Element.textContent = count0;
                if (count1Element) count1Element.textContent = count1;
                if (count2Element) count2Element.textContent = count2;
                if (totalClusters) totalClusters.textContent = total;
                
                // Update progress bars if they exist
                updateProgressBar('progress0', 'percent0', count0, total);
                updateProgressBar('progress1', 'percent1', count1, total);
                updateProgressBar('progress2', 'percent2', count2, total);
            })
            .catch(error => {
                console.error('Error fetching cluster counts:', error);
            });
    }
    
    // Function to update progress bar
    function updateProgressBar(progressId, percentId, count, total) {
        const progressElement = document.getElementById(progressId);
        const percentElement = document.getElementById(percentId);
        
        if (progressElement && percentElement && total > 0) {
            const percent = Math.round((count / total) * 100);
            progressElement.style.width = `${percent}%`;
            percentElement.textContent = `${percent}%`;
        }
    }
    
    // Init map type based on initial URL
    if (mapFrame) {
        const mapSrc = mapFrame.src;
        if (mapSrc.includes('map_smk.html')) {
            currentMapType = 'smk';
            if (smkButton) smkButton.click();
        } else {
            // Update initial map status
            if (mapStatus) {
                mapStatus.textContent = `Menampilkan hasil klasterisasi SMA untuk seluruh klaster`;
            }
        }
    }
});