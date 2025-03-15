//! src/domain/new_subscriber.rs
use crate::domain::{SubscriberName, SubscriberEmail};

pub struct NewSubscriber {
    pub email: SubscriberEmail,
    pub name: SubscriberName,
}