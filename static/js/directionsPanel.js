// Directions Panel Management
// Handles all directions functionality: panel UI, route calculation, navigation tracking

(function() {
    'use strict';
    
    // Module state
    let mapInstance = null;
    let directionsInstance = null;
    let stateInstance = null;
    let directionsCalculated = false;
    
    // Panel UI elements
    let panel = null;
    let header = null;
    let content = null;
    let collapseBtn = null;
    let closeBtn = null;
    let resizeHandle = null;
    let toggleBtn = null;
    
    // Navigation state
    let navigationWatchId = null;
    
    // Initialize panel UI elements
    function initPanelElements() {
        panel = document.getElementById("directionsPanel");
        header = document.getElementById("directionsPanelHeader");
        content = document.getElementById("directionsPanelContent");
        collapseBtn = document.getElementById("collapseDirections");
        closeBtn = document.getElementById("closeDirections");
        resizeHandle = document.getElementById("resizeHandle");
        toggleBtn = document.getElementById("directionsPanelToggle");
        
        return panel && header && content && collapseBtn && closeBtn;
    }
    
    // Function to show panel - only if route exists
    function showDirectionsPanel() {
        if (!panel) return;
        
        // Check if a route exists and has been calculated before showing
        if (!directionsInstance) {
            return; // No directions instance
        }
        
        const origin = directionsInstance.getOrigin();
        const destination = directionsInstance.getDestination();
        const hasRoute = !!(origin && destination);
        
        // Check if route has been calculated
        const hasCalculatedRoute = !!(directionsCalculated || 
                                     (stateInstance && stateInstance.directionsCalculated));
        
        if (!hasRoute || !hasCalculatedRoute) {
            // No route calculated, don't show panel
            return;
        }
        
        panel.style.display = "block";
        panel.classList.remove('hidden');
        // Reset to centered position on mobile
        if (window.innerWidth <= 767) {
            panel.style.left = '50%';
            panel.style.transform = 'translateX(-50%)';
            panel.style.right = 'auto';
            panel.style.bottom = '1rem';
            panel.style.top = 'auto';
        }
        if (toggleBtn) {
            toggleBtn.style.display = 'none';
        }
    }
    
    // Function to hide panel
    function hideDirectionsPanel() {
        if (!panel) return;
        
        panel.style.display = "none";
        panel.classList.add('hidden');
        // Only show toggle button if directions were calculated
        if (toggleBtn && directionsInstance) {
            const hasRoute = directionsInstance.getOrigin() && 
                             directionsInstance.getDestination();
            if (hasRoute) {
                toggleBtn.style.display = 'flex';
            } else {
                toggleBtn.style.display = 'none';
            }
        } else if (toggleBtn) {
            toggleBtn.style.display = 'none';
        }
    }
    
    // Setup panel UI handlers (collapse, drag, resize)
    function setupPanelUI() {
        if (!initPanelElements()) {
            setTimeout(setupPanelUI, 100);
            return;
        }
        
        // Initialize: Hide toggle button and panel by default
        if (toggleBtn) {
            toggleBtn.style.display = 'none';
        }
        
        // Ensure panel starts hidden
        if (panel) {
            panel.style.display = 'none';
            panel.classList.add('hidden');
        }
        
        // COLLAPSE toggle - Use class-based approach for better reliability
        if (collapseBtn) {
            collapseBtn.addEventListener("click", (e) => {
                e.stopPropagation();
                const icon = collapseBtn.querySelector("i");
                if (!icon || !content) return;
                
                const isCollapsed = content.classList.contains("collapsed");
                
                if (isCollapsed) {
                    // Expand: remove collapsed class and restore flex
                    content.classList.remove("collapsed");
                    content.style.flex = "";
                    content.style.maxHeight = "";
                    content.style.overflow = "";
                    if (!content.classList.contains("flex-1")) {
                        content.classList.add("flex-1");
                    }
                    icon.classList.remove("fa-chevron-up");
                    icon.classList.add("fa-chevron-down");
                } else {
                    // Collapse: add collapsed class and set flex to 0
                    content.classList.add("collapsed");
                    content.style.flex = "0 0 0%";
                    content.style.maxHeight = "0px";
                    content.style.overflow = "hidden";
                    icon.classList.remove("fa-chevron-down");
                    icon.classList.add("fa-chevron-up");
                }
            });
        }
        
        // TOGGLE button click handler - only show if route exists
        if (toggleBtn) {
            toggleBtn.addEventListener("click", () => {
                showDirectionsPanel();
            });
        }
        
        // DRAGGABLE header (disabled on mobile)
        let offsetX, offsetY, dragging = false;
        
        const isMobile = () => window.innerWidth <= 767;
        
        const resetPanelPosition = () => {
            if (isMobile() && panel) {
                panel.style.left = '50%';
                panel.style.transform = 'translateX(-50%)';
                panel.style.right = 'auto';
                panel.style.bottom = '1rem';
                panel.style.top = 'auto';
            }
        };
        
        if (header) {
            header.addEventListener("mousedown", (e) => {
                if (isMobile()) {
                    e.preventDefault();
                    return;
                }
                dragging = true;
                offsetX = e.clientX - panel.offsetLeft;
                offsetY = e.clientY - panel.offsetTop;
                header.classList.remove("grab");
                header.classList.add("grabbing");
            });
        }
        
        document.addEventListener("mousemove", (e) => {
            if (!dragging || isMobile() || !panel) return;
            panel.style.left = `${e.clientX - offsetX}px`;
            panel.style.top = `${e.clientY - offsetY}px`;
            panel.style.bottom = "auto";
        });
        
        document.addEventListener("mouseup", () => {
            if (dragging && !isMobile() && panel) {
                dragging = false;
                if (header) {
                    header.classList.add("grab");
                    header.classList.remove("grabbing");
                }
                localStorage.setItem(
                    "panelPosition",
                    JSON.stringify({
                        left: panel.style.left,
                        top: panel.style.top,
                    })
                );
            }
        });
        
        // Restore saved position (only on desktop)
        if (document.readyState === 'loading') {
            document.addEventListener("DOMContentLoaded", () => {
                if (isMobile()) {
                    resetPanelPosition();
                } else if (panel) {
                    const saved = localStorage.getItem("panelPosition");
                    if (saved) {
                        try {
                            const { left, top } = JSON.parse(saved);
                            panel.style.left = left;
                            panel.style.top = top;
                            panel.style.bottom = "auto";
                        } catch (e) {
                            console.warn("Failed to restore panel position:", e);
                        }
                    }
                }
            });
        } else {
            if (isMobile()) {
                resetPanelPosition();
            } else if (panel) {
                const saved = localStorage.getItem("panelPosition");
                if (saved) {
                    try {
                        const { left, top } = JSON.parse(saved);
                        panel.style.left = left;
                        panel.style.top = top;
                        panel.style.bottom = "auto";
                    } catch (e) {
                        console.warn("Failed to restore panel position:", e);
                    }
                }
            }
        }
        
        // Reset position on window resize to mobile
        window.addEventListener("resize", () => {
            if (isMobile()) {
                resetPanelPosition();
            }
        });
        
        // RESIZABLE bottom
        if (resizeHandle && panel) {
            resizeHandle.addEventListener("mousedown", function (e) {
                e.preventDefault();
                const startY = e.clientY;
                const startHeight = panel.offsetHeight;
                
                const resize = (e) => {
                    const newHeight = startHeight + (e.clientY - startY);
                    panel.style.height = newHeight + "px";
                };
                
                const stop = () => {
                    window.removeEventListener("mousemove", resize);
                    window.removeEventListener("mouseup", stop);
                };
                
                window.addEventListener("mousemove", resize);
                window.addEventListener("mouseup", stop);
            });
        }
    }
    
    // Setup directions functionality (route calculation, navigation)
    function setupDirectionsFunctionality(map, directions, state) {
        mapInstance = map;
        directionsInstance = directions;
        stateInstance = state;
        
        // Make directions accessible globally
        window.directionsInstance = directions;
        
        // Listen for the 'route' event from MapboxDirections
        directions.on('route', (e) => {
            if (!e.route || e.route.length === 0) {
                console.warn('No route found.');
                return;
            }

            // Mark that directions have been calculated
            directionsCalculated = true;
            if (state) {
                state.directionsCalculated = true;
            }
            window.directionsCalculated = true;

            const route = e.route[0];
            if (panel) {
                panel.classList.remove('hidden');
                panel.style.display = 'block';
            }
            if (toggleBtn) {
                toggleBtn.style.display = 'none';
            }
            
            // Update the directions panel content
            const directionsContent = document.getElementById('directions');
            if (directionsContent) {
                const distance = (route.distance / 1000).toFixed(1);
                const duration = Math.floor(route.duration / 60);
                
                directionsContent.innerHTML = `
                    <div class="mb-3 p-3 bg-gray-50 rounded-lg">
                        <div class="flex justify-between">
                            <span class="font-medium">Distance:</span>
                            <span>${distance} km</span>
                        </div>
                        <div class="flex justify-between">
                            <span class="font-medium">Duration:</span>
                            <span>${duration} min</span>
                        </div>
                    </div>
                    <div class="space-y-2 max-h-64 overflow-y-auto">
                        ${route.legs[0].steps.map((step, i) => `
                            <div class="flex items-start p-2 hover:bg-gray-50 rounded">
                                <div class="flex-shrink-0 mt-1 mr-3 w-6 h-6 rounded-full bg-primary-100 text-primary-600 flex items-center justify-center text-xs font-bold">
                                    ${i+1}
                                </div>
                                <div class="flex-1">
                                    <div class="text-sm">${step.maneuver.instruction}</div>
                                    ${step.distance > 0 ? `<div class="text-xs text-gray-500 mt-1">${(step.distance / 1000).toFixed(1)} km</div>` : ''}
                                </div>
                            </div>
                        `).join('')}
                    </div>
                `;
            }
        });

        // Error handling for directions
        directions.on('error', (e) => {
            console.error('Directions error:', e.error);
            if (window.Swal) {
                window.Swal.fire({
                    title: 'Routing Error',
                    text: 'Could not calculate route. Please try again later.',
                    icon: 'error',
                    confirmButtonText: 'OK'
                });
            }
        });

        // Show route function
        const showRoute = async (start, end) => {
            if (!window.Swal) {
                console.error('SweetAlert2 not available');
                return;
            }
            
            const loadingSwal = window.Swal.fire({
                title: 'Calculating Route',
                html: 'Please wait while we calculate the best route...',
                allowOutsideClick: false,
                didOpen: () => {
                    window.Swal.showLoading();
                }
            });

            try {
                // Clear any existing routes first
                directions.removeRoutes();
                
                // Set origin and destination
                directions.setOrigin(start);
                directions.setDestination(end);
                
                // Wait for the route to be calculated
                await new Promise((resolve, reject) => {
                    const checkRoute = () => {
                        if (directions.getOrigin() && directions.getDestination()) {
                            resolve();
                        } else {
                            setTimeout(checkRoute, 100);
                        }
                    };
                    
                    const timeout = setTimeout(() => {
                        reject(new Error('Route calculation timed out'));
                    }, 10000);
                    
                    const routeHandler = () => {
                        clearTimeout(timeout);
                        resolve();
                    };
                    
                    directions.on('route', routeHandler);
                    checkRoute();
                });
                
                // Show directions panel
                if (panel) {
                    panel.classList.remove('hidden');
                    panel.style.display = 'block';
                }
                if (toggleBtn) {
                    toggleBtn.style.display = 'none';
                }
                
                const directionsCtrl = document.querySelector('.mapboxgl-ctrl-directions');
                if (directionsCtrl) {
                    directionsCtrl.style.display = 'block';
                }
                
                // Center the map on the route
                if (mapInstance) {
                    const bounds = new mapboxgl.LngLatBounds()
                        .extend(start)
                        .extend(end);
                        
                    mapInstance.fitBounds(bounds, {
                        padding: {top: 100, bottom: 100, left: 100, right: 100},
                        maxZoom: 15,
                        speed: 1.2
                    });
                }
                
                await loadingSwal.close();
            } catch (error) {
                await loadingSwal.close();
                console.error('Error showing route:', error);
                window.Swal.fire({
                    title: 'Routing Error',
                    text: error.message || 'Failed to calculate route. Please try again.',
                    icon: 'error',
                    confirmButtonText: 'OK'
                });
            }
        };

        // Close button handler
        if (closeBtn && !closeBtn.hasAttribute('data-handler-attached')) {
            closeBtn.setAttribute('data-handler-attached', 'true');
            closeBtn.addEventListener('click', () => {
                if (panel) {
                    panel.classList.add('hidden');
                    panel.style.display = 'none';
                }
                
                // Only show toggle button if directions were calculated (route exists)
                const hasRoute = directions.getOrigin() && directions.getDestination();
                if (toggleBtn && hasRoute && directionsCalculated) {
                    toggleBtn.style.display = 'flex';
                } else if (toggleBtn) {
                    toggleBtn.style.display = 'none';
                }
                
                const directionsCtrl = document.querySelector('.mapboxgl-ctrl-directions');
                if (directionsCtrl) {
                    directionsCtrl.style.display = 'none';
                }
            });
        }
        
        // Toggle button handler - only active if directions were calculated
        if (toggleBtn && !toggleBtn.hasAttribute('data-handler-attached')) {
            toggleBtn.setAttribute('data-handler-attached', 'true');
            toggleBtn.addEventListener('click', () => {
                if (directionsInstance) {
                    const hasRoute = directionsInstance.getOrigin() && 
                                     directionsInstance.getDestination();
                    if (hasRoute && directionsCalculated) {
                        if (panel) {
                            panel.classList.remove('hidden');
                            panel.style.display = 'block';
                        }
                        if (toggleBtn) {
                            toggleBtn.style.display = 'none';
                        }
                        const directionsCtrl = document.querySelector('.mapboxgl-ctrl-directions');
                        if (directionsCtrl) {
                            directionsCtrl.style.display = 'block';
                        }
                    }
                }
            });
        }

        // Navigation tracking functions
        const startNavigation = () => {
            if (!directions.getOrigin() || !directions.getDestination()) {
                if (window.Swal) {
                    window.Swal.fire({
                        title: 'Route Required',
                        text: 'Please calculate a route first',
                        icon: 'info',
                        confirmButtonText: 'OK'
                    });
                }
                return;
            }

            if (!navigator.geolocation) {
                if (window.Swal) {
                    window.Swal.fire({
                        title: 'Location Not Supported',
                        text: 'Your browser does not support geolocation',
                        icon: 'error',
                        confirmButtonText: 'OK'
                    });
                }
                return;
            }

            if (stateInstance) {
                stateInstance.isNavigating = true;
                stateInstance.destination = directions.getDestination().geometry.coordinates;
            }
            
            // Show navigation overlay
            const navigationOverlay = document.getElementById('navigationOverlay');
            if (navigationOverlay) {
                navigationOverlay.classList.remove('hidden');
            }

            // Update button text
            const navButton = document.getElementById('startNavigation');
            const navButtonText = document.getElementById('navigationButtonText');
            const navButtonIcon = navButton ? navButton.querySelector('i') : null;
            if (navButton) {
                navButton.classList.remove('bg-primary-600', 'hover:bg-primary-700');
                navButton.classList.add('bg-red-600', 'hover:bg-red-700');
            }
            if (navButtonIcon) {
                navButtonIcon.className = 'fas fa-stop-circle mr-2';
            }
            if (navButtonText) {
                navButtonText.textContent = 'Stop Navigation';
            }

            // Create/update navigation marker
            if (stateInstance && stateInstance.navigationMarker) {
                stateInstance.navigationMarker.remove();
            }
            
            if (stateInstance && stateInstance.userLocation && mapInstance) {
                const navMarkerEl = document.createElement('div');
                navMarkerEl.className = 'navigation-marker';
                navMarkerEl.innerHTML = `
                    <div class="relative">
                        <i class="fas fa-location-arrow text-blue-600 text-4xl transform rotate-45"></i>
                        <div class="absolute inset-0 rounded-full bg-blue-500 opacity-30 animate-ping"></div>
                    </div>
                `;
                stateInstance.navigationMarker = new mapboxgl.Marker({
                    element: navMarkerEl,
                    anchor: 'center'
                }).setLngLat(stateInstance.userLocation).addTo(mapInstance);
            }

            // Start watching position
            const watchOptions = {
                enableHighAccuracy: true,
                timeout: 10000,
                maximumAge: 0
            };

            navigationWatchId = navigator.geolocation.watchPosition(
                (position) => {
                    const currentCoords = [position.coords.longitude, position.coords.latitude];
                    updateNavigationLocation(currentCoords, position.coords.accuracy);
                },
                (error) => {
                    console.error('Navigation location error:', error);
                    if (window.Swal) {
                        window.Swal.fire({
                            title: 'Location Error',
                            text: 'Could not track your location. Please check your location settings.',
                            icon: 'warning',
                            confirmButtonText: 'OK'
                        });
                    }
                },
                watchOptions
            );

            if (stateInstance) {
                stateInstance.navigationWatchId = navigationWatchId;
            }

            // Initial location update
            if (stateInstance && stateInstance.userLocation) {
                updateNavigationLocation(stateInstance.userLocation, null);
            }

            // Center map on user location with navigation view
            if (stateInstance && stateInstance.userLocation && mapInstance) {
                mapInstance.flyTo({
                    center: stateInstance.userLocation,
                    zoom: 16,
                    bearing: 0,
                    pitch: 60,
                    essential: true
                });
            }
        };

        const stopNavigation = () => {
            if (stateInstance) {
                stateInstance.isNavigating = false;
            }
            
            // Stop watching position
            if (navigationWatchId !== null) {
                navigator.geolocation.clearWatch(navigationWatchId);
                navigationWatchId = null;
            }
            
            if (stateInstance) {
                stateInstance.navigationWatchId = null;
            }

            // Hide navigation overlay
            const navigationOverlay = document.getElementById('navigationOverlay');
            if (navigationOverlay) {
                navigationOverlay.classList.add('hidden');
            }

            // Remove navigation marker
            if (stateInstance && stateInstance.navigationMarker) {
                stateInstance.navigationMarker.remove();
                stateInstance.navigationMarker = null;
            }

            // Reset button
            const navButton = document.getElementById('startNavigation');
            const navButtonText = document.getElementById('navigationButtonText');
            const navButtonIcon = navButton ? navButton.querySelector('i') : null;
            if (navButton) {
                navButton.classList.remove('bg-red-600', 'hover:bg-red-700');
                navButton.classList.add('bg-primary-600', 'hover:bg-primary-700');
            }
            if (navButtonIcon) {
                navButtonIcon.className = 'fas fa-location-arrow mr-2';
            }
            if (navButtonText) {
                navButtonText.textContent = 'Start Navigation';
            }

            // Reset map view
            if (mapInstance) {
                mapInstance.flyTo({
                    pitch: 0,
                    bearing: 0,
                    essential: true
                });
            }
        };

        const updateNavigationLocation = async (coords, accuracy) => {
            // Update navigation marker position
            if (stateInstance && stateInstance.navigationMarker) {
                stateInstance.navigationMarker.setLngLat(coords);
            }

            // Update current location info
            const locationInfo = document.getElementById('currentLocationInfo');
            if (locationInfo) {
                const accuracyText = accuracy ? `±${Math.round(accuracy)}m` : '';
                locationInfo.textContent = `${coords[1].toFixed(6)}, ${coords[0].toFixed(6)} ${accuracyText}`;
            }

            // Update route from current location to destination
            const now = Date.now();
            if (stateInstance) {
                if (!stateInstance.lastRouteUpdate || (now - stateInstance.lastRouteUpdate) > 5000) {
                    stateInstance.lastRouteUpdate = now;
                    await updateRouteFromCurrentLocation(coords);
                }
            }

            // Keep map centered on user location during navigation
            if (mapInstance) {
                mapInstance.flyTo({
                    center: coords,
                    zoom: 16,
                    essential: true,
                    duration: 1000
                });
            }
        };

        const updateRouteFromCurrentLocation = async (currentCoords) => {
            if (!stateInstance || !stateInstance.destination) return;

            try {
                // Update directions origin to current location
                directions.setOrigin(currentCoords);
                
                // Wait for route to update
                let routeData = null;
                let routeHandler = null;
                await new Promise((resolve) => {
                    const timeout = setTimeout(() => {
                        if (routeHandler) {
                            try {
                                if (typeof directions.off === 'function') {
                                    directions.off('route', routeHandler);
                                }
                            } catch (e) {
                                // Ignore if off is not supported
                            }
                        }
                        resolve();
                    }, 3000);
                    routeHandler = (e) => {
                        if (e.route && e.route.length > 0) {
                            routeData = e.route[0];
                            clearTimeout(timeout);
                            try {
                                if (typeof directions.off === 'function') {
                                    directions.off('route', routeHandler);
                                }
                            } catch (e) {
                                // Ignore if off is not supported
                            }
                            resolve();
                        }
                    };
                    directions.on('route', routeHandler);
                });

                if (routeData) {
                    // Update time and distance display
                    const duration = Math.floor(routeData.duration / 60);
                    const distance = (routeData.distance / 1000).toFixed(1);
                    
                    const timeEl = document.getElementById('timeToDestination');
                    const distanceEl = document.getElementById('distanceRemaining');
                    
                    if (timeEl) {
                        const hours = Math.floor(duration / 60);
                        const minutes = duration % 60;
                        if (hours > 0) {
                            timeEl.textContent = `${hours}h ${minutes}m`;
                        } else {
                            timeEl.textContent = `${minutes}m`;
                        }
                    }
                    
                    if (distanceEl) {
                        distanceEl.textContent = `${distance} km`;
                    }
                }
            } catch (error) {
                console.error('Error updating route:', error);
            }
        };

        // Start navigation button handler - prevent duplicate listeners
        const startNavButton = document.getElementById('startNavigation');
        if (startNavButton && !startNavButton.hasAttribute('data-listener-attached')) {
            startNavButton.setAttribute('data-listener-attached', 'true');
            startNavButton.addEventListener('click', () => {
                if (stateInstance && stateInstance.isNavigating) {
                    stopNavigation();
                } else {
                    startNavigation();
                }
            });
        }

        // Stop navigation button handler
        const stopNavButton = document.getElementById('stopNavigation');
        if (stopNavButton && !stopNavButton.hasAttribute('data-listener-attached')) {
            stopNavButton.setAttribute('data-listener-attached', 'true');
            stopNavButton.addEventListener('click', () => {
                stopNavigation();
            });
        }

        // Return public API
        return { showRoute };
    }
    
    // Public API
    window.DirectionsPanel = {
        // Initialize directions functionality (called from map.html)
        setupDirections: function(map, directions, state) {
            return setupDirectionsFunctionality(map, directions, state);
        },
        
        // Show/hide panel functions
        showPanel: showDirectionsPanel,
        hidePanel: hideDirectionsPanel
    };
    
    // Make functions globally accessible for backward compatibility
    window.showDirectionsPanel = showDirectionsPanel;
    window.hideDirectionsPanel = hideDirectionsPanel;
    
    // Initialize panel UI when DOM is ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', setupPanelUI);
    } else {
        setupPanelUI();
    }
    
    // Immediately hide panel if it exists (before DOM ready)
    (function hidePanelImmediately() {
        const panelEl = document.getElementById("directionsPanel");
        if (panelEl) {
            panelEl.style.display = 'none';
            panelEl.classList.add('hidden');
        }
    })();
})();
