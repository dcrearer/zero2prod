# API Documentation

## API Overview

**Base URL**: Configured via `application.base_url` in configuration
**Protocol**: HTTP/HTTPS
**Architecture**: RESTful API with server-rendered HTML responses (not JSON API)
**Authentication**: Cookie-based sessions for admin routes

## Public Endpoints

### Health Check

**Endpoint**: `GET /health_check`

**Description**: Returns health status of the application.

**Authentication**: None

**Request**: No parameters

**Response**:
- **Status**: 200 OK
- **Body**: Empty

**Example**:
```bash
curl -X GET http://localhost:8000/health_check
```

---

### Home Page

**Endpoint**: `GET /`

**Description**: Renders the home page.

**Authentication**: None

**Response**:
- **Status**: 200 OK
- **Content-Type**: text/html
- **Body**: HTML page

---

### Subscribe to Newsletter

**Endpoint**: `POST /subscriptions`

**Description**: Submits a subscription request. Creates a pending subscription and sends a confirmation email.

**Authentication**: None

**Request**:
- **Content-Type**: application/x-www-form-urlencoded
- **Body Parameters**:
  - `email` (string, required): Subscriber email address
  - `name` (string, required): Subscriber name

**Validation Rules**:
- Email must be valid format
- Name length: 1-256 characters
- Name must not contain forbidden characters: `,`, `/`, `(`, `)`, `"`, `<`, `>`, `\`, `{`, `}`

**Response**:
- **Success**: 200 OK (empty body)
- **Validation Error**: 400 Bad Request
- **Server Error**: 500 Internal Server Error

**Example**:
```bash
curl -X POST http://localhost:8000/subscriptions \
  -d "email=user@example.com&name=John Doe"
```

**Side Effects**:
- Inserts record into `subscriptions` table with status `pending_confirmation`
- Generates and stores confirmation token in `subscription_tokens` table
- Sends confirmation email with link to `/subscriptions/confirm?subscription_token={token}`

---

### Confirm Email Subscription

**Endpoint**: `GET /subscriptions/confirm`

**Description**: Confirms a pending subscription using the token from the confirmation email.

**Authentication**: None

**Request**:
- **Query Parameters**:
  - `subscription_token` (string, required): Token from confirmation email

**Response**:
- **Success**: 200 OK with HTML page
- **Invalid Token**: 401 Unauthorized
- **Server Error**: 500 Internal Server Error

**Example**:
```bash
curl -X GET "http://localhost:8000/subscriptions/confirm?subscription_token=abc123xyz"
```

**Side Effects**:
- Updates subscription status from `pending_confirmation` to `confirmed`
- Deletes used token from `subscription_tokens` table

---

## Authentication Endpoints

### Login Form

**Endpoint**: `GET /login`

**Description**: Renders the login form.

**Authentication**: None

**Response**:
- **Status**: 200 OK
- **Content-Type**: text/html
- **Body**: HTML login form

---

### Login Submission

**Endpoint**: `POST /login`

**Description**: Authenticates an admin user and creates a session.

**Authentication**: None (creates session on success)

**Request**:
- **Content-Type**: application/x-www-form-urlencoded
- **Body Parameters**:
  - `username` (string, required): Admin username
  - `password` (string, required): Admin password

**Response**:
- **Success**: 303 See Other → `/admin/dashboard`
  - Sets session cookie
- **Invalid Credentials**: 303 See Other → `/login` with error flash message
- **Server Error**: 500 Internal Server Error

**Example**:
```bash
curl -X POST http://localhost:8000/login \
  -d "username=admin&password=secret123" \
  -c cookies.txt
```

**Side Effects**:
- Creates session in Redis with user_id
- Sets HTTP-only session cookie

---

## Protected Admin Endpoints

All admin endpoints require authentication via session cookie. Unauthenticated requests are redirected to `/login`.

### Admin Dashboard

**Endpoint**: `GET /admin/dashboard`

**Description**: Renders the admin dashboard.

**Authentication**: Required (session cookie)

**Response**:
- **Success**: 200 OK with HTML dashboard
- **Unauthenticated**: 303 See Other → `/login`

---

### Newsletter Submission Form

**Endpoint**: `GET /admin/newsletters`

**Description**: Renders the form for submitting a newsletter issue.

**Authentication**: Required (session cookie)

**Response**:
- **Success**: 200 OK with HTML form
- **Unauthenticated**: 303 See Other → `/login`

---

### Publish Newsletter

**Endpoint**: `POST /admin/newsletters`

**Description**: Publishes a newsletter issue to all confirmed subscribers. Uses idempotency keys to prevent duplicate submissions.

**Authentication**: Required (session cookie)

**Request**:
- **Content-Type**: application/x-www-form-urlencoded
- **Body Parameters**:
  - `title` (string, required): Newsletter title
  - `text_content` (string, required): Plain text content
  - `html_content` (string, required): HTML content
  - `idempotency_key` (string, required): Client-supplied idempotency key

**Idempotency**:
- If the same `idempotency_key` is submitted again by the same user, the cached response is returned without re-executing the operation.

**Response**:
- **Success**: 303 See Other → `/admin/newsletters`
  - Sets flash message: "The newsletter issue has been accepted - emails will go out shortly."
- **Invalid Input**: 400 Bad Request
- **Unauthenticated**: 303 See Other → `/login`
- **Server Error**: 500 Internal Server Error

**Example**:
```bash
curl -X POST http://localhost:8000/admin/newsletters \
  -b cookies.txt \
  -d "title=Monthly Update&text_content=Hello...&html_content=<h1>Hello</h1>&idempotency_key=unique-key-123"
```

**Side Effects**:
- Inserts record into `newsletter_issues` table
- Enqueues delivery tasks (one per confirmed subscriber) into `issue_delivery_queue` table
- Stores response in `idempotency` table for replay

---

### Password Change Form

**Endpoint**: `GET /admin/password`

**Description**: Renders the password change form.

**Authentication**: Required (session cookie)

**Response**:
- **Success**: 200 OK with HTML form
- **Unauthenticated**: 303 See Other → `/login`

---

### Change Password

**Endpoint**: `POST /admin/password`

**Description**: Changes the authenticated user's password.

**Authentication**: Required (session cookie)

**Request**:
- **Content-Type**: application/x-www-form-urlencoded
- **Body Parameters**:
  - `current_password` (string, required): Current password for verification
  - `new_password` (string, required): New password
  - `new_password_check` (string, required): New password confirmation

**Validation Rules**:
- `new_password` and `new_password_check` must match
- `new_password` length: 12-128 characters
- `current_password` must verify against stored hash

**Response**:
- **Success**: 303 See Other → `/admin/password` with success flash message
- **Validation Error**: 303 See Other → `/admin/password` with error flash message
- **Unauthenticated**: 303 See Other → `/login`
- **Server Error**: 500 Internal Server Error

**Example**:
```bash
curl -X POST http://localhost:8000/admin/password \
  -b cookies.txt \
  -d "current_password=oldpass123&new_password=newpass456789&new_password_check=newpass456789"
```

**Side Effects**:
- Updates `password_hash` in `users` table
- Uses Argon2id for hashing

---

### Logout

**Endpoint**: `POST /admin/logout`

**Description**: Logs out the authenticated user by clearing the session.

**Authentication**: Required (session cookie)

**Response**:
- **Success**: 303 See Other → `/login`
  - Clears session cookie
- **Unauthenticated**: 303 See Other → `/login`

**Example**:
```bash
curl -X POST http://localhost:8000/admin/logout \
  -b cookies.txt
```

**Side Effects**:
- Deletes session from Redis
- Clears session cookie

---

## Data Models

### Subscriber (subscriptions table)

```rust
{
  id: Uuid,
  email: String,
  name: String,
  subscribed_at: DateTime<Utc>,
  status: String  // "pending_confirmation" | "confirmed"
}
```

### Subscription Token (subscription_tokens table)

```rust
{
  subscription_token: String,  // 25-character alphanumeric
  subscriber_id: Uuid
}
```

### User (users table)

```rust
{
  user_id: Uuid,
  username: String,
  password_hash: String  // Argon2id hash
}
```

### Newsletter Issue (newsletter_issues table)

```rust
{
  newsletter_issue_id: Uuid,
  title: String,
  text_content: String,
  html_content: String,
  published_at: DateTime<Utc>
}
```

### Issue Delivery Queue (issue_delivery_queue table)

```rust
{
  newsletter_issue_id: Uuid,
  subscriber_email: String
}
```

### Idempotency Record (idempotency table)

```rust
{
  user_id: Uuid,
  idempotency_key: String,
  response_status_code: i16,
  response_headers: Vec<HeaderPairRecord>,
  response_body: Vec<u8>,
  created_at: DateTime<Utc>
}
```

---

## Error Responses

### Standard Error Format

The application uses HTTP status codes and flash messages for error communication. Since this is a server-rendered application, errors are typically returned as HTML pages with flash messages, not JSON.

**Common Status Codes**:
- `200 OK` - Success
- `303 See Other` - Redirect after POST (PRG pattern)
- `400 Bad Request` - Validation error
- `401 Unauthorized` - Invalid token
- `500 Internal Server Error` - Server error

### Flash Messages

Flash messages are displayed on the next page load and automatically cleared. They are stored in signed cookies.

**Categories**:
- `info` - Informational messages (e.g., "Newsletter published")
- `error` - Error messages (e.g., "Invalid credentials")

---

## Authentication & Session Management

### Session Cookie

**Cookie Name**: Configured by actix-session (typically `id`)

**Properties**:
- HTTP-only: Yes (prevents JavaScript access)
- Secure: Yes (HTTPS only in production)
- SameSite: Lax
- Signed: Yes (HMAC with `hmac_secret`)

**Storage**: Redis

**Lifetime**: Configured via actix-session (typically session-scoped)

### HMAC Secret

Used for:
1. Signing session cookies
2. Signing flash message cookies

**Configuration**: `application.hmac_secret` in YAML or `APP_APPLICATION__HMAC_SECRET` env var

---

## Rate Limiting

**Current Implementation**: None

**AWS Modernization Opportunity**: Add API Gateway with rate limiting or use AWS WAF

---

## CORS

**Current Implementation**: None (same-origin only)

**AWS Modernization Opportunity**: Configure CORS middleware if building separate frontend

---

## API Versioning

**Current Implementation**: No versioning

**AWS Modernization Opportunity**: Add `/v1/` prefix for future versioning strategy

---

## External API Dependencies

### Email Service (Postmark)

**Base URL**: Configured via `email_client.base_url`

**Endpoint**: `POST /email`

**Authentication**: `X-Postmark-Server-Token` header

**Request Body**:
```json
{
  "From": "sender@example.com",
  "To": "recipient@example.com",
  "Subject": "Email subject",
  "HtmlBody": "<html>...</html>",
  "TextBody": "Plain text..."
}
```

**Response**:
- **Success**: 200 OK
- **Error**: 4xx/5xx with error details

**AWS Modernization**: Replace with Amazon SES for native AWS integration
