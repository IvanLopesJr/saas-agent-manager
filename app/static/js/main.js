/**
 * Main JavaScript for Sistema Multi-Empresas
 */

// Translation helper
function translateMessage(key, fallback) {
    if (window.APP_I18N && window.APP_I18N[key]) {
        return window.APP_I18N[key];
    }
    return fallback;
}

// CSRF Token handling for Django
function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}

const csrftoken = getCookie('csrftoken');

// Configure AJAX to include CSRF token
document.addEventListener('DOMContentLoaded', function() {
    // Add CSRF token to all AJAX requests
    const originalFetch = window.fetch;
    window.fetch = function(url, options = {}) {
        if (!options.headers) {
            options.headers = {};
        }
        if (typeof options.headers.append === 'function') {
            options.headers.append('X-CSRFToken', csrftoken);
        } else {
            options.headers['X-CSRFToken'] = csrftoken;
        }
        return originalFetch(url, options);
    };
    
    // Initialize tooltips if Bootstrap is loaded
    if (typeof bootstrap !== 'undefined') {
        const tooltipTriggerList = document.querySelectorAll('[data-bs-toggle="tooltip"]');
        const tooltipList = [...tooltipTriggerList].map(tooltipTriggerEl => new bootstrap.Tooltip(tooltipTriggerEl));
    }
    
    // Auto-hide alerts after 5 seconds
    const alerts = document.querySelectorAll('.alert:not(.alert-permanent)');
    alerts.forEach(alert => {
        setTimeout(() => {
            const bsAlert = new bootstrap.Alert(alert);
            bsAlert.close();
        }, 5000);
    });
});

// Show loading spinner
function showLoading() {
    const loader = document.createElement('div');
    loader.id = 'global-loader';
    loader.className = 'global-loader';
    loader.innerHTML = `<div class="spinner-border text-primary" role="status"><span class="visually-hidden">${translateMessage('loadingLabel', 'Loading...')}</span></div>`;
    document.body.appendChild(loader);
}

// Hide loading spinner
function hideLoading() {
    const loader = document.getElementById('global-loader');
    if (loader) {
        loader.remove();
    }
}

// Confirm delete action
function confirmDelete(message) {
    return confirm(message || translateMessage('confirmDelete', 'Tem certeza que deseja deletar este item? Esta ação não pode ser desfeita.'));
}

// Format currency
function formatCurrency(value, currency = 'BRL', symbol = 'R$') {
    const formatted = parseFloat(value).toFixed(2);
    
    if (currency === 'BRL') {
        return symbol + ' ' + formatted.replace('.', ',').replace(/\B(?=(\d{3})+(?!\d))/g, '.');
    } else {
        return symbol + ' ' + formatted.replace(/\B(?=(\d{3})+(?!\d))/g, ',');
    }
}

// Format date
function formatDate(dateString) {
    const date = new Date(dateString);
    const day = String(date.getDate()).padStart(2, '0');
    const month = String(date.getMonth() + 1).padStart(2, '0');
    const year = date.getFullYear();
    return `${day}/${month}/${year}`;
}

// Debounce function for search inputs
function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

// Show toast notification
function showToast(message, type = 'info') {
    const toastContainer = document.querySelector('.toast-container') || createToastContainer();
    
    const toast = document.createElement('div');
    toast.className = `toast align-items-center text-white bg-${type} border-0`;
    toast.setAttribute('role', 'alert');
    toast.setAttribute('aria-live', 'assertive');
    toast.setAttribute('aria-atomic', 'true');
    
    toast.innerHTML = `
        <div class="d-flex">
            <div class="toast-body">${message}</div>
            <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast"></button>
        </div>
    `;
    
    toastContainer.appendChild(toast);
    
    const bsToast = new bootstrap.Toast(toast);
    bsToast.show();
    
    toast.addEventListener('hidden.bs.toast', () => {
        toast.remove();
    });
}

function createToastContainer() {
    const container = document.createElement('div');
    container.className = 'toast-container position-fixed top-0 end-0 p-3';
    container.style.zIndex = '1060';
    document.body.appendChild(container);
    return container;
}

// Copy to clipboard
function copyToClipboard(text) {
    if (navigator.clipboard) {
        navigator.clipboard.writeText(text).then(() => {
            showToast(translateMessage('copySuccess', 'Copiado para a área de transferência!'), 'success');
        }).catch(err => {
            console.error(translateMessage('copyFailure', 'Failed to copy:'), err);
        });
    } else {
        // Fallback for older browsers
        const textarea = document.createElement('textarea');
        textarea.value = text;
        textarea.style.position = 'fixed';
        textarea.style.opacity = '0';
        document.body.appendChild(textarea);
        textarea.select();
        document.execCommand('copy');
        document.body.removeChild(textarea);
        showToast(translateMessage('copySuccess', 'Copiado para a área de transferência!'), 'success');
    }
}

// Handle form validation
function validateForm(formId) {
    const form = document.getElementById(formId);
    if (!form) return false;
    
    form.classList.add('was-validated');
    return form.checkValidity();
}

// Export functions to global scope
window.app = {
    getCookie,
    showLoading,
    hideLoading,
    confirmDelete,
    formatCurrency,
    formatDate,
    debounce,
    showToast,
    copyToClipboard,
    validateForm,
    translate: translateMessage
};
