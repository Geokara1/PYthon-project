import random
from typing import Dict, Any

# WORLD STATE: Η "αλήθεια" του περιβάλλοντος.
# Ο πράκτορας δεν έχει άμεση πρόσβαση εδώ, μόνο μέσω των tools.
WORLD_STATE = {
    "current_hour": 12,          # 0-23
    "weather_condition": "sunny", # sunny, cloudy, stormy
    "gas_reserve_mw": 500.0,     # Περιορισμένο απόθεμα φυσικού αερίου
    "grid_load_base": 150.0      # Βασικό φορτίο δικτύου
}

def forecast_energy_demand(hour_offset: int) -> float:
    """
    Προβλέπει τη ζήτηση ενέργειας (MW) για μια μελλοντική ώρα.
    
    Args:
        hour_offset: Πόσες ώρες μετά την τρέχουσα ώρα θέλουμε την πρόβλεψη.
        
    Returns:
        float: Η αναμενόμενη ζήτηση σε Megawatts.
    """
    target_hour = (WORLD_STATE["current_hour"] + hour_offset) % 24
    
    # Προσομοίωση καμπύλης ζήτησης: 
    # Χαμηλή τη νύχτα, αύξηση το πρωί, peak το απόγευμα (18:00-21:00)
    if 0 <= target_hour <= 6:
        multiplier = 0.5
    elif 7 <= target_hour <= 16:
        multiplier = 1.2
    elif 17 <= target_hour <= 21:
        multiplier = 2.0  # Peak demand
    else:
        multiplier = 1.0
        
    demand = WORLD_STATE["grid_load_base"] * multiplier
    # Προσθήκη μικρού θορύβου για ρεαλισμό
    return round(demand + random.uniform(-5, 5), 2)

def check_generation_capacity() -> Dict[str, float]:
    """
    Ελέγχει τη διαθέσιμη παραγωγή ενέργειας ανά πηγή την τρέχουσα στιγμή.
    Λαμβάνει υπόψη την ώρα (για ηλιακά) και τις καιρικές συνθήκες.
    
    Returns:
        dict: {'solar': float, 'wind': float, 'gas': float} σε MW.
    """
    hour = WORLD_STATE["current_hour"]
    weather = WORLD_STATE["weather_condition"]
    
    # Solar Logic: 0 τη νύχτα, peak το μεσημέρι, μειωμένο αν έχει συννεφιά
    if 6 <= hour <= 18:
        solar_base = 100.0 if weather == "sunny" else 30.0
        solar_cap = solar_base * (1 - abs(hour - 12) / 6)
    else:
        solar_cap = 0.0
        
    # Wind Logic: Περισσότερο αν έχει καταιγίδα, τυχαίο εύρος αλλιώς
    if weather == "stormy":
        wind_cap = random.uniform(80, 120)
    else:
        wind_cap = random.uniform(10, 50)
        
    # Gas Logic: Σταθερή πηγή αλλά εξαρτάται από το απόθεμα
    gas_cap = min(200.0, WORLD_STATE["gas_reserve_mw"])
    
    return {
        "solar": round(max(0, solar_cap), 2),
        "wind": round(wind_cap, 2),
        "gas": round(gas_cap, 2)
    }

def dispatch_energy_plan(distribution: Dict[str, float]) -> Dict[str, Any]:
    """
    Εφαρμόζει το πλάνο κατανομής ενέργειας στο δίκτυο και επιστρέφει μετρικές ευστάθειας.
    
    Args:
        distribution: Dictionary με MW ανά πηγή, π.χ. {"solar": 50, "wind": 20, "gas": 80}
        
    Returns:
        dict: Μετρικές όπως 'frequency_deviation' και 'blackout_risk'.
    """
    # 1. Υπολογισμός πραγματικής ζήτησης (ground truth)
    actual_demand = forecast_energy_demand(0)
    
    # 2. Υπολογισμός συνολικής προσφοράς από το πλάνο
    total_supply = sum(distribution.values())
    
    # 3. Έλεγχος αν το πλάνο είναι εφικτό βάσει των αποθεμάτων αερίου
    gas_requested = distribution.get("gas", 0)
    if gas_requested > WORLD_STATE["gas_reserve_mw"]:
        return {
            "status": "FAILED",
            "error": "Insufficient gas reserves",
            "blackout_risk": "CRITICAL"
        }
    
    # Ενημέρωση World State (State Persistence)
    WORLD_STATE["gas_reserve_mw"] -= gas_requested
    WORLD_STATE["current_hour"] = (WORLD_STATE["current_hour"] + 1) % 24
    
    # 4. Υπολογισμός ευστάθειας (Balance)
    diff = total_supply - actual_demand
    freq_dev = diff * 0.001 # Απλοϊκό μοντέλο: πλεόνασμα αυξάνει τη συχνότητα
    
    risk = "Low"
    if abs(diff) > 50:
        risk = "High"
    elif abs(diff) > 20:
        risk = "Medium"
        
    return {
        "status": "SUCCESS",
        "actual_demand_mw": actual_demand,
        "total_supply_mw": total_supply,
        "frequency_deviation": round(freq_dev, 4),
        "blackout_risk": risk,
        "remaining_gas": round(WORLD_STATE["gas_reserve_mw"], 2)
    }
