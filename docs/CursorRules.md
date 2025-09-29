# Cursor Rules - Modern Coding Standards Enforcement System

## Overview

This project includes a comprehensive **AI agent guidance system** using Cursor's `.mdc` rules format that **enforces professional, modern coding standards** across all languages. The rules are organized in a nested architecture that automatically provides context-aware expertise while ensuring code quality, security, and maintainability.

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

## 🛡️ Professional Coding Standards Enforcement

### Mandatory JavaScript/Node.js Standards
- **✅ ALWAYS use const/let** - NEVER use var
- **✅ ALWAYS use async/await** - NEVER use .then().catch() chains  
- **✅ ALWAYS validate inputs** - Check types, ranges, and required fields
- **✅ ALWAYS use template literals** - `${variable}` instead of concatenation
- **✅ ALWAYS use arrow functions** - For callbacks and short functions
- **✅ ALWAYS use destructuring** - Extract properties cleanly

### Mandatory Python Standards  
- **✅ ALWAYS use type hints** - All parameters and return values
- **✅ ALWAYS follow PEP 8** - Naming, spacing, line length (88 chars)
- **✅ ALWAYS use dataclasses** - For structured data
- **✅ ALWAYS use descriptive docstrings** - Google/NumPy style
- **✅ ALWAYS use logging** - Never use print() for debugging
- **✅ ALWAYS validate data** - Input validation and error handling

### Mandatory PHP Standards
- **✅ ALWAYS use strict types** - declare(strict_types=1)
- **✅ ALWAYS follow PSR-12** - Coding standards and formatting
- **✅ ALWAYS use proper DocBlocks** - @param, @return, @throws
- **✅ ALWAYS validate inputs** - Type checking and sanitization
- **✅ ALWAYS use final classes** - Unless inheritance is intended
- **✅ ALWAYS handle exceptions** - Try/catch with meaningful messages

### Mandatory Docker/DevOps Standards
- **✅ ALWAYS use specific image tags** - NEVER use 'latest'
- **✅ ALWAYS run as non-root** - Security principle of least privilege
- **✅ ALWAYS use multi-stage builds** - Smaller, more secure images
- **✅ ALWAYS scan for vulnerabilities** - Security-first approach
- **✅ ALWAYS set resource limits** - Memory and CPU constraints
- **✅ ALWAYS implement health checks** - Container monitoring

## 🎯 Professional-Grade Code Generation

This cursor rules system transforms any AI coding agent into a **professional software engineer** who:

✅ **Enforces modern standards** - ES6+, PEP 8, PSR-12, Docker security best practices  
✅ **Writes type-safe code** - TypeScript-ready JS, Python type hints, PHP strict types  
✅ **Implements security first** - Input validation, error handling, least privilege  
✅ **Optimizes performance** - Async patterns, caching, resource optimization  
✅ **Ensures maintainability** - Clean architecture, comprehensive documentation  
✅ **Follows industry standards** - SOLID principles, design patterns, best practices

### Code Quality Guarantees
- **🔒 Security**: All code includes proper input validation and error handling
- **⚡ Performance**: Async/await patterns, optimized database queries, caching strategies  
- **🧪 Testability**: Modular design, dependency injection, clear interfaces
- **📚 Documentation**: Comprehensive docstrings, type hints, inline comments
- **🔧 Maintainability**: SOLID principles, clean architecture, consistent naming  

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

## 🚀 Enterprise-Grade Standards
The cursor rules system enforces **enterprise-grade coding standards** that ensure all generated code is:

- **Production-ready** with proper error handling and logging
- **Security-hardened** with input validation and principle of least privilege  
- **Performance-optimized** with async patterns and resource management
- **Maintainable** with clean architecture and comprehensive documentation
- **Industry-compliant** following PEP 8, PSR-12, ES6+, and Docker best practices

### Quality Metrics Enforced
- **100% Type Safety**: All parameters and returns are properly typed
- **Zero Security Vulnerabilities**: Input validation and sanitization required
- **Modern Language Features**: ES6+, Python 3.9+, PHP 8+, Docker security
- **Comprehensive Error Handling**: Try/catch blocks with meaningful messages
- **Professional Documentation**: Docstrings, type hints, and inline comments

This system guarantees that every AI-generated contribution meets the highest professional standards used in enterprise software development.
