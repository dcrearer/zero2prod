# zero2prod

A Rust web application for email newsletter subscriptions with full AWS deployment infrastructure.

## Core Application

- Built with Actix-web framework
- PostgreSQL database with SQLx for type-safe queries
- AWS SES v2 for email sending
- Structured logging with tracing
- Configuration management via the config crate

## Key Features

- `/health_check` endpoint for health monitoring
- `/subscriptions` endpoint for newsletter signups
- Domain-driven design with validated types (subscriber email, name)
- Database migrations for schema management

## AWS Infrastructure (Terraform)

- EKS cluster deployment
- RDS PostgreSQL database
- ALB controller for ingress
- CI/CD pipeline with CodeBuild/CodePipeline
- Secrets management
- Modular terraform structure (networking, database, eks, cicd)

## Kubernetes Setup

- Kustomize-based deployments (dev/prod overlays)
- ConfigMaps for non-sensitive config
- Secrets for credentials
- Ingress configuration
- Docker containerization

## Configuration Approach

The app uses environment variables with the `APP__` prefix (e.g., `APP__DATABASE__HOST`) that map to nested config structures, integrating with Kubernetes ConfigMaps and Secrets.

---

The project follows the "Zero to Production in Rust" book structure, implementing production-ready patterns for a real-world web service.
