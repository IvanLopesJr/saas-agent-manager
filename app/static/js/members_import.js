/**
 * Members Import functionality
 */

const membersImportTranslate = (window.app && typeof window.app.translate === 'function')
    ? window.app.translate
    : (key, fallback) => fallback;

document.addEventListener('DOMContentLoaded', function() {
    const csvFileInput = document.querySelector('input[name="csv_file"]');
    
    if (csvFileInput) {
        csvFileInput.addEventListener('change', function(e) {
            const file = e.target.files[0];
            if (file) {
                const fileName = file.name;
                const fileSize = (file.size / 1024).toFixed(2);
                
                // Check file type
                if (!fileName.endsWith('.csv')) {
                    alert(membersImportTranslate('selectCsvPrompt', 'Por favor, selecione um arquivo CSV (.csv)'));
                    e.target.value = '';
                    return;
                }
                
                // Check file size (max 5MB)
                if (file.size > 5 * 1024 * 1024) {
                    alert(membersImportTranslate('csvFileTooLarge', 'O arquivo não pode ser maior que 5MB'));
                    e.target.value = '';
                    return;
                }
                
                // Show file info
                console.log(`Arquivo selecionado: ${fileName} (${fileSize} KB)`);
            }
        });
    }
    
});

// Download template CSV
function downloadTemplateCSV() {
    const csvContent = `nome;email;telefone;documento_identificacao;departamento;regional;tipo_cargo;cargo;sexo;data_nascimento;data_admissao;cidade;estado;pais;dealership;dealership_number;status;chatbots
"João Silva";"joao@email.com";"5511987654321";"BR123456";"Vendas";"Sudeste";"Gerencial";"Gerente Regional";"masculino";"15/01/1990";"10/02/2022";"São Paulo";"SP";"Brasil";"Concessionária ABC";"12345";"active";"Vendas,Suporte"
"Maria Santos";"maria@email.com";"5521999998888";"BR654321";"RH";"Sul";"Operacional";"Analista Sênior";"feminino";"20/06/1992";"05/03/2021";"Rio de Janeiro";"RJ";"Brasil";"Concessionária XYZ";"67890";"pending";"RH"`;
    
    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
    const link = document.createElement('a');
    const url = URL.createObjectURL(blob);
    
    link.setAttribute('href', url);
    link.setAttribute('download', 'template_membros.csv');
    link.style.visibility = 'hidden';
    
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
}

// Make function available globally
window.downloadTemplateCSV = downloadTemplateCSV;




