//! src/routes/subscriptions_confirm.rs
use actix_web::{HttpResponse, web};
use sqlx::PgPool;
use uuid::Uuid;

#[derive(serde::Deserialize)]
pub struct Parameters {
    subscription_token: String,
}

#[tracing::instrument(name = "Confirm a pending subscriber", skip(parameters, pool))]
pub async fn confirm(parameters: web::Query<Parameters>, pool: web::Data<PgPool>) -> HttpResponse {
    tracing::info!(
        "Attempting to confirm with token: {}",
        parameters.subscription_token
    );

    let id = match get_subscriber_id_from_token(&pool, &parameters.subscription_token).await {
        Ok(id) => {
            tracing::info!("Token lookup result: {:?}", id);
            id
        }
        Err(e) => {
            tracing::error!("Database error: {:?}", e);
            return HttpResponse::InternalServerError().finish();
        }
    };

    match id {
        None => {
            tracing::warn!("Token not found, returning 401");
            HttpResponse::Unauthorized().finish()
        }
        Some(subscriber_id) => {
            tracing::info!("Found subscriber_id: {}", subscriber_id);
            if confirm_subscriber(&pool, subscriber_id).await.is_err() {
                return HttpResponse::InternalServerError().finish();
            }
            HttpResponse::Ok().finish()
        }
    }
}

pub async fn get_subscriber_id_from_token(
    pool: &PgPool,
    subscription_token: &str,
) -> Result<Option<Uuid>, sqlx::Error> {
    let result = sqlx::query!(
        "SELECT subscriber_id FROM subscription_tokens WHERE subscription_token = $1",
        subscription_token
    )
    .fetch_optional(pool)
    .await
    .map_err(|e| {
        tracing::error!("Failed to execute query: {:?}", e);
        e
    })?;
    Ok(result.map(|r| r.subscriber_id))
}

#[tracing::instrument(name = "Mark subscriber as confirmed", skip(subscriber_id, pool))]
pub async fn confirm_subscriber(pool: &PgPool, subscriber_id: Uuid) -> Result<(), sqlx::Error> {
    sqlx::query!(
        r#"UPDATE subscriptions SET status = 'confirmed' WHERE id = $1"#,
        subscriber_id
    )
    .execute(pool)
    .await
    .map_err(|e| {
        tracing::error!("failed to execute query: {:?}", e);
        e
    })?;

    Ok(())
}
