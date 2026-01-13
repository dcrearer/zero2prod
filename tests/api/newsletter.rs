//! tests/api/newsletter.rs
use crate::helpers::{ConfirmationLinks, TestApp, spawn_app};
use assert2::assert;
use rstest::rstest;
use uuid::Uuid;
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
    app.post_login(&serde_json::json!({
        "username": &app.test_user.username,
        "password": Uuid::new_v4().to_string()
    })).await;

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

    let title = "Newsletter";
    let html_content = "<p>Newsletter body as html</p>";
    let text_content = "Newsletter body as plain text";

    let response = app.post_newsletters(format!(
        "title={}&html_content={}&text_content={}",
        title, html_content, text_content
    )).await;

    // Assert
    assert!(response.status() == 303);
}

#[tokio::test]
async fn newsletters_are_delivered_to_confirmed_subscribers() {
    let app = spawn_app().await;
    create_confirmed_subscriber(&app).await;

    app.post_login(&serde_json::json!({
        "username": &app.test_user.username,
        "password": &app.test_user.password,
    })).await;

    Mock::given(path("/email"))
        .and(method("POST"))
        .respond_with(ResponseTemplate::new(200))
        .expect(1)
        .mount(&app.email_server)
        .await;

    // Act
    let title = "Newsletter";
    let html_content = "<p>Newsletter body as html</p>";
    let text_content = "Newsletter body as plain text";

    let response = app.post_newsletters(format!(
        "title={}&html_content={}&text_content={}",
        title, html_content, text_content
    )).await;

    assert!(response.status() == 303);

}

#[rstest]
#[case("html_content=<p>Newsletter body as HTML</p>&text_content=Newsletter body as plain text", "missing title")]
#[case("title=Newsletter", "missing content")]
#[tokio::test]
async fn newsletters_return_400_for_invalid_data(
    #[case] invalid_body: String,
    #[case] error_message: String,
) {
    let app = spawn_app().await;

    app.post_login(&serde_json::json!({
        "username": &app.test_user.username,
        "password": &app.test_user.password,
    })).await;


    let response = app.post_newsletters(invalid_body).await;

    // Assert
    assert!(
        400 == response.status(),
        "The API did not fail with 400 Bad Request when the payload was {}",
        error_message
    );
}

#[tokio::test]
async fn requests_missing_authorization_are_rejected() {
    let app = spawn_app().await;

    // app.post_login(&serde_json::json!({
    //     "username": &app.test_user.username,
    //     "password": &app.test_user.password,
    // })).await;

    let title = "Newsletter";
    let html_content = "<p>Newsletter body as html</p>";
    let text_content = "Newsletter body as plain text";

    let response = app.post_newsletters(format!(
        "title={}&html_content={}&text_content={}",
        title, html_content, text_content
    )).await;

    // Assert
    assert!(303 == response.status());

}

#[tokio::test]
async fn non_existing_user_is_rejected() {
    let app = spawn_app().await;

    app.post_login(&serde_json::json!({
        "username": Uuid::new_v4().to_string(),
        "password": Uuid::new_v4().to_string(),
    })).await;


    let title = "Newsletter";
    let html_content = "<p>Newsletter body as html</p>";
    let text_content = "Newsletter body as plain text";

    let response = app.post_newsletters(format!(
        "title={}&html_content={}&text_content={}",
        title, html_content, text_content
    )).await;

    // Assert
    assert!(303 == response.status());
}

#[tokio::test]
async fn invalid_password_is_rejected() {
    let app = spawn_app().await;

    app.post_login(&serde_json::json!({
        "username": &app.test_user.username,
        "password": Uuid::new_v4().to_string(),
    })).await;

    let title = "Newsletter";
    let html_content = "<p>Newsletter body as html</p>";
    let text_content = "Newsletter body as plain text";

    let response = app.post_newsletters(format!(
        "title={}&html_content={}&text_content={}",
        title, html_content, text_content
    )).await;

    assert!(303 == response.status());
}
