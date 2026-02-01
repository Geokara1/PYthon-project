import os
from datetime import datetime

class AgentLogger:
    def __init__(self):
        self.log_file = None

    def setup(self, scenario_id):
        
        # Create a new file "logs"

        if not os.path.exists("logs"):
            os.makedirs("logs")

        # File timestamps to not erase previus inputs
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"logs/scenario_{scenario_id}_{timestamp}.txt"
        
        self.log_file = open(filename, "w", encoding="utf-8")
        print(f"\n LOGGING STARTED: Saving to {filename}\n")

    def log(self, tag, message):
        
        #Print and write the results on the screen and file respectively

        # Μορφή: [STATE] Message...
        formatted_message = f"[{tag}] {message}"
        

        print(formatted_message)
        

        if self.log_file:
            self.log_file.write(formatted_message + "\n")
            self.log_file.flush() # Εξασφαλίζει ότι γράφτηκε αμέσως

    def close(self):

        if self.log_file:
            self.log_file.close()
            print("\n LOGGING FINISHED.")

logger = AgentLogger()