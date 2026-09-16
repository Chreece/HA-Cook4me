"""Read explicit package amounts without inferring weight, density or servings."""
import math
import re

_UNITS = {
    'g': 'g', 'gr': 'g', 'gram': 'g', 'grams': 'g', 'gramm': 'g',
    'kg': 'kg', 'ml': 'ml', 'cl': 'cl', 'l': 'l',
    'pc': 'pcs', 'pcs': 'pcs', 'piece': 'pcs', 'pieces': 'pcs',
    'stück': 'pcs', 'stuck': 'pcs', 'stk': 'pcs',
    'egg': 'pcs', 'eggs': 'pcs', 'ei': 'pcs', 'eier': 'pcs',
    'œuf': 'pcs', 'œufs': 'pcs', 'oeuf': 'pcs', 'oeufs': 'pcs',
}
_NUMBER = r'\d+(?:[.,]\d{1,2})?'
_AMOUNT = re.compile(rf'(?:(\d+)\s*[x×]\s*)?({_NUMBER})\s*([a-zœü]+)\.?', re.I)


def _positive(value):
    if isinstance(value, bool):
        return None
    try:
        value = float(str(value).replace(',', '.'))
        return value if math.isfinite(value) and value > 0 else None
    except (ValueError, TypeError):
        return None


def explicit_product_basis(product):
    quantity = _positive(product.get('product_quantity'))
    unit = _UNITS.get(str(product.get('product_quantity_unit') or '').strip().casefold())
    if quantity is not None and unit:
        return quantity, unit
    # Only the dedicated quantity field, never a name, serving size or receipt
    # line quantity. Full-string matching rejects mixed units and drained weights.
    match = _AMOUNT.fullmatch(str(product.get('quantity') or '').strip())
    if not match:
        return None, ''
    count, amount, label = match.groups()
    quantity = _positive(amount)
    count = _positive(count or 1)
    unit = _UNITS.get(label.casefold())
    if quantity is None or count is None or not unit or not math.isfinite(quantity * count):
        return None, ''
    if unit == 'pcs' and (quantity * count) % 1:
        return None, ''
    return quantity * count, unit
