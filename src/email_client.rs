//! src/email_client.rs
use crate::domain::SubscriberEmail;
use aws_config::BehaviorVersion;
use aws_sdk_sesv2::error::{BuildError, SdkError};
use aws_sdk_sesv2::operation::send_email::SendEmailError;
use aws_sdk_sesv2::{
    Client,
    types::{Body, Content, Destination, EmailContent, Message},
};

#[derive(Clone)]
pub struct EmailClient {
    ses_client: Client,
    sender: SubscriberEmail,
}

pub struct SendEmailRequest {
    pub recipient: SubscriberEmail,
    pub subject: String,
    pub html_body: String,
    pub text_body: String,
}

impl EmailClient {
    pub async fn new(sender: SubscriberEmail) -> EmailClient {
        let config = aws_config::defaults(BehaviorVersion::latest()).load().await;
        let ses_client = Client::new(&config);

        Self { ses_client, sender }
    }

    pub async fn send_email(
        &self,
        request: SendEmailRequest,
    ) -> Result<(), SdkError<SendEmailError>> {
        let destination = Destination::builder()
            .to_addresses(request.recipient.as_ref())
            .build();

        let email_content =
            Self::build_email_content(request).map_err(SdkError::construction_failure)?;

        self.ses_client
            .send_email()
            .from_email_address(self.sender.as_ref())
            .destination(destination)
            .content(email_content)
            .send()
            .await?;

        Ok(())
    }

    fn build_email_content(request: SendEmailRequest) -> Result<EmailContent, BuildError> {
        let subject_content = Content::builder().data(request.subject).build()?;
        // .map_err(|e| format!("Failed to build subject: {}", e))?;

        let html_body = Content::builder().data(request.html_body).build()?;

        let text_body = Content::builder().data(request.text_body).build()?;

        let body = Body::builder().html(html_body).text(text_body).build();

        let message = Message::builder()
            .subject(subject_content)
            .body(body)
            .build();

        Ok(EmailContent::builder().simple(message).build())
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[tokio::test]
    async fn send_email_to_ses_simulator() {
        use crate::configuration::get_configuration;

        let config = get_configuration().expect("Failed to read configuration");
        let sender = config.email_client.sender().expect("Invalid sender email");
        let email_client = EmailClient::new(sender).await;

        let recipient =
            SubscriberEmail::parse("success@simulator.amazonses.com".to_string()).unwrap();

        let request = SendEmailRequest {
            recipient,
            subject: "Test Subject".to_string(),
            html_body: "<h1>Test Email</h1><p>This is a test from zero2prod</p>".to_string(),
            text_body: "Test Email\n\nThis is a test from zero2prod".to_string(),
        };

        let result = email_client.send_email(request).await;

        assert!(result.is_ok(), "Failed to send email: {:?}", result);
    }
}
