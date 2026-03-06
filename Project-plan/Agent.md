1. Agent Objective
The Loan Underwriting Agent evaluates loan applicants by orchestrating risk analysis tools.
It must:
1.	Understand the user request
2.	Decide which analysis tool to run
3.	Execute tools
4.	Reason on tool outputs
5.	Produce a final underwriting recommendation
The agent follows the ReAct (Reason → Act → Observe) pattern.

Agent Execution Model
The agent must follow a Node + Edge Graph Model.
Nodes represent execution stages.
Edges represent decision flow.

4. Agent Graph
User Request
      │
      ▼
Intent Node
      │
      ▼
Planning Node
      │
      ▼
Router Node
      │
 ┌────┼───────┐
 ▼    ▼       ▼
Credit Risk   Cashflow   Collateral
Tool Node     Tool Node  Tool Node
      │
      ▼
Observation Node
      │
      ▼
Reasoning Node
      │
      ▼
Decision Node
      │
      ▼
Final Response

Node Responsibilities
Intent Node
Purpose:
Understand the user's request.


Planning Node
The planning node determines:
Which tools are required.
Example reasoning:
To assess loan risk I need:

- credit score
- cashflow analysis
- collateral evaluation


Tool Nodes
The agent can call the  tools registered in the tools registry 

Observation Node
Collects tool outputs and updates agent context.


Reasoning Node
The LLM analyzes collected data.

Decision Node
Final underwriting recommendation.

Agent Context Model
The agent must maintain a shared context object.

Retry Mechanism
Each tool execution must support retries.

Guardrails
Agent must follow strict guardrails.
Allowed actions
The agent may only call: the tools registered in the tools registry 

Forbidden actions
The agent must NOT:
•	generate SQL queries
•	modify database
•	hallucinate financial data

Tool Usage Policy
Tools must be used only when necessary.
Example:
If user asks general question
Do not call tools


Agent must emit execution trace.
Example trace:
Step 1 Intent detected
Step 2 Plan created
Step 3 Tool calculate_credit_risk executed
Step 4 Tool analyze_cashflow executed
Step 5 Tool assess_collateral executed
Step 6 Final decision generated


 Extensibility Rules
Future tools may be added without modifying the core loop.
Examples:
fraud_check
employment_verification
kyc_validation
market_risk_analysis
The router must dynamically discover tools.

Implementation must use OpenAI GPT Agent SDK primitives.
Required components:
Agent
Tool
Runner
Router
Context
Agent must:
use tools through tool schema
maintain context state
execute reasoning loop


ReAct Loop Definition
The agent must follow this loop.
while not finished:

   think
   decide tool
   execute tool
   observe result
   update context
Stop condition:
decision generated

Logging Requirements
Logs must capture:
tool calls
tool outputs
reasoning steps
final decision
execution time

. Security Rules
Never expose:
raw transaction data
customer identifiers
full credit history
Agent outputs only aggregated insights.



