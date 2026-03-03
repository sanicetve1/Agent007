# Agentic Math CLI

Minimal agentic setup that routes natural language math instructions to simple tools (add, subtract, multiply, divide) via an LLM, and prints a structured execution trace plus the final result in the CLI.

## Setup

1. Create and activate a virtual environment.
2. Install dependencies:

```bash
pip install -e .
```

3. Copy `.env.example` to `.env` and set:

```bash
OPENAI_API_KEY=your_key_here
OPENAI_MODEL=gpt-4.1-mini
```

Optional: `ENABLE_MEMORY=true` (REPL keeps context), `ENABLE_GUARDS=true`, `MAX_MEMORY_MESSAGES=50`, `MAX_STEPS=4`.

## Usage

Run a single instruction:

```bash
python -m agentic_app.app "add two numbers: 2 and 3"
```

Or start an interactive session:

```bash
python -m agentic_app.app
```

