import json

def get_system_prompt(current_state, world_context):
  """
  Dynamically creates the System Prompt depending on the FSM state.
  Specialized for the Energy Grid Balancer Domain.
  """
  state_name = current_state.name if hasattr(current_state, 'name') else current_state

  # Base Persona & Format (Persona Reference?!?)
  base_prompt = """
  You are an Autonomous Energy Grid Balancer. 
  Your goal is to match Energy Supply with Demand while minimizing cost and preventing blackouts.

  CRITICAL RULES:
  1. You must output ONLY valid JSON. No markdown, no conversational text.
  2. You must follow the Finite State Machine logic provided below.
  3. Always include a "thought" field explaining your reasoning step-by-step.
  4. Prioritize Renewable Energy (Solar/Wind) because it is cheap.
  5. Use Gas only if Renewables are insufficient.

  RESPONSE FORMAT:
  {
    "thought": "Step-by-step reasoning...",
    "action_type": "TOOL_CALL" or "TRANSITION",
    "target": "Tool Name" or "Next State Name",
    "params": { ... arguments for the tool ... }
  }
  """

  # State-Specific Instructions
  

  # State 0: Initializing
  if state_name == "INITIALIZING":
    return base_prompt + """
    CURRENT STATE: INITIALIZING
    Task: The system is starting up.
    Action: Return a TRANSITION to "DEMAND_FORECASTING".
    """
  
  # State 1: Demand Forecasting (Tool Call)
  elif current_state == "DEMAND_FORECASTING":
    return base_prompt + """
    CURRENT STATE: DEMAND_FORECASTING
    Task: Predict the energy demand for the next hour.
    Action: Return a TOOL_CALL for 'forecast_energy_demand' with params {"hour_offset": 1}.
    """
  
  # State 2: Capacity Analysis (Tool Call)
  elif current_state == "CAPACITY_ANALYSIS":
    return base_prompt + """
    CURRENT STATE: CAPACITY_ANALYSIS
    Task: Check current generation capacity.
    Action: Return a TOOL_CALL for 'check_generation_capacity' with params {}.
    """
  
  # State 3: Dispatch Planning (The Brain/Reasoning)
  elif current_state == "DISPATCH_PLANNING":
    # Extracting data from memory for LLM to view
    demand = world_context.get('forecast_mw', 0)
    caps = world_context.get('capacity', {})

    return base_prompt + f"""
    CURRENT STATE: DISPATCH_PLANNING

    --- LIVE DATA ---
    Forecasted Demand: {demand} MW
    Available Capacity: {json.dumps(caps)}
    -----------------

    Task: Create a dispatch plan to meet the demand.

    LOGIC RULES:
    1. Use all available Solar and Wind first (Renewables).
    2. If (Solar+Wind) < Demand, use Gas up to its limit.
    3. If (Solar+Wind+Gas) < Demand, the rest is Load Shedding (implicit).

    Action: Return a TOOL_CALL for 'dispatch_energy_plan'.
    The params must contain a 'distribution' dictionary.

    Example Params:
    {{
      "distribution": {{ "solar": 50.5, "wind": 20.0, "gas": 100.0 }}
    }}
    """
  
  # State 4: Execution (Transition)
  elif current_state == "EXECUTION":
    return base_prompt + """
    CURRENT STATE: EXECUTION
    Task: The plan has been sent to the grid. Now check if it worked.
    Action: Return a TRANSITION to "STABILITY_CHECK".
    """
  
  # State 5: Stability Check (Evaluation)
  elif current_state == 'STABILITY_CHECK':
    metrics = world_context.get('last_metrics', {})

    return base_prompt + f"""
    CURRENT STATE: STABILITY_CHECK

    --- GRID STATUS ---
    {json.dumps(metrics)}
    -------------------

    Task: Evaluate the result.
    - If 'blackout_risk' is 'High' OR 'frequency_deviation' is large (> 0.05), it is a FAILURE.
    - Otherwise, it is a SUCCESS.

    Action:
    - If FAILURE -> Return a TRANSITION to "ADJUSTMENT".
    - If SUCCESS -> Return a TRANSITION to "TERMINATED".
    """

  # State 6: Adjustment (Replanning)
  elif current_state == "ADJUSTMENT":
    return base_prompt + """
    CURRENT STATE: ADJUSTMENT
    Task: The previous plan was unstable.
    Action: Return a TRANSITION to "DISPATCH_PLANNING" to try a safer distribution (e.g., use more Gas if available).
    """
  
  return base_prompt + f"\nCURRENT STATE: {state_name}\nAction: Return a TRANSITION to 'TERMINATED'."