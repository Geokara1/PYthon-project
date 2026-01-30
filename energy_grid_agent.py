import json
import time
import logging
import random
from enum import Enum, auto

# 1. EXECUTION TRACE LOGGING 
# Ρυθμίζουμε το logging ώστε να εμφανίζει STATE, PROMPT, RAW LLM, ACTION.
# Αυτά τα logs είναι υποχρεωτικά παραδοτέα (Killer Criterion)

logging.basicConfig(
    level=logging.INFO, 
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%H:%M:%S'
)

# 2. FORMAL STATE MODE
# Περιλαμβάνουμε το ADJUSTMENT για την απαίτηση Replanning 

class AgentState(Enum):
    INITIALIZING = auto()       
    DEMAND_FORECASTING = auto() # Tool 1
    CAPACITY_ANALYSIS = auto()  # Tool 2
    DISPATCH_PLANNING = auto()  # LLM Policy
    EXECUTION = auto()          # Tool 3
    STABILITY_CHECK = auto()    
    ADJUSTMENT = auto()         # Διόρθωση/Replanning 
    TERMINATED = auto()         


# 3. THE AGENT CLASS 
class EnergyGridAgent:
    def __init__(self):
    # current_state: Η μεταβλητή ελέγχου της FSM 
        self.current_state = AgentState.INITIALIZING
        self.is_running = True
        
        # OBSERVATIONS (O)
        self.memory = {
            "forecast_mw": 0.0,
            "capacity": {},
            "last_metrics": {}
        }
        
        # SLIDING WINDOW MEMORY 
        # Το LLM είναι stateless
        # το ιστορικό των τελευταίων N βημάτων για να υπάρχει συνείδηση
        self.history = []
        self.max_history = 5

    def get_system_prompt(self):
        """
        #CONSTRAINT ENFORCEMENT 
        #Ο κώδικας ελέγχει το current_state ΠΡΙΝ καλέσει το LLM και 
        προσαρμόζει το System Prompt. Έτσι, ο πράκτορας γνωρίζει 
        τους περιορισμούς της τρέχουσας κατάστασης.
        """
        prompts = {
            AgentState.INITIALIZING: "System Check mode. Verify all grid sensors.",
            AgentState.DEMAND_FORECASTING: "Forecasting mode. Use weather data to predict MW demand.",
            AgentState.CAPACITY_ANALYSIS: "Resource Analysis mode. Evaluate Solar, Wind, and Gas availability.",
            AgentState.DISPATCH_PLANNING: "Planning mode. Balance supply/demand with minimum cost.",
            AgentState.STABILITY_CHECK: "Evaluation mode. If blackout risk is High, you MUST trigger ADJUSTMENT.",
            AgentState.ADJUSTMENT: "Replanning mode. Modify the previous failed plan to restore stability."
        }
        return prompts.get(self.current_state, "You are an Energy Grid Balancer.")

    def observe(self):
        """
        OBSERVE 
        Συλλογή δεδομένων από το περιβάλλον (Tools). 
        Εδώ ο R2 θα συνδέσει τις πραγματικές συναρτήσεις.
        """
        logging.info(f"[STATE]: {self.current_state.name}")
        return self.memory

    def think(self, observations):
        
        #THINK 
        
        system_prompt = self.get_system_prompt()
        logging.info(f"[PROMPT]: {system_prompt}")

        # Προσομοίωση απόκρισης LLM σε μορφή JSON String
        # Ο R3 θα αντικαταστήσει αυτή τη λογική με πραγματικό API call
        decision_logic = self._mock_llm_logic()
        
        # Μετατροπή σε JSON String για προσομοίωση του API 
        raw_llm_json = json.dumps(decision_logic)
        logging.info(f"[RAW LLM]: {raw_llm_json}")
        
        # JSON Parsing: Μετατροπή του string πίσω σε Python αντικείμενο
        return json.loads(raw_llm_json)

    def act(self, decision):

        #ACT Εκτέλεση της απόφασης του LLM
        #Διαχωρίζει τις ενέργειες σε Tool Calls και Transitions
        
        action_type = decision.get("action_type")
        target = decision.get("target")

        if action_type == "TRANSITION":
            # Δυναμική μετάβαση βάσει κρίσης LLM 
            logging.info(f"[ACTION]: Transitioning to {target}")
            self.current_state = AgentState[target]
        
        elif action_type == "TOOL_CALL":
            # Κλήση εξωτερικής συνάρτησης 
            logging.info(f"[ACTION]: Calling Tool {target} with params {decision.get('params')}")
            self._update_memory_from_tool(target, decision.get('params'))

        # Έλεγχος για τερματισμό
        if self.current_state == AgentState.TERMINATED:
            self.is_running = False

    def _update_memory_from_tool(self, tool_name, params):
        """
        INTERFACE με τα TOOLS του R2
        Εδώ ενημερώνεται τα Observations 
        μετά από κάθε κλήση εργαλείου.
        """
        if tool_name == "forecast_demand":
            self.memory["forecast_mw"] = 120.5 # Mock τιμή
        elif tool_name == "check_capacity":
            self.memory["capacity"] = {"solar": 40, "wind": 20, "gas": 100}

    def _mock_llm_logic(self):
        """
        MOCK POLICY 
        Προσομοιώνει πώς το LLM θα επέλεγε την επόμενη κίνηση
        Θα αντικατασταθεί πλήρως από τον R3
        """
      
        if self.current_state == AgentState.DEMAND_FORECASTING and self.memory["forecast_mw"] > 0:
            return {"action_type": "TRANSITION", "target": "CAPACITY_ANALYSIS"}
            
        # Default ροή
        mapping = {
            AgentState.INITIALIZING: {"action_type": "TRANSITION", "target": "DEMAND_FORECASTING"},
            AgentState.CAPACITY_ANALYSIS: {"action_type": "TRANSITION", "target": "DISPATCH_PLANNING"},
            AgentState.DISPATCH_PLANNING: {"action_type": "TRANSITION", "target": "EXECUTION"},
            AgentState.EXECUTION: {"action_type": "TRANSITION", "target": "STABILITY_CHECK"},
            AgentState.STABILITY_CHECK: {"action_type": "TRANSITION", "target": "TERMINATED"}
        }
        return mapping.get(self.current_state, {"action_type": "TRANSITION", "target": "TERMINATED"})

    def run(self):
        
        #THE CONTROL LOOP (Observe -> Think -> Act)
        
        #Περιλαμβάνει Max Steps για αποφυγή ατέρμονων βρόχων.
        
        logging.info("--- AGENT EXECUTION STARTED ---")
        step = 0
        while self.is_running and step < 15:
            # 1. OBSERVE
            obs = self.observe()
            
            # 2. THINK
            decision = self.think(obs)
            
            # 3. ACT
            self.act(decision)
            
            # Sliding Window
            # Αποθηκεύουμε το βήμα στο ιστορικό και αφαιρούμε το παλαιότερο αν ξεπερασουμε το οριο
            self.history.append({
                "step": step, 
                "state": self.current_state.name, 
                "decision": decision
            })
            if len(self.history) > self.max_history:
                self.history.pop(0) 
                
            step += 1
            time.sleep(0.5) # Καθυστέρηση για αναγνωσιμότητα των logs
        logging.info("--- AGENT EXECUTION TERMINATED ---")


# 4. ENTRY POINT
if __name__ == "__main__":
    # Δημιουργία και εκκίνηση του πράκτορα
    agent = EnergyGridAgent()
    agent.run()