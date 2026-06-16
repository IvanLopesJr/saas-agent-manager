/**
 * Billing calculations and utilities
 */

const billingTranslate = (window.app && typeof window.app.translate === 'function')
    ? window.app.translate
    : (key, fallback) => fallback;

document.addEventListener('DOMContentLoaded', function() {
    // Initialize billing calculations
    initBillingCalculations();
    
    // Period validation
    const periodStartInput = document.querySelector('input[name="period_start"]');
    const periodEndInput = document.querySelector('input[name="period_end"]');
    
    if (periodStartInput && periodEndInput) {
        periodEndInput.addEventListener('change', function() {
            const startDate = new Date(periodStartInput.value);
            const endDate = new Date(periodEndInput.value);
            
            if (startDate >= endDate) {
                alert(billingTranslate('billingEndDateAfterStart', 'A data de fim deve ser posterior à data de início'));
                periodEndInput.value = '';
            }
        });
    }
});

function initBillingCalculations() {
    // Calculate totals on billing detail pages
    const billingTables = document.querySelectorAll('.table');
    
    billingTables.forEach(table => {
        if (table.querySelector('tfoot')) {
            calculateTableTotal(table);
        }
    });
}

function calculateTableTotal(table) {
    const valueColumn = table.querySelectorAll('tbody td:last-child');
    let total = 0;
    
    valueColumn.forEach(cell => {
        const value = cell.textContent.replace(/[^\d,]/g, '').replace(',', '.');
        total += parseFloat(value) || 0;
    });
    
    const totalCell = table.querySelector('tfoot td:last-child strong');
    if (totalCell) {
        const currencySymbol = totalCell.textContent.match(/[R$€£¥]/)?.[0] || 'R$';
        totalCell.textContent = `${currencySymbol} ${total.toFixed(2).replace('.', ',')}`;
    }
}

// Export billing data
function exportBillingData(billingId, format = 'csv') {
    window.location.href = `/billing/${billingId}/export/${format}/`;
}

// Filter billings by date range
function filterBillings() {
    const form = document.querySelector('form[method="get"]');
    if (form) {
        form.submit();
    }
}

// Calculate estimated cost
function calculateEstimatedCost(memberCount, pricePerMember, billingMode, chatbotCount = 0) {
    if (billingMode === 'per_user') {
        return memberCount * pricePerMember;
    } else {
        return memberCount * chatbotCount * pricePerMember;
    }
}

// Format billing period
function formatBillingPeriod(startDate, endDate) {
    const options = { year: 'numeric', month: 'long' };
    const start = new Date(startDate);
    const end = new Date(endDate);
    
    if (start.getMonth() === end.getMonth() && start.getFullYear() === end.getFullYear()) {
        return start.toLocaleDateString('pt-BR', options);
    } else {
        return `${start.toLocaleDateString('pt-BR', options)} - ${end.toLocaleDateString('pt-BR', options)}`;
    }
}

// Export functions to global scope
window.app = window.app || {};
window.app.exportBillingData = exportBillingData;
window.app.filterBillings = filterBillings;
window.app.calculateEstimatedCost = calculateEstimatedCost;
window.app.formatBillingPeriod = formatBillingPeriod;
