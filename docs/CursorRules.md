# Cursor Rules - AI Agent Guidance System

## Overview

This project includes a comprehensive **AI agent guidance system** using Cursor's `.mdc` rules format. The rules are organized in a nested architecture that automatically provides context-aware expertise to AI coding agents.

## 📁 Rules Architecture

### Nested Structure
```
project/
├── .cursor/rules/                    # Project-wide rules
│   ├── news-analysis-system.mdc     # Always apply - system overview
│   ├── docker-operations.mdc        # Auto-attach on docker files
│   └── testing-debugging.mdc        # Agent-requested for debugging
├── src/.cursor/rules/                # Node.js specific rules
│   ├── nodejs-development.mdc       # Auto-attach on src/**/*.js
│   └── database-operations.mdc      # Auto-attach on database files
├── hug/.cursor/rules/                # Python specific rules
│   └── python-development.mdc       # Auto-attach on hug/**/*.py
└── rss-bridge/.cursor/rules/         # RSS-bridge specific rules
    └── rss-content-development.mdc  # Auto-attach on rss-bridge/**/*.php
```

## 🎯 Rule Types & Triggers

### **Always Active**
- **[news-analysis-system.mdc](.cursor/rules/news-analysis-system.mdc)** - Core system architecture and navigation

### **Auto-Attach Rules**
| File Pattern | Activated Rules | Purpose |
|--------------|----------------|---------|
| `src/**/*.js` | nodejs-development + database-operations | Node.js/Express + MongoDB |
| `hug/**/*.py` | python-development | Python/Hug API + ML |
| `rss-bridge/**/*.php` | rss-content-development | RSS bridge creation |
| `**/docker-compose.yml` | docker-operations | Container management |
| `**/*database*` | database-operations | MongoDB operations |

### **Agent-Requested**
- **[testing-debugging.mdc](.cursor/rules/testing-debugging.mdc)** - AI decides when debugging guidance is needed

## 🚀 AI Agent Benefits

### Context-Aware Activation
```
Editing src/index.js         → Node.js + Database rules load automatically
Working with hug/hug.py      → Python development rules activate
Modifying docker-compose.yml → Docker operations rules engage
Creating new PHP bridge      → RSS-bridge development patterns available
```

### Performance Optimized
- **Targeted loading**: Only relevant rules activate for specific scenarios
- **Reduced context**: No irrelevant information cluttering AI context
- **Expert guidance**: Right patterns at exactly the right time
- **Automatic activation**: No manual rule selection needed

## 📋 Rules Content Summary

### **Project-Wide Rules**

#### **news-analysis-system.mdc** (Always Apply)
- System overview and architecture
- Component relationships and data flow
- Quick navigation to key files
- Critical safety guidelines

#### **docker-operations.mdc** (Auto-Attach)
- Service architecture and dependencies
- Volume management and networking
- Development workflows and debugging
- Container orchestration patterns

#### **testing-debugging.mdc** (Agent-Requested)
- Service health checks and connectivity tests
- Performance monitoring and optimization
- Error patterns and troubleshooting guides
- Testing workflows and validation procedures

### **Component-Specific Rules**

#### **Node.js Development** (`src/.cursor/rules/`)
- **nodejs-development.mdc**: Express patterns, route organization, RSS processing
- **database-operations.mdc**: MongoDB operations, schema patterns, aggregation pipelines

#### **Python Development** (`hug/.cursor/rules/`)
- **python-development.mdc**: Hug framework patterns, ML dataset generation, pandas integration

#### **RSS-Bridge Development** (`rss-bridge/.cursor/rules/`)
- **rss-content-development.mdc**: Bridge creation templates, CSS selectors, content extraction

## 🛡️ Safety & Quality Features

### Critical Guidelines
- Database volume protection (`E:\NewsDatabase` - NEVER DELETE)
- Upsert patterns for preventing duplicates
- Proper error handling and validation
- Performance optimization strategies

### Pattern Enforcement
- Consistent code patterns across technology stacks
- Established conventions for each component
- Best practices embedded in context
- Quality assurance through proven workflows

## 🎯 Expert-Level Contributions

This cursor rules system transforms any AI coding agent into an **expert contributor** who:

✅ **Navigates expertly** using automatic file pattern recognition  
✅ **Applies correct patterns** with context-aware rule activation  
✅ **Works efficiently** with focused, relevant information  
✅ **Maintains safety** with embedded critical guidelines  
✅ **Scales expertise** across multiple technology stacks  

## 🔧 Usage for Developers

### For AI Agents
The rules activate automatically based on file patterns and development context. No manual intervention required.

### For Human Developers
- Reference the rules for understanding project patterns
- Use as guidance for consistent development practices
- Leverage for onboarding new team members
- Reference for troubleshooting and debugging

## 📚 Related Documentation
- [Project Overview](ProjectOverview.md) - Complete system architecture
- [Main Application](MainApplication.md) - Node.js component details
- [Docker Setup](DockerSetup.md) - Container configuration
- [Getting Started](../GETTING_STARTED.md) - Quick start guide

## 🚀 Production Ready
The cursor rules system is production-ready and provides world-class AI agent guidance for the News Readability Analysis System. It ensures consistent, high-quality contributions while maintaining optimal performance and safety standards.
