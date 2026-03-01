Goal:
Design a minimal agentic setup where:

The user gives a natural language instruction (e.g., “add two numbers”).

The agent autonomously identifies the correct tool (add, subtract, multiply, divide).

The agent executes the tool and returns the result.

==========================================================
Folder Structure
===========================================================
agentic_app/
│
├── app.py                     # Entry point (CLI or API)
Provides a simple CLI interface to send user input to the agent and print the final result.
│
├── agent/
│   ├── __init__.py
│   ├── agent.py               # Core agent loop
│   ├── prompt.py              # System / agent instructions
│   ├── state.py               # Agent state object

agent/__init__.py

Initializes the agent module and exposes the main Agent class for external imports.
Keeps the package clean and allows from agent import Agent usage.

agent/agent.py

Implements the core agent execution loop: receives user input, calls the LLM, selects tools, executes them, and returns results.
Handles tool routing, state updates, and termination logic in a single controlled flow.

agent/prompt.py

Defines the system prompt and tool instructions that guide the LLM’s reasoning and tool selection behavior.
Central place to modify agent personality, rules, output format, and tool-calling expectations.

agent/state.py

Defines the structured AgentState object used to track user input, selected tools, arguments, and execution results.
Ensures predictable data flow across reasoning steps and makes future expansion (memory, planning) easier.


├── tools/
│   ├── __init__.py
│   ├── base.py                # Tool interface / contract
│   ├── registry.py            # Tool registration & lookup
│   │

tools/__init__.py

Initializes the tools package and optionally exposes commonly used tools or the registry for simplified imports.
Keeps the tools module modular and scalable as new tool categories are added.

tools/base.py

Defines the abstract Tool interface that all tools must implement, including required attributes and the run() method.
Ensures consistency across tools so the agent can execute any tool in a standardized way.

tools/registry.py

Maintains a centralized registry of all available tools and provides lookup functions for retrieving tools by name.
Acts as the bridge between the LLM-selected tool name and the actual executable tool instance.


│   ├── math/
│   │   ├── __init__.py
│   │   ├── add.py
│   │   ├── subtract.py
│   │   ├── multiply.py
│   │   └── divide.py

tools/math/__init__.py

Initializes the math tools subpackage and groups all arithmetic-related tools under a single namespace.
Allows the registry to import math tools cleanly and keeps tool categories well organized.

tools/math/add.py

Implements the AddTool, responsible for adding two numeric inputs using the standard tool interface.
Exposes a clear name and description so the agent can select it for addition-related user queries.

tools/math/subtract.py

Implements the SubtractTool, which subtracts one numeric value from another.
Used by the agent when the user intent indicates a subtraction operation.

tools/math/multiply.py

Implements the MultiplyTool, responsible for multiplying two numeric inputs.
Designed to be invoked when the agent detects multiplication intent in the user request.

tools/math/divide.py

Implements the DivideTool, which divides one numeric value by another and handles division-by-zero safely.
Provides reliable arithmetic execution while keeping error handling localized to the tool.

│
├── llm/
│   ├── __init__.py
│   └── client.py              # LLM wrapper (OpenAI)

llm/__init__.py

Initializes the LLM module and exposes the main client interface used by the agent.
Allows the rest of the system to import the LLM wrapper without depending on implementation details.

llm/client.py - Implements the LLM interaction layer responsible for sending prompts and receiving structured responses (including tool calls).
Abstracts the underlying provider so the system can switch between mock, local, or production LLMs without changing agent logic.
│
├── memory/
│   ├── __init__.py
│   └── conversation.py        # Short-term memory (optional now)
memory/__init__.py

Initializes the memory package and exposes available memory components to the agent.
Keeps memory-related logic modular and separate from reasoning and tool execution.

memory/conversation.py

Implements short-term conversation memory that stores recent user inputs and agent responses.
Provides contextual history to the LLM to maintain coherent multi-turn interactions.

│
├── config/
│   └── settings.py            # Model, temperature, etc.

config/settings.py

Defines centralized configuration values such as model name, temperature, and runtime flags.
Ensures environment-specific changes (dev, test, prod) can be made without modifying core logic.

│
└── README.md

======================================

technical details 
====================
Use popular libraries
use latest python packages 


## Strategy

1. Write plan with success criteria for each phase to be checked off. Include project scaffolding, including .gitignore, and rigorous unit testing.
2. Execute the plan ensuring all criteria are met
3. Carry out extensive integration testing with Playwright or similar, fixing defects
4. Only complete when the MVP is finished and tested, with the server running and ready for the user
5.The agent must emit a step-by-step execution trace showing intent interpretation, tool selection, tool execution, and final output.
This trace must be explicit, structured, and visible in the CLI, without exposing raw LLM chain-of-thought.

## Coding standards

1. Use latest versions of libraries and idiomatic approaches as of today
2. Keep it simple - NEVER over-engineer, ALWAYS simplify, NO unnecessary defensive programming. No extra features - focus on simplicity.
3. Be concise. Keep README minimal. IMPORTANT: no emojis ever
4. use .env file for api keys and other configurable paths required for the app. 



this is a a test comment from codex
