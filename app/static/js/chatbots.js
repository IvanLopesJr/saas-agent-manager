/**
 * Chatbots functionality
 */

document.addEventListener('DOMContentLoaded', function() {
    // Initialize chatbot selection
    initChatbotSelection();
    
    // Calculate total cost for per_chatbot mode
    const chatbotCheckboxes = document.querySelectorAll('input[name="chatbots"]');
    if (chatbotCheckboxes.length > 0) {
        chatbotCheckboxes.forEach(checkbox => {
            checkbox.addEventListener('change', updateChatbotCost);
        });
        
        // Initial calculation
        updateChatbotCost();
    }
});

function initChatbotSelection() {
    // Add "Select All" functionality
    const selectAllBtn = document.querySelector('[onclick*="selectAllChatbots"]');
    if (selectAllBtn) {
        selectAllBtn.addEventListener('click', function(e) {
            e.preventDefault();
            toggleAllChatbots();
        });
    }
}

function toggleAllChatbots() {
    const checkboxes = document.querySelectorAll('input[name="chatbots"]');
    const allChecked = Array.from(checkboxes).every(cb => cb.checked);
    
    checkboxes.forEach(cb => {
        cb.checked = !allChecked;
    });
    
    updateChatbotCost();
}

function updateChatbotCost() {
    const totalCostElement = document.getElementById('totalCost');
    if (!totalCostElement) return;
    
    const checkedBoxes = document.querySelectorAll('input[name="chatbots"]:checked');
    let total = 0;
    
    checkedBoxes.forEach(checkbox => {
        // Get price from data attribute or label
        const label = document.querySelector(`label[for="${checkbox.id}"]`);
        if (label) {
            const priceMatch = label.textContent.match(/[\d,]+\.?\d*/);
            if (priceMatch) {
                const price = parseFloat(priceMatch[0].replace(',', '.'));
                total += price;
            }
        }
    });
    
    // Get currency symbol
    const currencyMatch = totalCostElement.textContent.match(/[R$€£¥]/);
    const currencySymbol = currencyMatch ? currencyMatch[0] : 'R$';
    
    // Update display
    totalCostElement.textContent = `${currencySymbol} ${total.toFixed(2).replace('.', ',')}`;
}

// Export functions to global scope
window.app = window.app || {};
window.selectAllChatbots = toggleAllChatbots;
