# Unit 4: Compute Infrastructure - Functional Design Plan

## Overview

This plan outlines the functional design steps for Unit 4: Compute Infrastructure. This unit deploys the zero2prod web application as a containerized ECS Fargate service with Application Load Balancer, auto-scaling, and integration with Units 1-3.

## Unit Context

**Purpose**: Deploy zero2prod web application on ECS Fargate with ALB, auto-scaling, and observability

**Dependencies**:
- Unit 1: Network Infrastructure (VPC, subnets, security groups)
- Unit 2: Database Infrastructure (Aurora PostgreSQL, secrets)
- Unit 3: Cache Infrastructure (ElastiCache Serverless, secrets)

**Scope**:
- Application Load Balancer (ALB) with HTTPS/HTTP listeners
- ECS Fargate cluster and service
- ECS task definition with container configuration
- ECR repository for Docker images
- IAM roles (task execution, task role)
- Auto-scaling (CPU-based, 2-10 tasks)
- CloudWatch logging
- Secrets Manager integration

## Functional Design Plan

### Phase 1: Analyze Unit Requirements

- [x] Review unit definition from unit-of-work.md
- [x] Identify functional components (ALB, ECS, ECR, IAM)
- [x] Understand dependencies (NetworkStack, DatabaseStack, CacheStack)
- [x] Review existing application code structure

### Phase 2: Generate Context Questions

- [x] Create questions.md with embedded [Answer]: tags
- [x] Focus on ALB configuration, ECS task sizing, auto-scaling parameters, IAM permissions
- [x] Wait for user to complete all [Answer]: tags
- [x] Analyze responses for ambiguities
- [x] Create clarification-questions.md for 3 ambiguities
- [x] Receive clarifications from user

### Phase 3: Business Logic Modeling

- [x] Define ALB request routing logic (HTTP → HTTPS redirect, target group)
- [x] Define ECS task lifecycle (startup, health checks, shutdown)
- [x] Define auto-scaling trigger logic (CPU threshold, scale-out/scale-in)
- [x] Define secrets loading sequence (startup dependencies)
- [x] Define health check validation logic

### Phase 4: Domain Entities

- [x] Define ECS task configuration entity (CPU, memory, environment variables)
- [x] Define ALB configuration entity (listeners, target groups, health checks)
- [x] Define auto-scaling configuration entity (min, max, target CPU)
- [x] Define IAM policy entity (task execution permissions, task permissions)

### Phase 5: Business Rules

- [x] Define task resource constraints (1 vCPU, 2 GB RAM)
- [x] Define auto-scaling rules (target CPU 70%, min 2, max 10)
- [x] Define health check rules (endpoint, interval, timeout, thresholds)
- [x] Define deployment rules (rolling update, health check grace period)
- [x] Define IAM least privilege rules (minimal permissions)

### Phase 6: Create Artifacts

- [x] Create business-logic-model.md (ALB routing, ECS lifecycle, auto-scaling)
- [x] Create domain-entities.md (task config, ALB config, IAM policies)
- [x] Create business-rules.md (resource constraints, scaling rules, health checks)
- [x] Create user-decision-log.md (document user choices)

### Phase 7: Validation

- [x] Verify all artifacts reference user decisions
- [x] Verify business rules are complete and unambiguous (35 rules defined)
- [x] Verify domain entities capture all configuration (11 entities)
- [x] Update plan checkboxes

---

## Status

**Current Phase**: Phase 7 - COMPLETE

**Artifacts Generated**:
1. ✅ `questions.md` - 10 questions with user answers
2. ✅ `clarification-questions.md` - 3 clarifications resolved
3. ✅ `business-logic-model.md` - 5 business processes documented
4. ✅ `domain-entities.md` - 11 entities defined
5. ✅ `business-rules.md` - 35 rules (13 CRITICAL, 15 HIGH, 7 MEDIUM)
6. ✅ `user-decision-log.md` - 13 decisions with cost/compliance analysis
