import re

def parse_volume_string(text_string):
    if not text_string:
        return None
    
    match = re.search(r'(\d+\.?\d*)\s*(ltr|ml|l|g|kg|liter|litre|liters|milliliters|grams|kilograms|oz|ounce|fl\s?oz|fluid\sounces?)\b', text_string, re.I)
    if not match:
        return None
        
    quantity = float(match.group(1))
    unit = match.group(2).lower().strip()
    normalized_value = quantity
    
    if 'milliliter' in unit or unit == 'ml':
        unit = 'ml'
    elif 'liter' in unit or unit == 'l' or unit == 'ltr':
        normalized_value = quantity * 1000
        unit = 'L'
    elif 'gram' in unit or unit == 'g':
        unit = 'g'
    elif 'kilogram' in unit or unit == 'kg':
        normalized_value = quantity * 1000
        unit = 'kg'
    elif 'oz' in unit or 'ounce' in unit:
        normalized_value = quantity * 29.5735
        unit = 'fl oz'

    return {'quantity': quantity, 'unit': unit, 'normalized': normalized_value}

def parse_count_string(text_string):
    if not text_string:
        return None

    match = re.search(r'(\d+)(?:\s+\w+){0,2}\s*(wipes|count|sheets|sachets|pack|pcs|pieces|pc)\b|\b(wipes|count|sheets|sachets|pack|pcs|pieces|pc)(?:\s+\w+){0,2}\s*(\d+)', text_string, re.I)
    if not match:
        return None
    if match.group(1) and match.group(2):
        quantity = int(match.group(1))
    elif match.group(3) and match.group(4):
        quantity = int(match.group(4))
    else:
        return None
    return {'quantity': quantity, 'unit': 'units', 'normalized': quantity}

def parse_saco_count_string(text_string):
    if not text_string:
        return None
    
    match = re.search(r'(\d+)\s*-\s*(piece|wipes|rags)\b', text_string, re.I)
    if not match:
        return None
        
    quantity = int(match.group(1))
    return {'quantity': quantity, 'unit': 'units', 'normalized': quantity}

def parse_volume_with_multiplier(text_string):
    """
    Parsea una cadena para extraer el volumen, manejando formatos simples (ej. "5 LTR")
    y formatos con multiplicador (ej. "6x500ml", "6 Pcs X 3 LTR").
    """
    if not text_string:
        return None

    base_volume_data = parse_volume_string(text_string)
    if not base_volume_data:
        return None # Si no hay una unidad de volumen base (ml, L, etc.), no podemos continuar.

    multiplier = 1
    # Buscar patrones de multiplicador como "6x", "6 X", "6PcsX", "pack of 6"
    multiplier_match = re.search(r'(\d+)\s*[xX]\s*|(\d+)\s*Pcs\s*[xX]\s*', text_string, re.I)
    
    if multiplier_match:
        # Encontrar cuál de los grupos de captura tiene el número
        found_multiplier = multiplier_match.group(1) or multiplier_match.group(2)
        if found_multiplier:
            multiplier = int(found_multiplier)

    # Calcular la cantidad total
    total_quantity = base_volume_data['quantity'] * multiplier
    
    return {
        'quantity': total_quantity,
        'unit': base_volume_data['unit'],
        'normalized': base_volume_data['normalized'] * multiplier
    }
