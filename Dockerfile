# Builder stage
FROM public.ecr.aws/docker/library/rust:1.90.0 AS builder

WORKDIR /app
RUN apt update && apt install lld clang -y
COPY Cargo.toml Cargo.lock ./
COPY src src
COPY .sqlx .sqlx
COPY migrations migrations
COPY configuration configuration
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
COPY --from=builder /app/migrations migrations
RUN chown -R appuser:appuser /app

USER appuser
EXPOSE 8000
ENTRYPOINT ["./zero2prod"]