# Wallet Service API

A backend wallet service with Paystack payment integration, JWT authentication, and API key management for service-to-service access.

## Features

- Google OAuth 2.0 authentication with JWT tokens
- Wallet creation and balance management
- Paystack deposit integration with webhook verification
- Wallet-to-wallet transfers (atomic transactions)
- Transaction history tracking
- API key system for programmatic access
- Permission-based access control (deposit, transfer, read)
- API key expiration and rollover
- Maximum 5 active API keys per user
- Idempotent webhook processing
- Dual authentication: JWT or API keys

## Tech Stack

- **Framework:** FastAPI
- **Database:** PostgreSQL with SQLAlchemy ORM
- **Authentication:** JWT (Google OAuth), API Keys (SHA256 hashing)
- **Payment Provider:** Paystack
- **Migrations:** Alembic

## Installation

### Prerequisites
- Python 3.9+
- PostgreSQL 12+
- Paystack account (test keys)
- Google OAuth credentials

### Setup

1. **Clone repository:**
```bash
git clone https://github.com/idyweb/Wallet_Service_with_Paystack
cd wallet_service_with_paystack
```

2. **Create virtual environment:**
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. **Install dependencies:**
```bash
pip install -r requirements.txt
```

4. **Configure environment variables:**
```bash
cp .env.example .env
# Edit .env with your credentials
```

Required environment variables:
```env
DATABASE_URL=postgresql://user:password@localhost:5432/wallet_db
GOOGLE_CLIENT_ID=your_google_client_id
GOOGLE_CLIENT_SECRET=your_google_client_secret
GOOGLE_REDIRECT_URI=http://localhost:8000/auth/google/callback
JWT_SECRET_KEY=your-secret-key-min-32-characters
PAYSTACK_SECRET_KEY=sk_test_your_paystack_secret_key
```

5. **Run database migrations:**
```bash
alembic revision --autogenerate -m "Initial migration"
alembic upgrade head
```

6. **Start server:**
```bash
uvicorn main:app --reload --port 8000
```

Server will be available at: `http://localhost:8000`

## API Documentation

Interactive API docs available at:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

## Authentication

### Method 1: JWT (For Users)

**Step 1:** Get Google authorization URL
```bash
GET /auth/google
```

**Step 2:** User completes OAuth flow, receives JWT
```bash
GET /auth/google/callback?code=...
```

Response:
```json
{
  "status": "success",
  "data": {
    "jwt_token": "eyJhbGc...",
    "user": {
      "id": "uuid",
      "email": "user@example.com",
      "full_name": "John Doe"
    }
  }
}
```

**Step 3:** Use JWT in requests
```bash
Authorization: Bearer <jwt_token>
```

### Method 2: API Keys (For Services)

**Create API Key:**
```bash
POST /keys/create
Authorization: Bearer <jwt_token>
Content-Type: application/json

{
  "name": "payment-service",
  "permissions": ["deposit", "transfer", "read"],
  "expiry": "1D"
}
```

**Use API Key:**
```bash
x-api-key: sk_live_xxxxx
```

## API Endpoints

### Authentication
- `GET /auth/google` - Initiate Google OAuth
- `GET /auth/google/callback` - OAuth callback (returns JWT)

### API Key Management
- `POST /keys/create` - Create new API key (requires JWT)
- `POST /keys/rollover` - Rollover expired key (requires JWT)

### Wallet Operations
- `POST /wallet/deposit` - Initialize Paystack deposit
- `POST /wallet/paystack/webhook` - Paystack webhook handler
- `GET /wallet/deposit/{reference}/status` - Check deposit status
- `GET /wallet/balance` - Get wallet balance
- `POST /wallet/transfer` - Transfer funds to another wallet
- `GET /wallet/transactions` - Get transaction history

## Usage Examples

### 1. Deposit Money

```bash
POST /wallet/deposit
Authorization: Bearer <jwt_token>
Content-Type: application/json

{
  "amount": 5000
}
```

Response:
```json
{
  "status": "success",
  "data": {
    "reference": "dep_abc123",
    "authorization_url": "https://checkout.paystack.com/xyz"
  }
}
```

Complete payment at the `authorization_url`. Wallet will be credited automatically via webhook.

### 2. Check Balance

```bash
GET /wallet/balance
x-api-key: sk_live_xxxxx
```

Response:
```json
{
  "status": "success",
  "data": {
    "balance": 5000,
    "currency": "NGN"
  }
}
```

### 3. Transfer Funds

```bash
POST /wallet/transfer
Authorization: Bearer <jwt_token>
Content-Type: application/json

{
  "wallet_number": "a1b2c3d4e5f6",
  "amount": 1000
}
```

Response:
```json
{
  "status": "success",
  "message": "Transfer completed",
  "data": {
    "reference": "txf_xyz789",
    "amount": 1000,
    "recipient": "a1b2c3d4e5f6"
  }
}
```

### 4. View Transaction History

```bash
GET /wallet/transactions
Authorization: Bearer <jwt_token>
```

Response:
```json
{
  "status": "success",
  "data": {
    "transactions": [
      {
        "id": "uuid",
        "type": "deposit",
        "direction": "credit",
        "amount": 5000,
        "status": "success",
        "reference": "dep_abc123",
        "created_at": "2025-12-10T06:00:00Z"
      }
    ]
  }
}
```

## API Key System

### Permissions
- `deposit` - Initialize deposits
- `transfer` - Transfer funds between wallets
- `read` - View balance and transaction history

### Expiry Options
- `1H` - 1 hour
- `1D` - 1 day
- `1M` - 30 days
- `1Y` - 365 days

### Limits
- Maximum **5 active API keys** per user
- Expired keys can be rolled over with new expiry
- API keys are shown only once during creation

### Rollover Expired Key

```bash
POST /keys/rollover
Authorization: Bearer <jwt_token>
Content-Type: application/json

{
  "expired_key_id": "uuid-of-expired-key",
  "expiry": "1M"
}
```

New key inherits permissions from expired key.

## Paystack Integration

### Webhook Setup

1. Go to Paystack Dashboard → Settings → Webhooks
2. Add webhook URL: `https://yourdomain.com/wallet/paystack/webhook`
3. Paystack will send `charge.success` events when payments complete

### Testing Deposits

**Test Cards:**
- Success: `4084084084084081`
- Declined: `5060666666666666666`

Use any future expiry date and any CVV.

Paystack test docs: https://paystack.com/docs/payments/test-payments/

## Security Features

- Paystack webhook signature verification
- JWT token expiration (7 days default)
- API key hashing (SHA256)
- Permission-based access control
- Idempotent transaction processing
- Atomic wallet transfers (database transactions)
- Insufficient balance checks
- CORS middleware configuration

## Error Handling

The API returns standardized error responses:

```json
{
  "status": "failure",
  "status_code": 400,
  "message": "Insufficient balance",
  "error": {
    "balance": 1000,
    "required": 5000
  }
}
```

Common errors:
- `400` - Invalid request (insufficient balance, invalid expiry format)
- `401` - Authentication required or API key expired
- `403` - Missing required permission
- `404` - Resource not found (wallet, transaction, API key)
- `422` - Validation error

## Database Schema

### Users
- `id` (UUID, PK)
- `google_id` (String, Unique)
- `email` (String, Unique)
- `full_name` (String)

### Wallets
- `id` (UUID, PK)
- `user_id` (UUID, FK → users.id)
- `wallet_number` (String, Unique)
- `balance` (BigInt, in kobo)
- `currency` (String, default: NGN)

### Transactions
- `id` (UUID, PK)
- `reference` (String, Unique)
- `wallet_id` (UUID, FK → wallets.id)
- `user_id` (UUID, FK → users.id)
- `type` (Enum: deposit, transfer, withdrawal)
- `direction` (Enum: credit, debit)
- `amount` (BigInt, in kobo)
- `status` (Enum: pending, success, failed)
- `related_tx_id` (UUID, for linking transfer pairs)

### API Keys
- `id` (UUID, PK)
- `user_id` (UUID, FK → users.id)
- `name` (String)
- `hashed_key` (String)
- `permissions` (Array[String])
- `expires_at` (DateTime)
- `revoked` (Boolean)

### Webhook Logs
- `id` (UUID, PK)
- `provider` (String, e.g., "paystack")
- `payload` (JSON)
- `headers` (JSON)
- `processed` (Boolean)

## Development

### Running Tests
```bash
pytest
```

### Database Migrations
```bash
# Create new migration
alembic revision --autogenerate -m "Description"

# Apply migrations
alembic upgrade head

# Rollback
alembic downgrade -1
```


## Deployment

### Production Checklist
- [ ] Set strong `JWT_SECRET_KEY`
- [ ] Use production Paystack keys
- [ ] Configure CORS allowed origins
- [ ] Set up SSL/TLS (HTTPS)
- [ ] Configure production database
- [ ] Set up webhook URL in Paystack dashboard
- [ ] Enable database backups
- [ ] Set up monitoring/logging
- [ ] Configure rate limiting

### Environment Variables (Production)
```env
ENVIRONMENT=production
DATABASE_URL=postgresql://user:pass@host:5432/db
JWT_SECRET_KEY=<strong-secret-key>
PAYSTACK_SECRET_KEY=sk_live_<production-key>
```

## Support

For issues or questions:
- API Documentation: `/docs`
- Paystack Docs: https://paystack.com/docs
- Create an issue in the repository
