# AppLens - Project Group 8

> **Intelligent Microservice Debugging & Analysis**  
> Automatically understand, visualize, and debug complex microservice architectures using AI-powered graph analysis.

---

## 🔴 The Problem

Modern microservice architectures are incredibly complex and debugging them is painful:

- **Finding the source of an error** across dozens of services is like finding a needle in a haystack
- **Understanding downstream impacts** when something breaks requires tribal knowledge and manual investigation
- **Answering "what if I change this?"** means hours of manual code archaeology across multiple repositories
- **Service dependencies** are scattered across repos, configs, documentation, and team knowledge
- **Root cause analysis** often involves jumping between logs, code, and team members

When a production error occurs, teams waste hours or even days trying to:
1. Figure out which microservice actually caused the problem
2. Understand which other services are affected
3. Identify what changed recently that could have caused it
4. Assess the blast radius before attempting a fix

---

## ✅ What We're Solving

AppGraph AI creates an **intelligent graph memory of your entire microservice ecosystem** that AI agents can reason over. 

Instead of manual detective work, you get:

- **Instant service dependency mapping** from your GitHub repositories
- **AI-powered error analysis** that pinpoints the source microservice from error logs
- **Visual impact analysis** showing exactly which services are affected
- **Natural language Q&A** about your architecture and "what-if" scenarios
- **Context-aware debugging** that correlates errors with recent code changes

Think of it as giving your entire microservice architecture a brain that understands how everything connects and can explain what's happening when things go wrong.

---

## ✨ Features

### 🕸️ **Automatic Service Graph Construction**
- **Upload GitHub repo links** (single repos or entire organizations)
- **Automatic analysis** detects HTTP/gRPC calls, message queues, API contracts, and database dependencies
- **Unified dependency graph** built across all your microservices
- **Interactive visualization** showing how every service connects

### 🚨 **Intelligent Error Analysis**
- **Paste any error log or stack trace** into the chat
- **AI parses and understands** the error in the context of your service graph
- **Pinpoints the source microservice** with confidence reasoning
- **Highlights all affected services** (upstream and downstream impact)
- **Correlates with recent changes** to show what might have caused it

### 🎨 **Interactive Service Graph**
- **Real-time visualization** of your entire microservice architecture
- **Visual impact highlighting** when errors occur
- **Click to explore** endpoints, dependencies, and recent code changes
- **Filter and navigate** by service, protocol type, or recency

### 🤔 **Natural Language Q&A**

Ask anything about your architecture:
- *"Which services call the payment API?"*
- *"If I change the `/inventory/stock` endpoint, what will break?"*
- *"Show me all services that depend on the auth database"*
- *"What changed in checkout-service in the last week?"*
- *"What's the path from user-service to notification-service?"*

The AI understands your service graph and answers with precise information and visual highlights.

### 🔍 **Context-Aware Root Cause Analysis**

When you paste an error, you get:
- **Likely origin service** identified from error patterns
- **Impact cascade visualization** of all affected services
- **Recent code changes** that might be related
- **Evidence reasoning** explaining how the conclusion was reached
- **Suggested next steps** for investigation and remediation

### 📊 **What-If Analysis**
- Understand the impact before making changes
- See which services depend on specific endpoints or resources
- Identify circular dependencies and architectural issues
- Assess deployment risks across service boundaries

---

<div align="center">
  <p><strong>Built for developers who've debugged one too many microservice incidents</strong></p>
</div>
