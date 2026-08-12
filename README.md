# Enterprise RAG & Conversational Knowledge Assistant

This repository contains the step-by-step hands-on implementation of an **Enterprise RAG & Conversational Knowledge Assistant** built on AWS.

## 🏗 Project Architecture Overview

```text
                         USER
                           |
                           v
                    Frontend / Client
                           |
                           v
                     API Gateway
                           |
                           v
                        Lambda
                           |
                           v
                    LangGraph Agent
                           |
             +-------------+-------------+
             |             |             |
             v             v             v
         Retriever       Tools          LLM
             |             |              |
             v             v              v
        Vector Store    APIs/DBs       Amazon Bedrock
             |
             v
        S3 Documents
```

## 📁 Repository Structure

* `docs/` - Architecture diagrams, design decisions, phase checkpoints & notes.
* `src/` - Backend application code (Lambda handlers, LangGraph agents, RAG pipeline).
* `infrastructure/` - Infrastructure as Code (SAM / CloudFormation / CDK).
* `tests/` - Unit tests, integration tests & LLM evaluations.

## 🚀 Progress Tracker

- [x] Phase 0: Cloud Fundamentals & GenAI Context
- [x] Phase 1: AWS Account & Security Basics (IAM)
- [x] Phase 2: S3 Document Storage
- [x] Phase 3: Lambda Functions
- [x] Phase 4: API Gateway Integration
- [ ] Phase 5: CloudWatch Observability
- [ ] Phase 6: Amazon Bedrock Foundation Models
- [ ] Phase 7: First GenAI Endpoint
- [ ] Phase 8: RAG Architecture
- [ ] Phase 9: Bedrock Knowledge Bases & Vector Store
- [ ] Phase 10: Conversational Memory
- [ ] Phase 11: DynamoDB State Storage
- [ ] Phase 12: Bedrock Guardrails
- [ ] Phase 13: LangChain & LangGraph Integration
- [ ] Phase 14: Agent Tools & Function Calling
- [ ] Phase 15: Asynchronous Ingestion with SQS
- [ ] Phase 16: EventBridge Event Processing
- [ ] Phase 17: Step Functions Workflow Orchestration
- [ ] Phase 18: VPC & Private Networking
- [ ] Phase 19: Enterprise Security & Secrets Manager
- [ ] Phase 20: Comprehensive Observability
- [ ] Phase 21: LLM Evaluation Framework
- [ ] Phase 22: Cost Optimization & FinOps
- [ ] Phase 23: Infrastructure as Code (IaC)
- [ ] Phase 24: Production Deployment
- [ ] Phase 25: Failure Engineering & Resilience
- [ ] Phase 26: Final Enterprise Architecture & Interview Prep
