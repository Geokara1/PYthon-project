import json
import time
from logger import logger
import random
from enum import Enum, auto

# Import modules from team members
import tools          # Environment & Tools (R2)
import prompts        # Policy Prompts (R3)
import llm_engine     # LLM Connectivity (R3)

# FORMAL STATE MODE - STATES

class AgentState(Enum):
    INITIALIZING = auto()       
    DEMAND_FORECASTING = auto() # Tool 1: Load Prediction
    CAPACITY_ANALYSIS = auto()  # Tool 2: Resource Check
    DISPATCH_PLANNING = auto()  # LLM Policy Decision
    EXECUTION = auto()          # Tool 3: Grid Application
    STABILITY_CHECK = auto()    # Feedback Loop Evaluation
    ADJUSTMENT = auto()         # Replanning / Correction State
    TERMINATED = auto()         # Final State

# AGENT CLASS 
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
        self.history = []
        self.max_history = 6

        # LLM Engine provided by the Cognitive Policy Engineer (R3)
        self.llm = llm_engine.LLMEngine(api_token=hf_token)
         
    def observe(self):
        """
        Collect current internal state and memory
             
        """
        logger.log("STATE", self.current_state.name)
        return self.memory

    def think(self, observations):
        """
        Generate Prompt -> Call LLM -> Get Decision
        """
        
        # system Prompt απο Cοnstraint Enforcement
        system_prompt = prompts.get_system_prompt(self.current_state, observations)
        
        # Log the actual prompt sent to LLM
        logger.log("PROMPT", system_prompt)
        
        # Call the LLM
        decision = self.llm.get_decision(system_prompt, self.history)

        logger.log("RAW LLM", json.dumps(decision))

        return decision

    def act(self, decision):
        """
        Execute the LLM decision (Transition or Tool Call)
        """
        action_type = decision.get("action_type")
        target = decision.get("target")
        params =decision.get("params",{})

        if action_type == "TRANSITION":
            logger.log("ACTION", f"Transitioning to {target}")
            try:
                # Convert String from LLM to AgentState Enum
                self.current_state = AgentState[target]
            except KeyError:
                logger.log("ERROR", f"Invalid State Name: {target}. Defaulting to ADJUSTMENT.")
                self.current_state = AgentState.ADJUSTMENT
        
        elif action_type == "TOOL_CALL":
            # External function call
            logger.log("ACTION", f"Executing Tool {target} with params {params}")
            self._update_memory_from_tool(target, params)

        # Check for termination
        if self.current_state == AgentState.TERMINATED:
            self.is_running = False

    def _update_memory_from_tool(self, tool_name, params):
        """
        INTERFACE with R2 TOOLS
        """
        try:
            # Demand Forecasting Tool
            if tool_name == "forecast_energy_demand":
                offset = params.get("hour_offset", 1)
                res = tools.forecast_energy_demand(offset)
                self.memory["forecast_mw"] = res
                logger.log("OBSERVATION", f"Predicted demand: {res} MW")

            # Source Control Tool
            elif tool_name == "check_generation_capacity":
                res = tools.check_generation_capacity()
                self.memory["capacity"] = res
                logger.log("OBSERVATION", f"Available capacity: {res}")

            #Plan Execution Tool
            elif tool_name == "dispatch_energy_plan":
                dist = params.get("distribution", {})
                res = tools.dispatch_energy_plan(dist)
                self.memory["last_metrics"] = res
                logger.log("OBSERVATION", f"Grid Metrics: {res}")

            else:
                logger.log("WARNING", f"Unknown tool called: {tool_name}")
        
        except Exception as e:
            logger.log("CRITICAL ERROR", f"Tool execution failed: {e}")
    
    def run(self):
        """
        THE CONTROL LOOP: Observe -> Think -> Act
        """
        logger.log("SYSTEM", "--- AGENT EXECUTION STARTED ---")
        step = 0
        max_steps = 20 # Protection from infinite loops

        while self.is_running and step < max_steps:
            print(f"\n--- STEP {step} ---")

            # OBSERVE
            observations = self.observe()
            
            # THINK
            decision = self.think(observations)
            
            # SLIDING WINDOW
            self.history.append({
                "role": "assistant", 
                "content": json.dumps(decision)
            })
            
            if len(self.history) > self.max_history:
                self.history.pop(0)

            # ACT
            self.act(decision)
            
            step += 1
            time.sleep(1) # Pause for readability

        logger.log("SYSTEM", f"--- AGENT EXECUTION TERMINATED at Step {step} ---")

# ENTRY POINT
if __name__ == "__main__":
    agent = EnergyGridAgent()
    agent.run()