# Autonomous Energy Grid Balancer Agent

This project implements an LLM-based Autonomous Agent designed to manage and balance an electrical power grid. The agent uses a Hybrid Architecture, combining a deterministic Finite State Machine (FSM) with the probabilistic reasoning of a Large Language Model (LLM).

## Project Overview

- **Domain:** Energy Grid Balancer
- **Objective:** Match energy supply with demand while minimizing costs and preventing blackouts.
- **Model:** Qwen/Qwen2.5-Coder-32B-Instruct (via Hugging Face API)
- **Framework:** Python with `smolagents` and `huggingface_hub`.

## Team Members

1. **Member 1 (System Architect & FSM Engineer):** Georgios Karagkounis
2. **Member 2 (Environment & Tools Developer):** Nikos Zormpas
3. **Member 3 (Cognitive Policy Engineer):** Athanasios Davaris
4. **Member 4 (Integration & QA Specialist):** Giannis Spanoudakis

## Architecture

The agent operates on an Observe-Think-Act loop across the following states:

- `INITIALIZING`: System setup.
- `DEMAND_FORECASTING`: Predicting load for the next hour.
- `CAPACITY_ANALYSIS`: Checking Solar, Wind, and Gas availability.
- `DISPATCH_PLANNING`: LLM-driven strategy (Renewables > Gas > Load Shedding).
- `EXECUTION`: Applying the plan to the grid.
- `STABILITY_CHECK`: Evaluating grid metrics (Frequency & Blackout Risk).
- `ADJUSTMENT`: Replanning loop in case of instability.
- `TERMINATED`: Successful cycle completion.

## Installation

1. **Clone the repository:**

```bash
git clone https://github.com/Geokara1/PYthon-project.git
cd PYthon-project
```

2. **Install dependencies:**

```bash
pip install -r requirements.txt
```

3. **Set up your Hugging Face Token:**

- Windows (PowerShell): `$env:HF_TOKEN="your_token_here"`
- Linux/Mac: `export HF_TOKEN="your_token_here"`
- Google Colab: Add HF_TOKEN to the "Secrets" (Key icon) and enable notebook access.

## How to Run

Run the main entry point:

```bash
python main.py
```

Upon execution, you will be prompted to select one of the 5 Test Scenarios:

1. Normal Operation
2. Night Crisis
3. Stormy Weather
4. Gas Depletion (Stress Test)
5. Peak Demand

## File Structure

- `main.py`: Entry point and scenario selector.
- `agent.py`: Core FSM logic and Agent class.
- `tools.py`: Mock environment and grid tools.
- `llm_engine.py`: Hugging Face API connectivity and JSON parsing.
- `prompts.py`: Dynamic system prompts for each state.
- `logger.py`: Execution trace logging system.
- `logs/`: Directory containing the 5 mandatory execution logs.

## Safety & Robustness

- **Constraint Enforcement:** The agent is restricted by a whitelist of actions per state.
- **Graceful Failure:** If a tool fails or the grid is unstable, the agent enters an `ADJUSTMENT` phase to rectify the plan.
- **Chain of Thought:** The LLM is forced to perform mathematical reasoning in a `thought` field before generating commands.
