"""
QC-Check 02 — Cost Estimation Module
Calculates estimated cost based on components list.
"""
import re

# Mock Cost Database
# Maps Part Number OR Name keywords to Price
COST_DB = {
    # Keywords
    "connector": 5.50,
    "cable": 2.00,
    "wire": 0.50,
    "shield": 1.20,
    "jacket": 0.80,
    "relief": 0.30,
    "contact": 0.10,
    "housing": 1.50,
    "label": 0.05,
    "tube": 0.20,
    # Specific Part Numbers (Examples)
    "ha-190031": 15.00,
    "m12-5p": 8.00,
}

def calculate_estimate(components: list) -> dict:
    """
    Calculate cost estimate from a list of components.
    
    Args:
        components: List of dicts
        
    Returns:
        {
            "items": [
                {"name": "...", "part_number": "...", "unit_price": 0.0, "total": 0.0}
            ],
            "total_cost": 0.0,
            "currency": "USD"
        }
    """
    items = []
    total_cost = 0.0
    
    for comp in components:
        name = comp.get("name", "Unknown")
        part_num = comp.get("part_number", "")
        count_raw = comp.get("count", 1)
        
        # Parse count
        count = 1
        if isinstance(count_raw, (int, float)):
            count = count_raw
        elif isinstance(count_raw, str):
            match = re.search(r'\d+(\.\d+)?', count_raw)
            if match:
                count = float(match.group())
        
        # Find price (Try Part Number first, then Name)
        price = 0.0
        match_key = None
        
        if part_num:
            pn_lower = str(part_num).lower()
            for key, val in COST_DB.items():
                if key in pn_lower:
                    price = val
                    match_key = key + " (PN)"
                    break
        
        if price == 0.0:
            name_lower = name.lower()
            for key, val in COST_DB.items():
                if key in name_lower:
                    price = val
                    match_key = key
                    break
                
        # Default price
        if price == 0.0:
            price = 1.0 
            
        item_total = price * count
        total_cost += item_total
        
        items.append({
            "name": name,
            "part_number": part_num,
            "count": count,
            "unit_price": price,
            "total": item_total,
            "matched_type": match_key or "estimate"
        })
        
    return {
        "items": items,
        "total_cost": round(total_cost, 2),
        "currency": "USD"
    }
