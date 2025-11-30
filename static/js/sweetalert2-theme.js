/**
 * SweetAlert2 Theme Configuration
 * Unified theme configuration for MyNextHome application
 * Matches the application's primary green color scheme
 */

(function() {
    'use strict';

    // Wait for SweetAlert2 to be loaded
    if (typeof Swal === 'undefined') {
        console.warn('SweetAlert2 is not loaded. Theme configuration skipped.');
        return;
    }

    // Theme configuration matching MyNextHome's primary green colors
    const SwalTheme = {
        color: '#166534', // primary-800 (dark green text)
        background: '#ffffff',
        confirmButtonColor: '#16a34a', // primary-600 (green)
        cancelButtonColor: '#6b7280', // gray-500
        denyButtonColor: '#ef4444', // red-500
        inputBackgroundColor: '#ffffff',
        inputBorderColor: '#d1d5db', // gray-300
        inputColor: '#111827', // gray-900
        validationMessageColor: '#ef4444', // red-500
        progressBarColor: '#16a34a', // primary-600
        backdrop: 'rgba(0, 0, 0, 0.4)',
        popup: {
            background: '#ffffff',
            borderRadius: '0.5rem',
            boxShadow: '0 10px 15px -3px rgba(0, 0, 0, 0.1), 0 4px 6px -2px rgba(0, 0, 0, 0.05)',
        },
        buttonsStyling: true,
        customClass: {
            container: 'swal2-container-custom',
            popup: 'swal2-popup-custom',
            title: 'swal2-title-custom',
            htmlContainer: 'swal2-html-container-custom',
            confirmButton: 'swal2-confirm-custom',
            cancelButton: 'swal2-cancel-custom',
            denyButton: 'swal2-deny-custom',
            input: 'swal2-input-custom',
        }
    };

    // Set default configuration for all SweetAlert2 instances
    Swal.mixin({
        color: SwalTheme.color,
        background: SwalTheme.background,
        confirmButtonColor: SwalTheme.confirmButtonColor,
        cancelButtonColor: SwalTheme.cancelButtonColor,
        denyButtonColor: SwalTheme.denyButtonColor,
        buttonsStyling: true,
        customClass: {
            confirmButton: 'swal2-confirm-custom',
            cancelButton: 'swal2-cancel-custom',
            denyButton: 'swal2-deny-custom',
        }
    });

    // Make theme configuration globally accessible
    window.SwalTheme = SwalTheme;
})();

