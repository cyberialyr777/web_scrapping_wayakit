INSTRUCTIONS_FILE = 'analysis.csv'
OUTPUT_CSV_FILE = 'final_results_test.csv'
CSV_COLUMNS = [
    'date', 'industry', 'subindustry', 'type_of_product', 'generic_product_type',
    'product', 'price_sar', 'company', 'source', 'url',
    'unit_of_measurement', 'total_quantity'
]

TARGET_MAP = {
    'Home': ['amazon', 'mumzworld', 'saco'],
    'Automotive': ['amazon', 'saco'],
    'Pets': ['amazon'],
}

MUMZWORLD_EXCLUSIONS = [
    'oven and grill cleaner',
    'shower and tub cleaner',
    'mold and mildew remover',
    'general sanitizer for vegetable and salad washing',
    'tile and laminate cleaner',
    'wax and floor polish',
    'carpet shampoo',
    'spot remover for carpets',
    'leather cleaner',
]

SACO_EXCLUSIONS = [
    'microfiber for vehicle cleaning',
    'long brush for seating cleaning',
    'general sanitizer for vegetable and salad washing',
    'fabric refresher',
    'car surface disinfectant wet rags',
    'car water spot remover',
    'car bug and poop remover',
    'waterless car wash product',
    'car surface disinfectant',
    'car gum remover',
]

# USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/108.0.0.0 Safari/537.36"
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"