# Builder stage
FROM public.ecr.aws/docker/library/rust:1.92.0-bookworm AS builder

WORKDIR /app
RUN apt update && apt install lld clang -y
COPY . .
ENV SQLX_OFFLINE true
RUN cargo build --release

# Runtime stage
FROM public.ecr.aws/docker/library/debian:bookworm-slim AS runtime

WORKDIR /app

# Create non-root user
RUN groupadd -r appuser && useradd -r -g appuser appuser

RUN apt-get update -y \
    && apt-get install -y --no-install-recommends openssl ca-certificates \
    && apt-get autoremove -y \
    && apt-get clean -y \
    && rm -rf /var/lib/apt/lists/*

COPY --from=builder /app/target/release/zero2prod zero2prod
COPY --from=builder /app/configuration configuration
RUN chown appuser:appuser zero2prod

USER appuser
EXPOSE 8000
ENV APP_ENVIRONMENT production
ENTRYPOINT ["./zero2prod"]