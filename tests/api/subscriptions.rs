//! tests/api/subscriptions.rs
use crate::helpers::spawn_app;
use assert2::assert;
use rstest::rstest;
use wiremock::matchers::{method, path};
use wiremock::{Mock, ResponseTemplate};

#[tokio::test]
async fn subscribe_returns_a_200_for_valid_form_data() {
    let app = spawn_app().await;
    let body = "name=le%20guin&email=ursula_le_guin%40gmail.com";

    Mock::given(path("/email"))
        .and(method("POST"))
        .respond_with(ResponseTemplate::new(200))
        .mount(&app.email_server)
        .await;

    let response = app.post_subscriptions(body.into()).await;

    assert!(200 == response.status());
}

#[tokio::test]
async fn subscribe_persist_the_new_subscriber() {
    let app = spawn_app().await;
    let body = "name=le%20guin&email=ursula_le_guin%40gmail.com";

    Mock::given(path("/email"))
        .and(method("POST"))
        .respond_with(ResponseTemplate::new(200))
        .mount(&app.email_server)
        .await;

    // Act
    app.post_subscriptions(body.into()).await;

    // Assert
    let saved = sqlx::query!("SELECT email, name, status FROM subscriptions")
        .fetch_one(&app.db_pool)
        .await
        .expect("Failed to fetch saved subscription.");

    assert!(saved.email == "ursula_le_guin@gmail.com");
    assert!(saved.name == "le guin");
    assert!(saved.status == "pending_confirmation");
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
    let response = app.post_subscriptions(invalid_body).await;

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
    let response = app.post_subscriptions(body).await;

    assert!(
        400 == response.status(),
        "The API did not return 400 BAD Request when the payload was {}.",
        description
    );
}

#[tokio::test]
async fn subscribe_sends_a_confirmation_email_for_valid_data() {
    let app = spawn_app().await;
    let body = "name=le%20guin&email=ursula_le_guin%40gmail.com";

    Mock::given(path("/email"))
        .and(method("POST"))
        .respond_with(ResponseTemplate::new(200))
        .expect(1)
        .mount(&app.email_server)
        .await;

    // Act
    let response = app.post_subscriptions(body.into()).await;

    // Assert
    assert!(200 == response.status());
}

#[tokio::test]
async fn subscribe_sends_a_confirmation_email_with_a_link() {
    let app = spawn_app().await;
    let body = "name=le%20guin&email=ursula_le_guin%40gmail.com";

    Mock::given(path("/email"))
        .and(method("POST"))
        .respond_with(ResponseTemplate::new(200))
        .mount(&app.email_server)
        .await;

    // Act
    app.post_subscriptions(body.into()).await;

    // Assert
    let email_request = &app.email_server.received_requests().await.unwrap()[0];
    let confirmation_links = app.get_confirmation_links(email_request);

    assert!(confirmation_links.html == confirmation_links.plain_text);
}

#[tokio::test]
async fn subscribe_fails_if_there_is_a_fatal_database_error() {
    let app = spawn_app().await;
    let body = "name=le%20guin&email=ursula_le_guin%40gmail.com";

    // Sabotage the database
    sqlx::query!("ALTER TABLE subscription_tokens DROP COLUMN subscription_token;")
        .execute(&app.db_pool)
        .await
        .unwrap();

    let response = app.post_subscriptions(body.into()).await;
    assert!(response.status() == 500);
}
