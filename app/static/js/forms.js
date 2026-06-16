/**
 * Form utilities and validations
 */

const formsTranslate = (window.app && typeof window.app.translate === 'function')
    ? window.app.translate
    : (key, fallback) => fallback;

document.addEventListener('DOMContentLoaded', function() {
    // CPF mask
    const cpfInputs = document.querySelectorAll('input[name="cpf"]');
    cpfInputs.forEach(input => {
        input.addEventListener('input', function(e) {
            let value = e.target.value.replace(/\D/g, '');
            if (value.length <= 11) {
                value = value.replace(/(\d{3})(\d)/, '$1.$2');
                value = value.replace(/(\d{3})(\d)/, '$1.$2');
                value = value.replace(/(\d{3})(\d{1,2})$/, '$1-$2');
            }
            e.target.value = value;
        });
    });
    
    // Phone mask
    const phoneInputs = document.querySelectorAll('input[name="phone"], input[type="tel"]');
    phoneInputs.forEach(input => {
        input.addEventListener('input', function(e) {
            let value = e.target.value.replace(/\D/g, '');
            if (value.length <= 11) {
                if (value.length <= 10) {
                    value = value.replace(/(\d{2})(\d)/, '($1)$2');
                    value = value.replace(/(\d{4})(\d)/, '$1-$2');
                } else {
                    value = value.replace(/(\d{2})(\d)/, '($1)$2');
                    value = value.replace(/(\d{5})(\d)/, '$1-$2');
                }
            }
            e.target.value = value;
        });
    });
    
    // Currency mask
    const currencyInputs = document.querySelectorAll('input[name*="price"], input[name*="value"]');
    currencyInputs.forEach(input => {
        if (input.type === 'number') {
            input.addEventListener('blur', function(e) {
                if (e.target.value) {
                    e.target.value = parseFloat(e.target.value).toFixed(2);
                }
            });
        }
    });
    
    // Form validation on submit
    const forms = document.querySelectorAll('form[method="post"]');
    forms.forEach(form => {
        form.addEventListener('submit', function(e) {
            if (!form.checkValidity()) {
                e.preventDefault();
                e.stopPropagation();
            }
            form.classList.add('was-validated');
        });
    });
    
    // Prevent double submit
    forms.forEach(form => {
        form.addEventListener('submit', function() {
            const submitBtn = form.querySelector('button[type="submit"]');
            if (submitBtn) {
                submitBtn.disabled = true;
                const sendingText = formsTranslate('formSubmitting', 'Enviando...');
                submitBtn.innerHTML = `<span class="spinner-border spinner-border-sm me-2"></span>${sendingText}`;
                
                // Re-enable after 3 seconds in case of validation errors
                setTimeout(() => {
                    submitBtn.disabled = false;
                    submitBtn.innerHTML = submitBtn.getAttribute('data-original-text') || formsTranslate('formSubmitDefault', 'Salvar');
                }, 3000);
            }
        });
    });
    
    // Store original button text
    const submitButtons = document.querySelectorAll('button[type="submit"]');
    submitButtons.forEach(btn => {
        btn.setAttribute('data-original-text', btn.innerHTML);
    });
});


