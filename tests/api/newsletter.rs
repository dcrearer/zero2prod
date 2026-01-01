//! tests/api/newsletter.rs
use crate::helpers::{ConfirmationLinks, TestApp, spawn_app};
use assert2::assert;
use rstest::rstest;
use wiremock::matchers::{any, method, path};
use wiremock::{Mock, ResponseTemplate};

async fn create_unconfirmed_subscriber(app: &TestApp) -> ConfirmationLinks {
    let body = "name=le%20guin&email=ursula_le_guin%40gmail.com";

    // Mock email server endpoint
    let _mock_guard = Mock::given(path("/email"))
        .and(method("POST"))
        .respond_with(ResponseTemplate::new(200))
        .named("Create unconfirmed subscriber")
        .expect(1)
        .mount_as_scoped(&app.email_server)
        .await;

    app.post_subscriptions(body.into())
        .await
        .error_for_status()
        .unwrap();

    let email_server = &app
        .email_server
        .received_requests()
        .await
        .unwrap()
        .pop()
        .unwrap();
    app.get_confirmation_links(email_server)
}

async fn create_confirmed_subscriber(app: &TestApp) {
    let confirmation_link = create_unconfirmed_subscriber(app).await;
    reqwest::get(confirmation_link.html)
        .await
        .unwrap()
        .error_for_status()
        .unwrap();
}

#[tokio::test]
async fn newsletters_are_not_delivered_to_unconfirmed_subscribers() {
    let app = spawn_app().await;
    create_unconfirmed_subscriber(&app).await;

    // If newsletter system incorrectly sends emails:
    // 1. System makes HTTP POST to /email
    // 2. Mock receives the call
    // 3. Mock thinks: "Expected 0 calls, but got 1!"
    // 4. Mock panics: "Mock was expected to be called 0 times but was called 1 times"
    // 5. Test fails

    Mock::given(any())
        .respond_with(ResponseTemplate::new(200))
        .expect(0)
        .mount(&app.email_server)
        .await;

    // Act
    let newsletter_request_body = serde_json::json!({
        "title": "Newsletter title",
        "content": {
            "text": "Newsletter body as plain text",
            "html": "<p>Newsletter body as HTML</p>",
        }
    });

    let response = app.post_newsletters(newsletter_request_body).await;

    // Assert
    assert!(response.status() == 200);
}

#[tokio::test]
async fn newsletters_are_delivered_to_confirmed_subscribers() {
    let app = spawn_app().await;
    create_confirmed_subscriber(&app).await;

    Mock::given(path("/email"))
        .and(method("POST"))
        .respond_with(ResponseTemplate::new(200))
        .expect(1)
        .mount(&app.email_server)
        .await;

    // Act
    let newsletter_request_body = serde_json::json!({
        "title": "Newsletter title",
        "content": {
            "text": "Newsletter body as plain text",
            "html": "<p>Newsletter body as HTML</p>",
        }
    });

    let response = app.post_newsletters(newsletter_request_body).await;

    assert!(response.status() == 200);
}

#[rstest]
#[case(
    serde_json::json!({
        "content": {
            "text": "Newsletter body as plain text",
            "html": "<p>Newsletter body as HTML</p>",}})
            ,"missing title")]
#[case(
    serde_json::json!({"title": "Newsletter"}),"missing content")]
#[tokio::test]
async fn newsletters_return_400_for_invalid_data(
    #[case] invalid_body: serde_json::Value,
    #[case] error_message: &str,
) {
    let app = spawn_app().await;

    let response = app.post_newsletters(invalid_body).await;

    // Assert
    assert!(
        400 == response.status(),
        "The API did not fail with 400 Bad Request when the payload was {}",
        error_message
    );
}
