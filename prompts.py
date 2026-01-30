import json

def get_system_prompt(current_state, world_context):
  """
  Dynamically creates the System Prompt depending on the FSM state.
  """

  # Base Persona & Format (Persona Reference?!?)
  base_prompt = """
  You are an Autonomous Energy Grid Balancer Agent.
  Your goal is to maintain grid stability, prevent blackouts, and minimize cost.

  CRITICAL RULES:
  1. You must output ONLY valid JSON. No markdown, no conversational text.
  2. You must follow the Finite State Machine logic provided below.
  3. Always include a "thought" field explaining your reasoning step-by-step (Chain of Thought).

  RESPONSE FORMAT:
  {
    "thought": "Analysis of the situation...",
    "action_type": "TOOL_CALL" or "TRANSITION",
    "target": "Tool Name" or "Next State Name",
    "params": { ... arguments for the tool ... }
  }
  """

  # State-Specific Instructions
  state_instructions = ""

  # State 0: Initializing
  if current_state == "INITIALIZING":
    current_state = """
    CURRENT STATE: INITIALIZING
    Task: The system is starting up.
    Action: You MUST transition to DEMAND_FORECASTING to start the cycle.
    """
  
  # State 1: Demand Forecasting (Tool Call)
  elif current_state == "DEMAND_FORECASTING":
    state_instructions = """
    CURRENT STATE: DEMAND_FORECASTING
    Task: You need to know the expected energy demand for the next hour.
    Action: Call the tool 'forecast_demand' with params {"hour_offset": 1}.
    """
  
  # State 2: Capacity Analysis (Tool Call)
  elif current_state == "CAPACITY_ANALYSIS":
    state_instructions = """
    CURRENT STATE: CAPACITY_ANALYSIS
    Task: Check available generation capacity from all sources (Solar, Wind, Gas).
    Action: Call the tool 'check_capacity' with empty params {}.
    """
  
  # State 3: Dispatch Planning (The Brain/Reasoning)
  elif current_state == "DISPATCH_PLANNING":
    # Here we provide the data we collected from LLM
    forecast = world_context.get('forecast_mw', 0)
    capacity = world_context.get('capacity', {})

    state_instructions = f"""
    CURRENT STATE: DISPATCH_PLANNING

    --- LIVE DATA ---
    Forecasted Demand: {forecast} MW
    Available Capacity: {json.dumps(capacity)}
    -----------------

    Task: Create a dispatch plan to meet the demand.

    LOGIC RULES:
    1. Prioritize Renewables (Solar + Wind) first because they are cheap.
    2. Use Gas only if Renewables are not enough.
    3. If (Solar + Wind + Gas) < Demand, you MUST use Load Shedding (cut power).

    Action: Call 'dispatch_energy' with params:
    {{
      "solar": int,
      "wind": int,
      "gas": int,
      "load_shedding": int (amount of demand not met)
    }}
    """
  
  # State 4: Execution (Transition)
  elif current_state == "EXECUTION":
    state_instructions = """
    CURRENT STATE: EXECUTION
    Task: The plan has been sent to the grid. Now check if it worked.
    Action: Transition to STABILITY_CHECK.
    """
  
  # State 5: Stability Check (Evaluation)
  elif current_state == 'STABILITY_CHECK':
    metrics = world_context.get('last_metrics', {})

    state_instructions = f"""
    CURRENT STATE: STABILITY_CHECK

    --- GRID STATUS ---
    {json.dumps(metrics)}
    -------------------

    Task: Evaluate the result.
    - If 'blackout_risk' is 'High' OR 'frequency_deviation' > 0.1, you MUST transition to ADJUSTMENT.
    - Otherwise, if stable, transition to TERMINATED (or loop back to DEMAND_FORECASTING for next step).
    """

  # State 6: Adjustment (Replanning)
  elif current_state == "ADJUSTMENT":
    state_instructions = """
    CURRENT STATE: ADJUSTMENT
    Task: Critical failure detected! The previous plan failed.
    Action: Transition back to DISPATCH_PLANNING to try a safer strategy (e.g., more Gas, more Load Shedding).
    """
  
  # Fallback
  else:
    state_instructions = "Unknown State. Transition to TERMINATED."
  
  return f"{base_prompt}\n\n{state_instructions}"