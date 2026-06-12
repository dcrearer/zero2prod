# Business Overview

## Business Context Diagram

```text
+------------------------------------------------------------------+
|                     Newsletter Service System                    |
|                          (zero2prod)                             |
+------------------------------------------------------------------+
|                                                                  |
|  External Actors:                                                |
|  +------------------------+    +---------------------------+     |
|  | Public Users           |    | Admin Users               |     |
|  | (Newsletter Readers)   |    | (Content Publishers)      |     |
|  +------------------------+    +---------------------------+     |
|            |                              |                      |
|            v                              v                      |
|  +-------------------+          +----------------------+         |
|  | Subscription Mgmt |          | Newsletter Publishing|         |
|  |  - Subscribe      |          |  - Create Issues     |         |
|  |  - Confirm Email  |          |  - Queue Delivery    |         |
|  +-------------------+          +----------------------+         |
|            |                              |                      |
|            v                              v                      |
|  +-------------------------------------------------------+       |
|  |           Core Business Services                      |       |
|  | - User Authentication & Authorization                 |       |
|  | - Email Delivery (async background processing)       |       |
|  | - Idempotency Management                              |       |
|  +-------------------------------------------------------+       |
|                                                                  |
|  External Dependencies:                                          |
|  +------------------+  +------------------+  +---------------+   |
|  | PostgreSQL DB    |  | Redis Cache      |  | Email Service |   |
|  | (Persistent Data)|  | (Sessions)       |  | (Postmark API)|   |
|  +------------------+  +------------------+  +---------------+   |
+------------------------------------------------------------------+
```

## Business Description

**Business Description**: Zero2prod is a production-grade newsletter distribution service that enables organizations to manage subscriber lists and distribute email newsletters. The system handles the complete lifecycle of newsletter operations: user subscription with email confirmation, administrative content publishing, and asynchronous email delivery to confirmed subscribers.

**Business Transactions**: 

1. **Subscription Registration** - Public users submit their email and name to subscribe to the newsletter. The system validates input, generates a unique confirmation token, stores the pending subscription, and sends a confirmation email.

2. **Email Confirmation** - Users click a link in their confirmation email with a unique token. The system validates the token and activates the subscription, marking it as "confirmed".

3. **User Authentication** - Admin users log in with username/password. The system validates credentials using Argon2 hashing, creates a secure session in Redis, and grants access to administrative features.

4. **Newsletter Publishing** - Authenticated admins create newsletter issues with title, text content, and HTML content. The system uses idempotency keys to prevent duplicate submissions, stores the newsletter issue, and enqueues delivery tasks (one per confirmed subscriber).

5. **Async Email Delivery** - A background worker continuously polls the delivery queue, retrieves pending tasks using row-level locking (FOR UPDATE SKIP LOCKED), sends emails via the email service API, and removes completed tasks from the queue.

6. **Password Management** - Authenticated admins can change their password. The system validates the current password, hashes the new password with Argon2, and updates the user record.

7. **Session Management** - The system maintains admin sessions in Redis with secure cookie-based session IDs, automatically expiring inactive sessions.

**Business Dictionary**:

- **Subscriber**: A person who has registered to receive newsletters. Status can be "pending_confirmation" or "confirmed".
- **Subscription Token**: A unique, time-limited token sent via email to verify subscriber email addresses.
- **Newsletter Issue**: A published newsletter containing title, text content, and HTML content, distributed to all confirmed subscribers.
- **Delivery Queue**: An asynchronous task queue containing one delivery task per confirmed subscriber per newsletter issue.
- **Idempotency Key**: A unique identifier supplied by the client to prevent duplicate newsletter submissions if the request is retried.
- **Confirmed Subscriber**: A subscriber who has completed email verification by clicking the confirmation link.
- **Admin User**: An authenticated user with privileges to publish newsletters and manage administrative functions.
- **Session**: A secure, time-limited authentication context stored in Redis and referenced by a cookie.

## Component Level Business Descriptions

### Web Application (Main Binary)
- **Purpose**: Serves as the primary HTTP API for public subscription operations and admin newsletter management
- **Responsibilities**: 
  - Handles HTTP requests/responses
  - Manages authentication and authorization
  - Routes requests to appropriate handlers
  - Manages database transactions
  - Integrates with email service for confirmation emails

### Background Worker
- **Purpose**: Processes the newsletter delivery queue asynchronously to send emails to confirmed subscribers
- **Responsibilities**:
  - Polls delivery queue continuously
  - Retrieves newsletter content
  - Sends emails via email service API
  - Handles failures gracefully (logs errors, continues processing)
  - Prevents race conditions using database row-level locking

### Domain Layer
- **Purpose**: Enforces business rules and validation for core domain entities
- **Responsibilities**:
  - Validates subscriber names (length, forbidden characters)
  - Validates email addresses (format, DNS validation)
  - Provides type-safe wrappers for domain values

### Authentication & Authorization Module
- **Purpose**: Secures admin endpoints and manages user sessions
- **Responsibilities**:
  - Password hashing and verification (Argon2)
  - Session creation and validation
  - Middleware to protect admin routes
  - User credential management

### Idempotency Module
- **Purpose**: Prevents duplicate newsletter publications when requests are retried
- **Responsibilities**:
  - Validates idempotency keys
  - Tracks request processing state
  - Stores and retrieves cached responses
  - Ensures exactly-once semantics for newsletter publishing

### Email Client
- **Purpose**: Integrates with external email service provider (Postmark) to send transactional emails
- **Responsibilities**:
  - Formats email requests
  - Authenticates with Postmark API
  - Sends confirmation and newsletter emails
  - Handles timeouts and retries
