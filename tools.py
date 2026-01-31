import random
from typing import Dict, Any

# 1. REPRODUCIBILITY & CONFIGURATION

# Fixed seed ensures that stochastic events (like wind noise) are 
# consistent across all team members' execution logs.
random.seed(363251497)

# Economic Parameters (Goal: Cost Minimization - PDF Page 4)
GAS_COST_PER_MW = 100.0  # Natural gas has high operational cost
RENEWABLE_COST = 0.0     # Solar and Wind are free sources




# The "Ground Truth" of the environment. The agent only sees this 
# through the observations returned by tools.
WORLD_STATE = {
    "current_hour": 12,          # 0-23
    "weather_condition": "sunny", # sunny, cloudy, stormy
    "gas_reserve_mw": 500.0,     # Total available gas fuel
    "grid_load_base": 150.0      # Base city consumption
}


def set_scenario(scenario_id: int):
    """
    Configures the environment for the 5 mandatory scenarios (PDF Page 8).
    This allows the QA Specialist (R4) to generate diverse logs.
    """
    global WORLD_STATE
    if scenario_id == 1: # Happy Path: Noon, Sunny, High Reserves
        WORLD_STATE.update({"current_hour": 12, "weather_condition": "sunny", "gas_reserve_mw": 500.0})
    elif scenario_id == 2: # Night Crisis: No solar, low wind, medium reserves
        WORLD_STATE.update({"current_hour": 22, "weather_condition": "cloudy", "gas_reserve_mw": 300.0})
    elif scenario_id == 3: # Stormy: High wind, zero solar, high demand
        WORLD_STATE.update({"current_hour": 14, "weather_condition": "stormy", "gas_reserve_mw": 400.0})
    elif scenario_id == 4: # Depletion: Critical gas levels, requires Load Shedding
        WORLD_STATE.update({"current_hour": 10, "weather_condition": "sunny", "gas_reserve_mw": 40.0})
    elif scenario_id == 5: # Peak Demand: Evening peak load, high pressure
        WORLD_STATE.update({"current_hour": 19, "weather_condition": "cloudy", "gas_reserve_mw": 500.0})

# 3. AGENT TOOLS

def forecast_energy_demand(hour_offset: int) -> float:
    """
        Predicts the expected energy demand (MW) for a future time offset.
    
    Args:
        hour_offset: Hours from the current time.
    Returns:
        float: Expected demand in Megawatts.
    
    """
    target_hour = (WORLD_STATE["current_hour"] + hour_offset) % 24
    
    # Load curve modeling (Human behavior simulation)
    if 0 <= target_hour <= 6:
        multiplier = 0.5 # Night low
    elif 7 <= target_hour <= 16:
        multiplier = 1.2 #Work hours
    elif 17 <= target_hour <= 21:
        multiplier = 2.0  # Evening peak demand
    else:
        multiplier = 1.0
        
    demand = WORLD_STATE["grid_load_base"] * multiplier
    # Add stochastic noise
    return round(demand + random.uniform(-5, 5), 2)

def check_generation_capacity() -> Dict[str, float]:
    """
    Checks current available power from all sources based on environment.
    
    Returns:
        dict: Available MW for Solar, Wind, Gas, and current Gas Reserves.
    
    """
    hour = WORLD_STATE["current_hour"]
    weather = WORLD_STATE["weather_condition"]
    
    # Solar Logic: Time and cloud dependent
    if 6 <= hour <= 18:
        solar_base = 100.0 if weather == "sunny" else 30.0
        solar_cap = solar_base * (1 - abs(hour - 12) / 6)
    else:
        solar_cap = 0.0
        
    # Wind Logic: Peak performance during stormy weather
    if weather == "stormy":
        wind_cap = random.uniform(80, 120)
    else:
        wind_cap = random.uniform(10, 50)
        
    # Gas Logic: Stable source, limited by current physical reserves
    gas_cap = min(200.0, WORLD_STATE["gas_reserve_mw"])
    
    return {
        "solar": round(max(0, solar_cap), 2),
        "wind": round(wind_cap, 2),
        "gas": round(gas_cap, 2),
        "gas_reserve": round(WORLD_STATE["gas_reserve_mw"], 2) # Crucial for Replanning 

    }

def dispatch_energy_plan(distribution: Dict[str, float]) -> Dict[str, Any]:
    """
     Applies the energy distribution plan and returns grid stability metrics.
    
    Args:
        distribution: Dict containing MW per source (solar, wind, gas).
    Returns:
        dict: Execution status, stability metrics, and operational cost.

    """
    actual_demand = forecast_energy_demand(0)
    total_supply = sum(distribution.values())
    gas_requested = distribution.get("gas", 0)


     # 1. Graceful Failure Trigger
     # If the agent requests more gas than physically available, the plan fails.
    if gas_requested > WORLD_STATE["gas_reserve_mw"]:
        return {
            "status": "FAILED",
            "error": "Insufficient gas reserves",
            "blackout_risk": "CRITICAL",
            "remaining_gas" : round(WORLD_STATE["gas_reserve_mw"], 2) #   SOSSSSSSSSSSSS8888888888
        }
    
    # 2. State Persistence: Update the world
    # Actions have permanent consequences on the environment.
    WORLD_STATE["gas_reserve_mw"] -= gas_requested
    WORLD_STATE["current_hour"] = (WORLD_STATE["current_hour"] + 1) % 24
    
    # 3. Cost and Stability Calculation
    total_cost = gas_requested * GAS_COST_PER_MW
    diff = total_supply - actual_demand 
    freq_dev = diff * 0.001 # Simplified frequency model
    
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
        "cost": total_cost,
        "remaining_gas": round(WORLD_STATE["gas_reserve_mw"], 2)
    }
