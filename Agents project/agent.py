import json
import time
import logging
import random
from enum import Enum, auto

import tools          # Από τον R2
import prompts        # Από τον R3
import llm_engine     # Από τον R3


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
    
    def __init__(self,hf_token=None): #SOS Hf_token για API key
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
        #LLm Engine απο Cognitive Policy Engineer
        self.llm = llm_engine.LLMEngine(api_token=hf_token)
         
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
        
        # system Prompt απο Cοnstraint Enforcement
        system_prompt = prompts.get_system_prompt(self.current_state, observations)
        
        logging.info(f"[PROMPT SENT TO LLM]")
        
        # Χρήση Self.llm που ειναι στην __init__
         # Καλούμε τη μέθοδο get_decision του Constrait Enforcement
        decision = self.llm.get_decision(system_prompt, self.history)

        logging.info(f"[RAW LLM]: {json.dumps(decision)}")

        
        return decision

    def act(self, decision):

        #ACT Εκτέλεση της απόφασης του LLM
        #Διαχωρίζει τις ενέργειες σε Tool Calls και Transitions
        
        action_type = decision.get("action_type")
        target = decision.get("target")
        params =decision.get("params",{})

        if action_type == "TRANSITION":
                logging.info(f"[ACTION]: Transitioning to {target}")
                try:
                # Μετατροπή του String από το LLM στο Enum AgentState
                    self.current_state = AgentState[target]
                except KeyError:
                    logging.error(f"Invalid State Name: {target}. Defaulting to ADJUSTMENT.")
                    self.current_state = AgentState.ADJUSTMENT
        
        elif action_type == "TOOL_CALL":
            # Κλήση εξωτερικής συνάρτησης 
            logging.info(f"[ACTION]: Executing Tool {target}")
            self._update_memory_from_tool(target, params)

        # Έλεγχος για τερματισμό
        if self.current_state == AgentState.TERMINATED:
            self.is_running = False

    def _update_memory_from_tool(self, tool_name, params):
        """
        INTERFACE με τα TOOLS του R2
        Εδώ ενημερώνεται τα Observations 
        μετά από κάθε κλήση εργαλείου.
        """
         # 1. Σύνδεση με το Tool Πρόβλεψης Ζήτησης
        if tool_name == "forecast_energy_demand":
        # Λήψη παραμέτρου από το LLM (π.χ. {"hour_offset": 1})
            offset = params.get("hour_offset", 1)
        # Κλήση του πραγματικού εργαλείου του R2
            res = tools.forecast_energy_demand(offset)
        # Ενημέρωση της "Αλήθειας" του πράκτορα
            self.memory["forecast_mw"] = res
            logging.info(f"[OBSERVATION]: Predicted demand: {res} MW")

    # 2. Σύνδεση με το Tool Ελέγχου Πηγών
        elif tool_name == "check_generation_capacity":
        # Κλήση του εργαλείου του R2
            res = tools.check_generation_capacity()
            self.memory["capacity"] = res
            logging.info(f"[OBSERVATION]: Available capacity: {res}")

    # 3. Σύνδεση με το Tool Εκτέλεσης Πλάνου
        elif tool_name == "dispatch_energy_plan":
        # Λήψη του πλάνου που αποφάσισε το LLM
            dist = params.get("distribution", {})
        # Εφαρμογή στο δίκτυο μέσω του R2
            res = tools.dispatch_energy_plan(dist)
        # Αποθήκευση των metrics ευστάθειας (Κρίσιμο για το Feedback Loop)
            self.memory["last_metrics"] = res

            
            logging.info(f"[OBSERVATION]: Grid Metrics: {res}")
    
    def run(self):
        """
        THE CONTROL LOOP: Observe -> Think -> Act (PDF Σελ. 7)
        Ο κεντρικός βρόχος που καθιστά τον πράκτορα αυτόνομο.
        """
        logging.info("--- AGENT EXECUTION STARTED ---")
        step = 0
        max_steps = 15 # Προστασία από ατέρμονους βρόχους (PDF Σελ. 8)

        while self.is_running and step < max_steps:
            logging.info(f"\n=== STEP {step} | STATE: {self.current_state.name} ===")

            # 1. OBSERVE: Συλλογή δεδομένων από το περιβάλλον (R2)
            # Τώρα η observe() επιστρέφει πραγματικά δεδομένα από το tools.py
            observations = self.observe()
            
            # 2. THINK: Λήψη απόφασης από το πραγματικό LLM (R3)
            # Η think() πλέον καλεί το LLMEngine και το Qwen 2.5
            decision = self.think(observations)
            
            # 3. SLIDING WINDOW: Ενημέρωση ιστορικού (PDF Σελ. 7)
            # ΑΛΛΑΓΗ: Αποθηκεύουμε την απόφαση σε μορφή που καταλαβαίνει το LLM (role-based)
            self.history.append({
                "role": "assistant", 
                "content": json.dumps(decision)
            })
            
            # Διατήρηση μόνο των τελευταίων N βημάτων (Sliding Window)
            if len(self.history) > self.max_history:
                self.history.pop(0)

            # 4. ACT: Python Execution
            # Η act() τώρα καλεί τα πραγματικά εργαλεία και αλλάζει το State
            self.act(decision)
            
            step += 1
            time.sleep(1) # Παύση για συγχρονισμό και ανάγνωση των logs

        logging.info(f"--- AGENT EXECUTION TERMINATED at Step {step} ---")

# 4. ENTRY POINT
if __name__ == "__main__":
    # Δημιουργία και εκκίνηση του πράκτορα
    agent = EnergyGridAgent()
    agent.run()