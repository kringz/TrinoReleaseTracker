$(document).ready(function() {
    // Handle form submission
    $('#comparisonForm').on('submit', function(e) {
        e.preventDefault();
        
        const fromVersion = $('#fromVersion').val();
        const toVersion = $('#toVersion').val();
        
        if (!fromVersion || !toVersion) {
            alert('Please select both versions to compare');
            return;
        }
        
        // Show loading overlay
        $('#loadingOverlay').show();
        
        // Clear previous results
        $('#connector-list').html('');
        $('#connector-details').html('');
        
        // Make AJAX request to compare versions
        $.ajax({
            url: '/api/compare_versions',
            type: 'POST',
            data: $(this).serialize(),
            dataType: 'json',
            success: function(data) {
                // Update comparison header
                $('#comparison-header').text(`Changes from Trino ${data.from_version} to Trino ${data.to_version}`);
                
                // Process connector data
                processConnectorData(data);
                
                // Show results
                $('#comparison-results').show();
                
                // Hide loading overlay
                $('#loadingOverlay').hide();
                
                // Scroll to results
                $('html, body').animate({
                    scrollTop: $('#comparison-results').offset().top - 20
                }, 500);
            },
            error: function(xhr, status, error) {
                // Hide loading overlay
                $('#loadingOverlay').hide();
                
                // Show error message
                alert('Error comparing versions: ' + (xhr.responseJSON ? xhr.responseJSON.error : error));
            }
        });
    });
    
    // Handle connector search
    $('#connector-search').on('input', function() {
        const searchTerm = $(this).val().toLowerCase();
        
        $('.connector-link').each(function() {
            const connectorName = $(this).text().toLowerCase();
            if (connectorName.includes(searchTerm)) {
                $(this).show();
            } else {
                $(this).hide();
            }
        });
    });
    
    // Function to process and display connector data
    function processConnectorData(data) {
        const connectors = data.connectors;
        const connectorList = $('#connector-list');
        const connectorDetails = $('#connector-details');
        
        if (!connectors || Object.keys(connectors).length === 0) {
            connectorDetails.html(`
                <div class="alert alert-info">
                    <i class="fas fa-info-circle me-2"></i>
                    No changes found between Trino ${data.from_version} and Trino ${data.to_version}.
                </div>
            `);
            return;
        }
        
        // Sort connectors alphabetically, but keep "General" at the top
        const sortedConnectors = Object.keys(connectors).sort((a, b) => {
            if (a === 'General') return -1;
            if (b === 'General') return 1;
            return a.localeCompare(b);
        });
        
        // Populate connector list
        sortedConnectors.forEach(connector => {
            const breakingCount = connectors[connector].breaking_changes.length;
            const featureCount = connectors[connector].new_features.length;
            const totalCount = breakingCount + featureCount;
            
            const connectorItem = $(`
                <a href="#${connector.replace(/\s+/g, '-')}" class="list-group-item list-group-item-action d-flex justify-content-between align-items-center connector-link">
                    ${connector}
                    <span class="badge bg-primary rounded-pill">${totalCount}</span>
                </a>
            `);
            
            if (breakingCount > 0) {
                connectorItem.append(`
                    <span class="badge bg-danger ms-1">${breakingCount}</span>
                `);
            }
            
            connectorList.append(connectorItem);
        });
        
        // Populate connector details
        sortedConnectors.forEach(connector => {
            const connectorData = connectors[connector];
            const connectorId = connector.replace(/\s+/g, '-');
            
            const connectorSection = $(`
                <div class="connector-section" id="${connectorId}">
                    <div class="card connector-card">
                        <div class="card-header">
                            <div class="connector-title">
                                <i class="fas fa-plug me-2"></i>
                                <h3 class="mb-0">${connector} Connector</h3>
                            </div>
                            <div>
                                <span class="badge bg-danger">${connectorData.breaking_changes.length} Breaking</span>
                                <span class="badge bg-success">${connectorData.new_features.length} Features</span>
                            </div>
                        </div>
                        <div class="card-body">
                            <div class="changes-container">
                                <!-- Breaking changes -->
                                ${connectorData.breaking_changes.length > 0 ? `
                                    <h4 class="text-danger mb-3">
                                        <i class="fas fa-exclamation-triangle me-2"></i>
                                        Breaking Changes
                                    </h4>
                                    <div class="breaking-changes mb-4">
                                        ${connectorData.breaking_changes.map(change => `
                                            <div class="change-item breaking">
                                                <span class="version-pill badge bg-secondary">v${change.version}</span>
                                                <p class="mb-0">${change.description}</p>
                                            </div>
                                        `).join('')}
                                    </div>
                                ` : ''}
                                
                                <!-- New features -->
                                ${connectorData.new_features.length > 0 ? `
                                    <h4 class="text-success mb-3">
                                        <i class="fas fa-star me-2"></i>
                                        New Features
                                    </h4>
                                    <div class="new-features">
                                        ${connectorData.new_features.map(feature => `
                                            <div class="change-item feature">
                                                <span class="version-pill badge bg-secondary">v${feature.version}</span>
                                                <p class="mb-0">${feature.description}</p>
                                            </div>
                                        `).join('')}
                                    </div>
                                ` : ''}
                                
                                ${connectorData.breaking_changes.length === 0 && connectorData.new_features.length === 0 ? `
                                    <div class="alert alert-info">
                                        <i class="fas fa-info-circle me-2"></i>
                                        No changes detected for this connector between these versions.
                                    </div>
                                ` : ''}
                            </div>
                        </div>
                    </div>
                </div>
            `);
            
            connectorDetails.append(connectorSection);
        });
        
        // Attach click event to connector links
        $('.connector-link').on('click', function(e) {
            e.preventDefault();
            const target = $(this).attr('href');
            $('html, body').animate({
                scrollTop: $(target).offset().top - 20
            }, 400);
        });
    }
    
    // Expand/collapse all functionality
    $('#expand-all').on('click', function() {
        $('.collapse').collapse('show');
    });
    
    $('#collapse-all').on('click', function() {
        $('.collapse').collapse('hide');
    });
});
