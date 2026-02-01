import os
import sys
import tools
from agent import EnergyGridAgent
from logger import logger

def main():
  print("=================================================")
  print("   AUTONOMOUS ENERGY GRID AGENT - INITIALIZING   ")
  print("=================================================")

  # Token Check

  token = os.getenv("HF_TOKEN")
  if not token:
    print("   WARNING: HF_TOKEN not found in environment variables.")
    print("   The agent will try to find it in Colab Secrets.")
  else:
    print("  HF_TOKEN found in environment.")
  
  # Scenario Selection
  print("\n--- SCENARIO SELECTION ---")
  print("1. Normal Operation (Sunny, Noon)")
  print("2. Night Crisis (No Solar, Low Wind)")
  print("3. Stormy Weather (High Wind, No Solar)")
  print("4. Gas Depletion (Critical - Requires Load Shedding)")
  print("5. Peak Demand (Evening High Load)")

  try:
    choice = input("Select a scenario (1-5) [Default: 1]: ").strip()
    scenario_id = int(choice) if choice else 1
  except ValueError:
    print("Invalid input. Defaulting to Scenario 1.")
    scenario_id = 1
  
  print(f"\n Setting up Scenario {scenario_id}...")
  tools.set_scenario(scenario_id)
  logger.setup(scenario_id)

  # Print initial state for verification
  # print(f"   Current Hour: {tools.WORLD_STATE['current_hour']}:00")
  # print(f"   Weather: {tools.WORLD_STATE['weather_condition']}")
  # print(f"   Gas Reserves: {tools.WORLD_STATE['gas_reserve_mw']} MW")

  #print initial state
  logger.log("INIT", f"Current Hour: {tools.WORLD_STATE['current_hour']}:00")
  logger.log("INIT", f"Weather: {tools.WORLD_STATE['weather_condition']}")
  logger.log("INIT", f"Gas Reserves: {tools.WORLD_STATE['gas_reserve_mw']} MW")

  # Initialize and Run Agent
  print("\n Launching Agent...")
  try:
    bot = EnergyGridAgent(hf_token=token)
    bot.run()
  except KeyboardInterrupt:
    logger.log("SYSTEM", "Execution interrupted by user.")
  except Exception as e:
    logger.log("CRITICAL ERROR", str(e))
  finally:
    logger.close()

if __name__ == "__main__":
  main()