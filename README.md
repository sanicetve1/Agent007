# Agentic Math CLI

Minimal agentic setup that routes natural language math instructions to simple tools (add, subtract, multiply, divide) via an LLM, and prints a structured execution trace plus the final result in the CLI.

## Setup

1. Create and activate a virtual environment.
2. Install dependencies:

```bash
pip install -e .
```

3. Configure environment variables:

```bash
OPENAI_API_KEY=your_key_here
OPENAI_MODEL=gpt-4.1-mini
OPENAI_TEMPERATURE=0.0
ENABLE_MEMORY=false
MEMORY_TURN_LIMIT=6
MEMORY_MAX_CHARS_PER_MESSAGE=1000
```

## Usage

Run a single instruction:

```bash
python -m agentic_app.app "add two numbers: 2 and 3"
```

Start an interactive session:

```bash
python -m agentic_app.app
```

## Memory behavior

- Memory is opt-in and controlled by `ENABLE_MEMORY`.
- When enabled, REPL mode keeps a stable session context for the lifetime of the process.
- Use `/reset` in REPL mode to clear conversation memory for the current session.
- Single-run CLI remains stateless by default.

## Testing

```bash
PYTHONPATH=. pytest -q
```
