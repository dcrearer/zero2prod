# Zero2Prod Architecture

## Project Overview
A newsletter service built with Rust, featuring subscription management and health monitoring.

## Module Dependencies

```
┌─────────────────────────────────────────────────────────────────┐
│                        zero2prod Project                        │
└─────────────────────────────────────────────────────────────────┘

┌─────────────┐    ┌─────────────────┐    ┌──────────────────┐
│    main     │───▶│ configuration   │    │    telemetry     │
│             │    │                 │    │                  │
│ - tokio     │    │ Settings        │    │ - tracing setup  │
│ - PgPool    │    │ DatabaseSettings│    │ - log formatting │
└─────────────┘    └─────────────────┘    └──────────────────┘
       │                     │                       │
       ▼                     │                       │
┌─────────────┐              │                       │
│   startup   │◀─────────────┘                       │
│             │                                      │
│ - HttpServer│                                      │
│ - App setup │                                      │
│ - routes    │                                      │
└─────────────┘                                      │
       │                                             │
       ▼                                             │
┌─────────────────────┐                              │
│   routes/           │◀─────────────────────────────┘
│                     │
│ mod.rs              │
│ ├─health_check.rs   │
│ └─subscriptions.rs  │
└─────────────────────┘
```

## Request Flow

1. **main** → Load configuration → Initialize telemetry → Connect to database
2. **startup** → Create HTTP server → Register routes
3. **routes** → Handle requests → Database operations → Response

## Key Patterns

- **Modular design**: Clear separation of concerns
- **Configuration-driven**: YAML config with type-safe deserialization  
- **Structured logging**: Tracing with JSON output
- **Database abstraction**: sqlx for compile-time verified queries
- **Security**: Secret types for sensitive data
- **Async throughout**: tokio runtime with async handlers

---
*Last updated: 2025-12-16*
