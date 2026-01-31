import json
import time
import logging
import random
from enum import Enum, auto

#Import modules from team members

import tools          # Environment & Tools (R2)
import prompts        # Policy Prompts (R3)
import llm_engine     # LLM Connectivity (R3)



# 1. EXECUTION TRACE LOGGING 
# Configured to display [STATE], [PROMPT], [RAW LLM], [ACTION], [OBSERVATION].
# These logs are mandatory deliverables (Killer Criterion).

logging.basicConfig(
    level=logging.INFO, 
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%H:%M:%S'
)

# 2. FORMAL STATE MODE - STATES
# Includes the ADJUSTMENT state for the mandatory Replanning requirement.

class AgentState(Enum):
    INITIALIZING = auto()       
    DEMAND_FORECASTING = auto() # Tool 1: Load Prediction
    CAPACITY_ANALYSIS = auto()  # Tool 2: Resource Check
    DISPATCH_PLANNING = auto()  # LLM Policy Decision
    EXECUTION = auto()          # Tool 3: Grid Application
    STABILITY_CHECK = auto()    # Feedback Loop Evaluation
    ADJUSTMENT = auto()         # Replanning / Correction State
    TERMINATED = auto()         # Final State


# 3. THE AGENT CLASS 
class EnergyGridAgent:
    
    def __init__(self,hf_token=None): #SOS Hf_token For API key
    # current_state: The FSM control variable
        self.current_state = AgentState.INITIALIZING
        self.is_running = True
        
        # OBSERVATIONS (O): The agent's internal memory of the world
        self.memory = {
            "forecast_mw": 0.0,
            "capacity": {},
            "last_metrics": {}
        }
        
        # SLIDING WINDOW MEMORY 
        #  LLM is stateless
        # Maintains the last N steps to provide context to the stateless LLM.
        self.history = []
        self.max_history = 6
        # LLM Engine provided by the Cognitive Policy Engineer (R3)
        self.llm = llm_engine.LLMEngine(api_token=hf_token)
         
    def observe(self):
        """
        OBSERVE: Collect current internal state and memory
             
        """
        logging.info(f"[STATE]: {self.current_state.name}")
        return self.memory

    def think(self, observations):
        
        #THINK 
        
        # system Prompt απο Cοnstraint Enforcement
        system_prompt = prompts.get_system_prompt(self.current_state, observations)
        
        # Log the actual prompt sent to LLM
        logging.info(f"[PROMPT]: {system_prompt}")
        
        # Use Self.llm which is in __init__
         # Call the get_decision method of Constraint Enforcement
        decision = self.llm.get_decision(system_prompt, self.history)

        logging.info(f"[RAW LLM]: {json.dumps(decision)}")

        
        return decision

    def act(self, decision):

        # ACT Execution of the LLM decision
        # Separates actions into Tool Calls and Transitions
        
        action_type = decision.get("action_type")
        target = decision.get("target")
        params =decision.get("params",{})

        if action_type == "TRANSITION":
                logging.info(f"[ACTION]: Transitioning to {target}")
                try:
                # Convert String from LLM to AgentState Enum
                    self.current_state = AgentState[target]
                except KeyError:
                    logging.error(f"Invalid State Name: {target}. Defaulting to ADJUSTMENT.")
                    self.current_state = AgentState.ADJUSTMENT
        
        elif action_type == "TOOL_CALL":
            # External function call
            logging.info(f"[ACTION]: Executing Tool {target}")
            self._update_memory_from_tool(target, params)

        # Check for termination
        if self.current_state == AgentState.TERMINATED:
            self.is_running = False

    def _update_memory_from_tool(self, tool_name, params):
        """
        INTERFACE with R2 TOOLS
        Observations are updated here
        after each tool call.
        """
         # 1. Connection with Demand Forecasting Tool
        if tool_name == "forecast_energy_demand":
        # Receive parameter from LLM
            offset = params.get("hour_offset", 1)
        # Call the actual R2 tool
            res = tools.forecast_energy_demand(offset)
        # Update the agent's "Truth"
            self.memory["forecast_mw"] = res
            logging.info(f"[OBSERVATION]: Predicted demand: {res} MW")

    # 2. Connection with Source Control Tool
        elif tool_name == "check_generation_capacity":
        # Call the R2 tool
            res = tools.check_generation_capacity()
            self.memory["capacity"] = res
            logging.info(f"[OBSERVATION]: Available capacity: {res}")

    # 3. Connection with Plan Execution Tool
        elif tool_name == "dispatch_energy_plan":
        # Receive the plan decided by the LLM
            dist = params.get("distribution", {})
        # Implementation on the grid via R2
            res = tools.dispatch_energy_plan(dist)
        # Store stability metrics (Critical for Feedback Loop)
            self.memory["last_metrics"] = res

            
            logging.info(f"[OBSERVATION]: Grid Metrics: {res}")
    
    def run(self):
        """
        THE CONTROL LOOP: Observe -> Think -> Act (PDF Σελ. 7)
        The central loop that makes the agent autonomous.
        """
        logging.info("--- AGENT EXECUTION STARTED ---")
        step = 0
        max_steps = 15 # Protection from infinite loops

        while self.is_running and step < max_steps:
            logging.info(f"\n=== STEP {step} | STATE: {self.current_state.name} ===")

            # 1. OBSERVE: Data collection from the environment (R2)
            # Now observe() returns actual data from tools.py
            observations = self.observe()
            
            # 2. THINK: Decision making from the actual LLM (R3)
            # think() now calls LLMEngine and Qwen 2.5
            decision = self.think(observations)
            
            # 3. SLIDING WINDOW: Update history
            # CHANGE: We store the decision in a format understood by the LLM (role-based)
            self.history.append({
                "role": "assistant", 
                "content": json.dumps(decision)
            })
            
            # Keep only the last N steps (Sliding Window)
            if len(self.history) > self.max_history:
                self.history.pop(0)

            # 4. ACT: Python Execution
            # act() now calls the actual tools and changes the State
            self.act(decision)
            
            step += 1
            time.sleep(1) # Pause for synchronization and log reading

        logging.info(f"--- AGENT EXECUTION TERMINATED at Step {step} ---")

# 4. ENTRY POINT
if __name__ == "__main__":
    # Creation and startup of the agent
    agent = EnergyGridAgent()
    agent.run()