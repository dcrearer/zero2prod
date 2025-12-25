//! tests/api/subscriptions.rs
use crate::helpers::spawn_app;
use assert2::assert;
use rstest::rstest;

#[tokio::test]
async fn subscribe_returns_a_200_for_valid_form_data() {
    let app = spawn_app().await;
    let body = "name=le%20guin&email=ursula_le_guin%40gmail.com";
    let response = app.post_subscriptions(body.into()).await;

    assert!(200 == response.status());

    let saved = sqlx::query!("SELECT email, name FROM subscriptions")
        .fetch_one(&app.db_pool)
        .await
        .expect("Failed to fetch saved subscription.");

    assert!(saved.email == "ursula_le_guin@gmail.com");
    assert!(saved.name == "le guin");
}

#[rstest]
#[case("name=le%20guin", "missing the email")]
#[case("email=ursula_le_guin%40gmail.com", "missing the name")]
#[case("", "missing both name and email")]
#[tokio::test]
async fn subscribe_returns_a_400_when_data_is_missing(
    #[case] invalid_body: String,
    #[case] error_message: &str,
) {
    let app = spawn_app().await;
    let response = app.post_subscriptions(invalid_body.into()).await;

    assert!(
        400 == response.status(),
        "The API did not fail with 400 Bad Request when the payload was {}.",
        error_message
    )
}

#[rstest]
#[case("name=&email=ursula_le_guin%40gmail.com", "empty name")]
#[case("name=Ursula&email=", "empty email")]
#[case("name=Ursula&email=definitely-not-an-email", "invalid email")]
#[tokio::test]
async fn subscribe_returns_a_400_when_fields_are_present_but_invalid(
    #[case] body: String,
    #[case] description: &str,
) {
    let app = spawn_app().await;
    let response = app.post_subscriptions(body.into()).await;

    assert!(
        400 == response.status(),
        "The API did not return 400 BAD Request when the payload was {}.",
        description
    );
}
