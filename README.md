# LedgerPro - Accounting & Financial Management System

A comprehensive, production-grade accounting platform built with Django, Django REST Framework, React, PostgreSQL, Redis, and Celery. LedgerPro provides full double-entry bookkeeping, chart of accounts management, journal entries, financial statement generation (Profit & Loss, Balance Sheet, Cash Flow), tax calculations, multi-currency support, and complete audit trails.

## Features

- **Double-Entry Bookkeeping**: Every transaction is recorded as balanced debits and credits ensuring accounting integrity.
- **Chart of Accounts**: Hierarchical account structure supporting Assets, Liabilities, Equity, Revenue, and Expenses with unlimited sub-account depth.
- **Journal Entries**: Create, review, approve, and post journal entries with full audit trail tracking.
- **Financial Statements**: Auto-generated Profit & Loss, Balance Sheet, and Cash Flow statements with date-range filtering and comparative periods.
- **Invoicing**: Create professional invoices, track payments, issue credit notes, and manage accounts receivable.
- **Expense Management**: Categorize expenses, attach receipts, and track spending against budgets.
- **Banking**: Bank account management, transaction import, and bank reconciliation workflow.
- **Tax Management**: Configurable tax rates, automatic tax calculations on invoices, and tax return preparation.
- **Multi-Currency**: Full multi-currency support with real-time exchange rate updates and currency conversion.
- **Audit Trail**: Every data change is logged with timestamp, user, and before/after values for regulatory compliance.
- **Multi-Tenant**: Company-based data isolation supporting multiple businesses per user.
- **Role-Based Access Control**: Granular permissions for Accountant, Manager, Auditor, and Admin roles.

## Architecture

```
+-------------------+       +-------------------+       +-------------------+
|   React Frontend  | <---> |   Nginx Reverse   | <---> |  Django + DRF API |
|   (Port 3000)     |       |   Proxy (Port 80) |       |   (Port 8000)     |
+-------------------+       +-------------------+       +-------------------+
                                                                |
                                    +---------------------------+---------------------------+
                                    |                           |                           |
                            +-------v-------+           +-------v-------+           +-------v-------+
                            |  PostgreSQL   |           |     Redis     |           |    Celery     |
                            |  (Port 5432)  |           |  (Port 6379)  |           |   Worker      |
                            +---------------+           +---------------+           +---------------+
```

## Tech Stack

| Layer       | Technology                        |
|-------------|-----------------------------------|
| Backend     | Python 3.11, Django 4.2, DRF 3.14 |
| Frontend    | React 18, Redux Toolkit, Recharts |
| Database    | PostgreSQL 15                     |
| Cache/Queue | Redis 7                           |
| Task Queue  | Celery 5.3                        |
| Web Server  | Nginx 1.25                        |
| Containers  | Docker, Docker Compose            |

## Prerequisites

- Docker and Docker Compose v2+
- Git

## Quick Start

1. **Clone the repository**
   ```bash
   git clone https://github.com/your-org/ledgerpro.git
   cd ledgerpro
   ```

2. **Configure environment variables**
   ```bash
   cp .env.example .env
   # Edit .env with your preferred settings
   ```

3. **Build and start all services**
   ```bash
   docker compose up --build -d
   ```

4. **Run database migrations**
   ```bash
   docker compose exec backend python manage.py migrate
   ```

5. **Create a superuser**
   ```bash
   docker compose exec backend python manage.py createsuperuser
   ```

6. **Seed initial data (chart of accounts template)**
   ```bash
   docker compose exec backend python manage.py seed_accounts
   ```

7. **Access the application**
   - Frontend: http://localhost
   - API: http://localhost/api/
   - Admin: http://localhost/api/admin/

## Development Setup (without Docker)

### Backend
```bash
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver
```

### Frontend
```bash
cd frontend
npm install
npm start
```

## API Documentation

The API follows RESTful conventions. All endpoints require authentication via JWT tokens.

### Authentication
| Endpoint              | Method | Description          |
|-----------------------|--------|----------------------|
| /api/auth/login/      | POST   | Obtain JWT tokens    |
| /api/auth/refresh/    | POST   | Refresh access token |
| /api/auth/register/   | POST   | Register new user    |

### Ledger
| Endpoint                        | Method | Description                |
|---------------------------------|--------|----------------------------|
| /api/ledger/accounts/           | GET    | List chart of accounts     |
| /api/ledger/accounts/           | POST   | Create account             |
| /api/ledger/journal-entries/    | GET    | List journal entries       |
| /api/ledger/journal-entries/    | POST   | Create journal entry       |
| /api/ledger/trial-balance/      | GET    | Generate trial balance     |

### Invoicing
| Endpoint                  | Method | Description           |
|---------------------------|--------|-----------------------|
| /api/invoicing/invoices/  | GET    | List invoices         |
| /api/invoicing/invoices/  | POST   | Create invoice        |
| /api/invoicing/payments/  | POST   | Record payment        |

### Reports
| Endpoint                        | Method | Description            |
|---------------------------------|--------|------------------------|
| /api/reports/profit-loss/       | GET    | Profit & Loss report   |
| /api/reports/balance-sheet/     | GET    | Balance Sheet report   |
| /api/reports/cash-flow/         | GET    | Cash Flow Statement    |

## Environment Variables

See `.env.example` for all available configuration options.

## Testing

```bash
# Backend tests
docker compose exec backend python manage.py test

# Frontend tests
docker compose exec frontend npm test
```

## Project Structure

```
ledgerpro/
├── backend/
│   ├── apps/
│   │   ├── accounts/      # User management, companies, fiscal years
│   │   ├── ledger/         # Chart of accounts, journal entries, double-entry
│   │   ├── invoicing/      # Invoices, payments, credit notes
│   │   ├── expenses/       # Expense tracking and categorization
│   │   ├── banking/        # Bank accounts and reconciliation
│   │   ├── reports/        # Financial statement generation
│   │   └── tax/            # Tax rates and tax returns
│   ├── config/             # Django settings and configuration
│   └── utils/              # Shared utilities
├── frontend/
│   └── src/
│       ├── api/            # API client modules
│       ├── components/     # Reusable React components
│       ├── pages/          # Page-level components
│       ├── store/          # Redux store and slices
│       └── hooks/          # Custom React hooks
├── nginx/                  # Nginx configuration
├── docker-compose.yml
└── .env.example
```

## License

This project is licensed under the MIT License.
