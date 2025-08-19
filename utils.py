import re

def parse_volume_string(text_string):
    if not text_string:
        return None
    
    match = re.search(r'(\d+\.?\d*)\s*(ml|l|g|kg|liter|litre|liters|milliliters|grams|kilograms|oz|ounce|fluid\sounces?)\b', text_string, re.I)
    if not match:
        return None
        
    quantity = float(match.group(1))
    unit = match.group(2).lower().strip()
    normalized_value = quantity
    
    if 'milliliter' in unit or unit == 'ml':
        unit = 'ml'
    elif 'liter' in unit or unit == 'l':
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
