// Directions Panel Management
// Handles collapse, drag, resize, and toggle functionality

(function() {
    'use strict';
    
    // Wait for DOM to be ready
    function initDirectionsPanel() {
        const panel = document.getElementById("directionsPanel");
        const header = document.getElementById("directionsPanelHeader");
        const content = document.getElementById("directionsPanelContent");
        const collapseBtn = document.getElementById("collapseDirections");
        const closeBtn = document.getElementById("closeDirections");
        const resizeHandle = document.getElementById("resizeHandle");
        const toggleBtn = document.getElementById("directionsPanelToggle");
        
        if (!panel || !header || !content || !collapseBtn || !closeBtn) {
            // Elements not found, retry after a short delay
            setTimeout(initDirectionsPanel, 100);
            return;
        }
        
        // Initialize: Hide toggle button and panel by default
        // It will only show after directions are calculated and panel is closed
        if (toggleBtn) {
            toggleBtn.style.display = 'none';
        }
        
        // Ensure panel starts hidden
        if (panel) {
            panel.style.display = 'none';
            panel.classList.add('hidden');
        }
        
        // COLLAPSE toggle - Use class-based approach for better reliability
        collapseBtn.addEventListener("click", (e) => {
            e.stopPropagation();
            const icon = collapseBtn.querySelector("i");
            const isCollapsed = content.classList.contains("collapsed");
            
            if (isCollapsed) {
                // Expand: remove collapsed class and restore flex
                content.classList.remove("collapsed");
                // Remove inline styles to let Tailwind classes work
                content.style.flex = "";
                content.style.maxHeight = "";
                content.style.overflow = "";
                // Ensure flex-1 class is present (it should be from HTML)
                if (!content.classList.contains("flex-1")) {
                    content.classList.add("flex-1");
                }
                icon.classList.remove("fa-chevron-up");
                icon.classList.add("fa-chevron-down");
            } else {
                // Collapse: add collapsed class and set flex to 0
                content.classList.add("collapsed");
                // Override Tailwind flex-1 with inline style
                content.style.flex = "0 0 0%";
                content.style.maxHeight = "0px";
                content.style.overflow = "hidden";
                icon.classList.remove("fa-chevron-down");
                icon.classList.add("fa-chevron-up");
            }
        });
        
        // Function to show panel - only if route exists
        function showDirectionsPanel() {
            // Check if a route exists and has been calculated before showing
            if (!window.directionsInstance) {
                return; // No directions instance
            }
            
            const origin = window.directionsInstance.getOrigin();
            const destination = window.directionsInstance.getDestination();
            const hasRoute = !!(origin && destination);
            
            // Check if route has been calculated
            const hasCalculatedRoute = !!(window.directionsCalculated || (window.state && window.state.directionsCalculated));
            
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
            panel.style.display = "none";
            panel.classList.add('hidden');
            // Only show toggle button if directions were calculated
            if (toggleBtn && window.directionsInstance) {
                const hasRoute = window.directionsInstance.getOrigin() && 
                                 window.directionsInstance.getDestination();
                if (hasRoute) {
                    toggleBtn.style.display = 'flex';
                } else {
                    toggleBtn.style.display = 'none';
                }
            } else if (toggleBtn) {
                toggleBtn.style.display = 'none';
            }
        }
        
        // CLOSE panel - handler is set up in map.html's setupDirections function
        // which has more complete logic for state management
        // This handler is kept as a fallback but map.html's handler takes precedence
        if (closeBtn && !closeBtn.hasAttribute('data-handler-attached')) {
            closeBtn.setAttribute('data-handler-attached', 'true');
            closeBtn.addEventListener("click", () => {
                hideDirectionsPanel();
            });
        }
        
        // TOGGLE button click handler - only show if route exists
        if (toggleBtn) {
            toggleBtn.addEventListener("click", () => {
                // showDirectionsPanel() already checks for route existence
                showDirectionsPanel();
            });
        }
        
        // DRAGGABLE header (disabled on mobile)
        let offsetX, offsetY, dragging = false;
        
        // Function to check if on mobile
        const isMobile = () => window.innerWidth <= 767;
        
        // Function to reset panel to centered position on mobile
        const resetPanelPosition = () => {
            if (isMobile() && panel) {
                panel.style.left = '50%';
                panel.style.transform = 'translateX(-50%)';
                panel.style.right = 'auto';
                panel.style.bottom = '1rem';
                panel.style.top = 'auto';
            }
        };
        
        header.addEventListener("mousedown", (e) => {
            // Disable dragging on mobile
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
        
        document.addEventListener("mousemove", (e) => {
            if (!dragging || isMobile()) return;
            panel.style.left = `${e.clientX - offsetX}px`;
            panel.style.top = `${e.clientY - offsetY}px`;
            panel.style.bottom = "auto";
        });
        
        document.addEventListener("mouseup", () => {
            if (dragging && !isMobile()) {
                dragging = false;
                header.classList.add("grab");
                header.classList.remove("grabbing");
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
                } else {
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
            // DOM already loaded
            if (isMobile()) {
                resetPanelPosition();
            } else {
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
        if (resizeHandle) {
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
        
        // Make functions globally accessible for other scripts
        window.showDirectionsPanel = showDirectionsPanel;
        window.hideDirectionsPanel = hideDirectionsPanel;
    }
    
    // Immediately hide panel if it exists (before DOM ready)
    (function hidePanelImmediately() {
        const panel = document.getElementById("directionsPanel");
        if (panel) {
            panel.style.display = 'none';
            panel.classList.add('hidden');
        }
    })();
    
    // Initialize when DOM is ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initDirectionsPanel);
    } else {
        // DOM already loaded
        initDirectionsPanel();
    }
})();

