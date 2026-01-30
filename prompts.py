import json

def get_system_prompt(current_state, world_context):
  """
  Dynamically creates the System Prompt depending on the FSM state.
  Specialized for the Energy Grid Balancer Domain.
  """
  if not isinstance(current_state, str):
    current_state = current_state.name

  # Base Persona & Format (Persona Reference?!?)
  base_prompt = """
  You are an Autonomous Energy Grid Balancer Agent.
  Your goal is to match Energy Supply with Demand while minimizing cost and preventing blackouts.

  CRITICAL RULES:
  1. You must output ONLY valid JSON. No markdown, no conversational text.
  2. You must follow the Finite State Machine logic provided below.
  3. Always include a "thought" field explaining your reasoning step-by-step (Chain of Thought).

  RESPONSE FORMAT:
  {
    "thought": "Step-by-step reasoning...",
    "action_type": "TOOL_CALL" or "TRANSITION",
    "target": "Tool Name" or "Next State Name",
    "params": { ... arguments for the tool ... }
  }
  """

  # State-Specific Instructions
  state_instructions = ""

  # State 0: Initializing
  if current_state == "INITIALIZING":
    state_instructions = """
    CURRENT STATE: INITIALIZING
    Task: The system is starting up.
    Action: You MUST transition to DEMAND_FORECASTING to start the cycle.
    """
  
  # State 1: Demand Forecasting (Tool Call)
  elif current_state == "DEMAND_FORECASTING":
    state_instructions = """
    CURRENT STATE: DEMAND_FORECASTING
    Task: You need to know the expected energy demand for the next hour.
    Action: Call the tool 'forecast_energy_demand' with params {"hour_offset": 1}.
    """
  
  # State 2: Capacity Analysis (Tool Call)
  elif current_state == "CAPACITY_ANALYSIS":
    state_instructions = """
    CURRENT STATE: CAPACITY_ANALYSIS
    Task: Check available generation capacity from all sources (Solar, Wind, Gas).
    Action: Call the tool 'check_generation_capacity' with empty params {}.
    """
  
  # State 3: Dispatch Planning (The Brain/Reasoning)
  elif current_state == "DISPATCH_PLANNING":
    # Extracting data from memory for LLM to view
    demand = world_context.get('forecast_mw', 0)
    caps = world_context.get('capacity', {})

    state_instructions = f"""
    CURRENT STATE: DISPATCH_PLANNING

    --- LIVE DATA ---
    Forecasted Demand: {demand} MW
    Available Capacity: {json.dumps(caps)}
    -----------------

    Task: Create a dispatch plan to meet the demand.

    LOGIC RULES (PRIORITY):
    1. RENEWABLES FIRST: Use Solar and Wind first because they are cheap/free.
    2. GAS SECOND: Use Gas only if Renewables are not enough to meet demand.
    3. LOAD SHEDDING LAST: If (Solar + Wind + Gas) < Demand, you MUST use Load Shedding (cut power) for the difference.

    Action: Call 'dispatch_energy_plan' with arguments:
    {{
      "distribution": {{ "solar": int, "wind": int, "gas": int }},
      "load_shedding": int (amount of demand not met, 0 if fully met)
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
    - If 'blackout_risk' is 'High' OR 'frequency_deviation' > 0.05 -> FAILURE.
    - Else -> SUCCESS.

    Action:
    - If FAILURE -> Transition to ADJUSTMENT.
    - If SUCCESS -> Transition to TERMINATED (or loop back to DEMAND_FORECASTING).
    """

  # State 6: Adjustment (Replanning)
  elif current_state == "ADJUSTMENT":
    state_instructions = """
    CURRENT STATE: ADJUSTMENT
    Task: Critical failure detected! The previous plan failed.
    Action: Transition back to DISPATCH_PLANNING to try a more aggressive Load Shedding strategy to save the grid.
    """
  
  # Fallback
  else:
    state_instructions = "Unknown State. Transition to TERMINATED."
  
  return f"{base_prompt}\n\n{state_instructions}"