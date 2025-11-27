use crate::domain::SubscriberEmail;
use config::{Config, Environment, File};
use secrecy::{ExposeSecret, SecretString};
use serde::Deserialize;
use serde_aux::field_attributes::deserialize_number_from_string;
use sqlx::postgres::PgConnectOptions;
use sqlx::postgres::PgSslMode;

#[derive(Debug, Clone, Deserialize)]
pub struct Settings {
    pub database: DatabaseSettings,
    pub application: ApplicationSettings,
    pub email_client: EmailClientSettings,
}

#[derive(Debug, Clone, Deserialize)]
pub struct DatabaseSettings {
    pub username: String,
    pub password: SecretString,
    #[serde(deserialize_with = "deserialize_number_from_string")]
    pub port: u16,
    pub host: String,
    pub database_name: String,
    pub require_ssl: bool,
}

#[derive(Debug, Clone, Deserialize)]
pub struct ApplicationSettings {
    #[serde(deserialize_with = "deserialize_number_from_string")]
    pub port: u16,
    pub host: String,
    pub base_url: String,
}

#[derive(Debug, Clone, Deserialize)]
pub struct EmailClientSettings {
    pub sender_email: String,
}

impl DatabaseSettings {
    pub fn connection_option(&self) -> PgConnectOptions {
        let ssl_mode = if self.require_ssl {
            PgSslMode::Require
        } else {
            PgSslMode::Prefer
        };

        PgConnectOptions::new()
            .host(&self.host)
            .username(&self.username)
            .password(self.password.expose_secret())
            .port(self.port)
            .ssl_mode(ssl_mode)
            .database(&self.database_name)
    }
}

impl EmailClientSettings {
    pub fn sender(&self) -> Result<SubscriberEmail, String> {
        SubscriberEmail::parse(self.sender_email.clone())
    }
}

pub fn get_configuration() -> Result<Settings, config::ConfigError> {
    Config::builder()
        .add_source(File::with_name("configuration/base").required(false))
        .add_source(File::with_name("configuration/local").required(false))
        .add_source(Environment::with_prefix("APP").separator("__"))
        .build()?
        .try_deserialize()
}
