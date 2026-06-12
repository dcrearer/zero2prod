# Unit 4: Compute Infrastructure - Clarification Questions

## Purpose

A few responses need clarification before proceeding with functional design artifact generation.

---

## Clarification 1: Health Check Validation Scope

**Original Question 4 Follow-up**: Should the health check endpoint validate both database and cache connectivity, or just database?

**Your Answer**: *(empty)*

**Clarification Needed**: The `/health_check` endpoint can validate:
- **Option A**: Database connectivity only (simpler, faster health checks)
- **Option B**: Both database and cache connectivity (comprehensive, but slower)
- **Option C**: Neither - just return 200 OK (fastest, but doesn't validate dependencies)

**Recommendation**: Option A (database only) is common practice. Cache failures are typically non-fatal (sessions degrade gracefully), while database failures prevent core functionality.

[Answer]: A

---

## Clarification 2: Container Image Strategy

**Original Question 6 Main Answer**: *(empty - appears to be a formatting issue)*

**Your Follow-up Answer**: B (GitHub Actions)

**Clarification Needed**: I see you selected B (GitHub Actions) in the follow-up field. Can you confirm:
- **Option B**: GitHub Actions CI/CD pipeline (build on push to main, push to ECR)

Is this correct? If so, I'll proceed with GitHub Actions as the container image build strategy.

[Answer]: Yes

---

## Clarification 3: Observability Environment Variables

**Original Question 7 Follow-up**: Should we add environment variables for feature flags or observability integrations (e.g., AWS X-Ray)?

**Your Answer**: *(empty)*

**Clarification Needed**: Should the ECS task definition include environment variables for:
- **AWS X-Ray** tracing (e.g., `AWS_XRAY_DAEMON_ADDRESS`, `AWS_XRAY_TRACING_NAME`)
- **Feature flags** (e.g., `FEATURE_NEW_UI=false`)
- **Other observability** (e.g., CloudWatch Embedded Metrics Format)

**Options**:
- **Option A**: Add AWS X-Ray environment variables (enable distributed tracing)
- **Option B**: Add feature flag support (dynamic feature toggling)
- **Option C**: Add both X-Ray and feature flags
- **Option D**: Skip for now, add in Unit 7 (Observability Infrastructure)

**Recommendation**: Option D (defer to Unit 7) keeps Unit 4 focused on core compute infrastructure. Observability can be added in Unit 7 without redeploying.

[Answer]: A

---

## Next Steps

Once you provide these clarifications, I will:
1. Generate functional design artifacts:
   - `business-logic-model.md` (ALB routing, ECS lifecycle, auto-scaling logic)
   - `domain-entities.md` (task config, ALB config, IAM policies)
   - `business-rules.md` (resource constraints, scaling rules, health checks)
   - `user-decision-log.md` (document all decisions with rationale)
2. Update the functional design plan
3. Present completion message for your review
