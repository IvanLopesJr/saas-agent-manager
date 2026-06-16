"""
CSV import/export utilities
"""

import csv
import io
import re
from datetime import datetime
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.db.models import Prefetch
from django.utils.translation import gettext_lazy as _
from ..models import CompanyMember
from .validators import clean_identification_document


def _detect_delimiter(file_data: str) -> str:
    """Return ';' by default, fallback to ',' when semicolons are absent."""
    if not file_data:
        return ';'
    first_line = file_data.splitlines()[0]
    if ';' in first_line:
        return ';'
    if ',' in first_line:
        return ','
    return ';'


def _parse_date(value: str):
    """Parse dates in dd/mm/YYYY or ISO fallback."""
    if not value:
        return None
    value = value.strip()
    if not value:
        return None
    for fmt in ('%d/%m/%Y', '%Y-%m-%d'):
        try:
            return datetime.strptime(value, fmt).date()
        except ValueError:
            continue
    return None


ROLE_TYPE_MAP = {
    'gerencial': 'management',
    'management': 'management',
    'operacional': 'operational',
    'operational': 'operational',
    'tecnico': 'technical',
    'técnico': 'technical',
    'technical': 'technical',
    'suporte': 'support',
    'support': 'support',
    'outro': 'other',
    'other': 'other',
}
VALID_ROLE_TYPES = set(ROLE_TYPE_MAP.values())
SEX_MAP = {
    'masculino': 'male',
    'm': 'male',
    'male': 'male',
    'feminino': 'female',
    'f': 'female',
    'female': 'female',
    'outro': 'other',
    'other': 'other',
    'prefere nao informar': 'prefer_not',
    'prefere não informar': 'prefer_not',
    'prefer not': 'prefer_not',
}


def _read_csv_file(uploaded_file):
    raw_data = uploaded_file.read()
    try:
        return raw_data.decode('utf-8')
    except UnicodeDecodeError:
        try:
            return raw_data.decode('latin-1')
        except UnicodeDecodeError:
            return raw_data.decode('cp1252', errors='ignore')


def parse_csv_file(csv_file, company):
    """
    Parse CSV file for member import
    
    Args:
        csv_file: UploadedFile object
        company: Company instance
    
    Returns:
        List of dictionaries with member data (each entry may include an 'errors' dict)
    """
    file_data = _read_csv_file(csv_file)
    delimiter = _detect_delimiter(file_data)
    csv_reader = csv.DictReader(io.StringIO(file_data), delimiter=delimiter)
    
    members_data = []
    existing_documents = set(
        CompanyMember.objects.values_list('identification_document', flat=True)
    )
    seen_documents = set()
    
    for line_number, row in enumerate(csv_reader, start=2):
        role_value = row.get('tipo_cargo', '').strip()
        normalized_role = ROLE_TYPE_MAP.get(role_value.lower(), role_value.lower() if role_value else '')
        if normalized_role and normalized_role not in VALID_ROLE_TYPES:
            normalized_role = 'other'

        row_errors = {}

        def add_error(field, message):
            row_errors.setdefault(field, []).append(str(message))

        name = row.get('nome', '').strip()
        if not name:
            add_error('name', _('Nome é obrigatório.'))

        email = row.get('email', '').strip().lower()
        if not email:
            add_error('email', _('Email é obrigatório.'))
        else:
            try:
                validate_email(email)
            except ValidationError:
                add_error('email', _('Email inválido.'))

        phone_raw = row.get('telefone', '').strip()
        if not phone_raw:
            add_error('phone', _('Telefone é obrigatório. Informe DDI e apenas números.'))
        elif not phone_raw.isdigit():
            add_error('phone', _('Telefone deve conter apenas números. Ex: 5511999999999.'))
        elif len(phone_raw) < 11:
            add_error('phone', _('Telefone deve incluir DDI (mínimo 11 dígitos).'))

        document = clean_identification_document(row.get('documento_identificacao', ''))
        if not document:
            add_error('identification_document', _('Documento é obrigatório.'))
        else:
            if document in seen_documents:
                add_error('identification_document', _('Documento duplicado no arquivo.'))
            elif document in existing_documents:
                add_error('identification_document', _('Documento já cadastrado no sistema.'))
            else:
                seen_documents.add(document)

        sex_value = row.get('sexo', '').strip().lower()
        normalized_sex = SEX_MAP.get(sex_value, '')
        if sex_value and not normalized_sex:
            add_error('sex', _('Sexo inválido. Valores aceitos: masculino, feminino, outro, prefere não informar.'))

        hire_date_str = row.get('data_admissao', '').strip()
        hire_date = _parse_date(hire_date_str)
        if hire_date_str and not hire_date:
            add_error('hire_date', _('Data inválida. Utilize DD/MM/YYYY.'))

        birth_date_str = row.get('data_nascimento', '').strip()
        birth_date = _parse_date(birth_date_str)
        if birth_date_str and not birth_date:
            add_error('birth_date', _('Data inválida. Utilize DD/MM/YYYY.'))

        status_value = row.get('status', 'active').strip().lower()
        if status_value not in ['active', 'inactive', 'pending']:
            add_error('status', _('Status inválido. Use active, inactive ou pending.'))

        member_data = {
            'line_number': line_number,
            'name': name,
            'email': email,
            'phone': phone_raw,
            'identification_document': document,
            'department': row.get('departamento', '').strip(),
            'regional': row.get('regional', '').strip(),
            'role_type': normalized_role,
            'position': row.get('cargo', '').strip(),
            'sex': normalized_sex,
            'birth_date': birth_date,
            'dealership': row.get('dealership', '').strip(),
            'dealership_number': row.get('dealership_number', '').strip(),
            'status': status_value if status_value in ['active', 'inactive', 'pending'] else 'active',
            'chatbots': row.get('chatbots', '').strip(),
            'city': row.get('cidade', '').strip(),
            'state': row.get('estado', '').strip(),
            'country': row.get('pais', '').strip(),
            'hire_date': hire_date,
            'errors': row_errors,
        }
        
        members_data.append(member_data)
    
    return members_data


from django.db.models import Prefetch


def generate_csv_export(members):
    """
    Generate CSV export for members

    Args:
        members: QuerySet of CompanyMember

    Returns:
        CSV string
    """
    members = members.prefetch_related(
        Prefetch(
            'chatbot_accesses',
            queryset=CompanyMember.chatbot_accesses.field.model.objects.filter(status='active')
                                         .select_related('chatbot'),
            to_attr='_active_chatbot_accesses'
        )
    )
    output = io.StringIO()
    writer = csv.writer(output, delimiter=';')
    
    # Write header
    writer.writerow([
        'nome', 'email', 'telefone', 'documento_identificacao', 'departamento',
        'regional', 'tipo_cargo', 'cargo', 'sexo', 'data_nascimento', 'data_admissao',
        'cidade', 'estado', 'pais', 'dealership', 'dealership_number', 'status', 'chatbots'
    ])
    
    # Write data
    for member in members:
        chatbots = ','.join(
            acc.chatbot.name for acc in getattr(member, '_active_chatbot_accesses', [])
        )
        
        writer.writerow([
            member.name,
            member.email,
            member.phone,
            member.identification_document,
            member.department,
            member.regional,
            member.get_role_type_display() if member.role_type else '',
            member.position,
            member.get_sex_display() if member.sex else '',
            member.birth_date.strftime('%d/%m/%Y') if member.birth_date else '',
            member.hire_date.strftime('%d/%m/%Y') if member.hire_date else '',
            member.city,
            member.state,
            member.country,
            member.dealership,
            member.dealership_number,
            member.status,
            chatbots
        ])
    
    return output.getvalue()


def validate_csv_structure(csv_file):
    """
    Validate CSV file structure
    
    Args:
        csv_file: UploadedFile object
    
    Returns:
        Tuple (is_valid, error_message)
    """
    try:
        raw_data = csv_file.read()
        try:
            file_data = raw_data.decode('utf-8')
        except UnicodeDecodeError:
            try:
                file_data = raw_data.decode('latin-1')
            except UnicodeDecodeError:
                file_data = raw_data.decode('cp1252', errors='ignore')
        csv_file.seek(0)  # Reset file pointer
        delimiter = _detect_delimiter(file_data)
        csv_reader = csv.DictReader(io.StringIO(file_data), delimiter=delimiter)
        
        # Check required columns
        required_columns = ['nome', 'email', 'documento_identificacao', 'telefone']
        headers = csv_reader.fieldnames
        
        if not headers:
            return False, _('Arquivo CSV vazio ou inválido')
        
        missing_columns = [col for col in required_columns if col not in headers]
        if missing_columns:
            return False, _('Colunas obrigatórias faltando: {}').format(', '.join(missing_columns))
        
        return True, None
    
    except Exception as e:
        return False, str(e)
