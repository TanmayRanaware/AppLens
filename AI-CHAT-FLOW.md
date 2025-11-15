# AI Chat Flow: How Natural Language is Processed

## Overview
The AI chat converts natural language queries into database queries and graph visualizations using CrewAI agents powered by GPT-4.

## Flow Diagram

```
User Input (Natural Language)
    ↓
Frontend: ChatDock.tsx
    ↓ (HTTP POST)
Backend Routes: /chat/error-analyzer, /chat/what-if, /nlq
    ↓
CrewAI Agents (ErrorAgent, WhatIfAgent, NLQAgent)
    ↓
LLM Processing (GPT-4 via langchain-openai)
    ↓
Database Queries (PostgreSQL)
    ↓
Response (JSON with results + graph hints)
    ↓
Frontend: Highlights nodes/links on graph
```

## 1. Frontend: ChatDock Component

**File:** `frontend/components/ChatDock.tsx`

### How it works:
1. **User types a message** in the input field
2. **Tool mode detection:**
   - `error-analyzer`: Detects keywords like "error", "log"
   - `what-if`: Detects keywords like "what if", "impact", "change"
   - `nlq` (default): All other queries

3. **Sends HTTP POST request:**
   ```typescript
   // Error Analyzer
   POST /chat/error-analyzer
   { log_text: "user message" }
   
   // What-If Simulator
   POST /chat/what-if
   { repo: "repo-name", diff: "user message" }
   
   // Natural Language Query
   POST /nlq
   { question: "user message" }
   ```

4. **Receives response** and highlights nodes/links on the graph

## 2. Backend Routes

### Error Analyzer Route
**File:** `backend/app/routes/chat.py`

```python
POST /chat/error-analyzer
→ Creates ErrorAgent instance
→ Calls agent.analyze(log_text)
→ Returns: { affected_nodes, affected_edges, reasoning }
```

### What-If Simulator Route
**File:** `backend/app/routes/chat.py`

```python
POST /chat/what-if
→ Creates WhatIfAgent instance
→ Calls agent.simulate(repo, diff, pr_url)
→ Returns: { predicted_impacted_nodes, reasoning }
```

### Natural Language Query Route
**File:** `backend/app/routes/nlq.py`

```python
POST /nlq
→ Creates NLQAgent instance
→ Calls agent.query(question)
→ Returns: { results, graph_hints }
```

## 3. CrewAI Agents Processing

### Error Agent (`backend/app/agents/error_agent.py`)

**How it processes natural language:**
1. **Regex extraction** from log text:
   - Service names: `([a-z]+(?:-[a-z]+)+-service)`
   - URLs: `https?://[^\s]+|/[a-z0-9/_-]+`
   - Kafka topics: `topic[:\s]+([a-z0-9._-]+)`

2. **Database queries:**
   - Searches `Service` table by name (case-insensitive)
   - Searches `Interaction` table by URL or Kafka topic
   - Finds affected services and edges

3. **Returns:**
   - `affected_nodes`: List of service IDs
   - `affected_edges`: List of source/target pairs
   - `reasoning`: Summary of findings

**Data sources:**
- `Service` table (services in your microservices)
- `Interaction` table (HTTP calls, Kafka messages between services)

### NLQ Agent (`backend/app/agents/nlq_agent.py`)

**How it processes natural language:**
1. **Pattern matching** for common queries:
   - "services that call X" → `_query_service_calls()`
   - "kafka topic" → `_query_kafka_topics()`
   - "highest in-degree" → `_query_top_services_by_degree()`
   - "fan-out" or "hops" → `_query_fanout()`
   - Generic → `_generic_query()` (uses LLM)

2. **Regex extraction:**
   - Service names: `call[s]?\s+([a-z-]+)`
   - Topic names: `topic[:\s]+([a-z0-9._-]+)`
   - Hop counts: `(\d+)\s+hop[s]?`

3. **Database queries:**
   - Joins `Service` and `Interaction` tables
   - Uses SQLAlchemy ORM for safe queries
   - BFS traversal for fan-out queries

4. **Returns:**
   - `results`: Query results (services, topics, etc.)
   - `graph_hints`: Services to highlight on graph

**Data sources:**
- `Service` table
- `Interaction` table
- `Repository` table

### What-If Agent (`backend/app/agents/whatif_agent.py`)

**How it processes natural language:**
1. **Extracts change information:**
   - PR URL → Extracts repo and PR number
   - File path → Extracts service name
   - Diff text → Analyzes changes

2. **Service detection:**
   - Extracts service name from file path
   - Searches database for matching services

3. **Blast radius calculation:**
   - Finds 1-hop neighbors (direct dependencies)
   - Finds 2-hop neighbors (indirect dependencies)
   - Uses BFS traversal

4. **Returns:**
   - `predicted_impacted_nodes`: Services that will be affected
   - `predicted_impacted_edges`: Edges that will be affected
   - `reasoning`: Impact analysis

**Data sources:**
- `Service` table
- `Interaction` table
- GitHub API (via MCP client) for PR/file information

## 4. LLM Usage (GPT-4)

**All agents use:**
```python
ChatOpenAI(
    model="gpt-4",
    temperature=0.1,  # Low temperature for consistent results
    openai_api_key=settings.openai_api_key
)
```

**CrewAI Agent setup:**
```python
Agent(
    role="Agent Role",
    goal="Agent goal",
    backstory="Agent backstory",
    verbose=True,
    llm=self.llm  # GPT-4 instance
)
```

**Note:** Currently, most processing uses regex and pattern matching. The LLM is set up but not heavily used yet. The `_generic_query()` method in NLQAgent is a placeholder for future LLM-based query generation.

## 5. Database Schema

### Tables Used:

1. **`services`**
   - `id`, `name`, `repo_id`, `language`
   - Stores all microservices

2. **`interactions`**
   - `source_service_id`, `target_service_id`
   - `edge_type` (HTTP, Kafka)
   - `http_method`, `http_url`, `kafka_topic`
   - Stores relationships between services

3. **`repositories`**
   - `id`, `full_name`, `html_url`
   - Stores GitHub repository information

## 6. Example Flow

### Example 1: "Show services that call auth-service"

1. User types: "Show services that call auth-service"
2. Frontend sends: `POST /nlq { question: "Show services that call auth-service" }`
3. NLQAgent detects pattern: "services that call"
4. Extracts service name: "auth-service"
5. Database query:
   ```sql
   SELECT Service.* FROM Service
   JOIN Interaction ON Service.id = Interaction.source_service_id
   WHERE Interaction.target_service_id = (SELECT id FROM Service WHERE name LIKE '%auth-service%')
   ```
6. Returns: List of services that call auth-service
7. Frontend highlights those services on the graph

### Example 2: Error log analysis

1. User pastes error log with service names and URLs
2. Frontend sends: `POST /chat/error-analyzer { log_text: "..." }`
3. ErrorAgent extracts:
   - Service names via regex
   - URLs via regex
   - Kafka topics via regex
4. Database queries find matching services and interactions
5. Returns: Affected nodes and edges
6. Frontend highlights them on the graph

## 7. Current Limitations

1. **Pattern-based processing:** Most queries use regex/pattern matching, not full LLM understanding
2. **Generic queries:** `_generic_query()` is not fully implemented
3. **SQL generation:** LLM-based SQL generation is not yet implemented (for safety)
4. **Error handling:** Basic error handling, could be improved

## 8. Future Improvements

1. **Full LLM integration:** Use GPT-4 to understand complex queries
2. **Safe SQL generation:** Use LLM to generate SQL with validation
3. **Context awareness:** Remember previous queries in conversation
4. **Better extraction:** Use LLM for better entity extraction from logs
5. **Multi-hop analysis:** More sophisticated graph traversal algorithms

## Summary

- **Natural Language → Pattern Matching/Regex → Database Queries → Results**
- **Data comes from:** PostgreSQL database (services, interactions, repositories)
- **LLM used:** GPT-4 via CrewAI (currently limited, mostly for agent setup)
- **Processing:** Mostly regex-based extraction + database queries
- **Output:** JSON with results + graph highlighting hints

