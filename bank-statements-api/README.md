# Bank Statement Analyzer API

Backend API for the Bank Statement Analyzer application.

## Features

- Transaction management (create, read, update, delete)
- Statement processing architecture for parsing bank statements
- Transaction categorization with hierarchical categories
- Accounts and counterparties as separate concepts: a transaction's other side is
  either a counterparty (a person or company) or one of your own accounts (a transfer)
- File upload and analysis
- RESTful API with FastAPI
- PostgreSQL database
- Hexagonal Architecture (Ports and Adapters)
- LLM integration for schema detection

## Setup

### Prerequisites

- Python 3.8+
- PostgreSQL

### Installation

1. Clone the repository
2. Create a virtual environment:
   ```
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```
3. Install dependencies:
   ```
   pip install -e .
   ```
4. Create a PostgreSQL database:
   ```
   createdb bank_statements
   ```
5. Initialize the database:
   ```
   python -m app.db_init
   ```

## Running the API

```
python run.py
```

The API will be available at http://localhost:8000.

## API Documentation

Once the API is running, you can access the Swagger documentation at:
- http://localhost:8000/docs
- http://localhost:8000/redoc

## Key Components

### Statement Processing Architecture

The Statement Processing Architecture consists of several components that work together to process bank statements:

1. **StatementFileTypeDetector**: Detects file types (CSV, XLSX)
2. **StatementParser**: Parses file content into DataFrames
3. **SchemaDetector**: Uses LLM to detect column mappings
4. **TransactionNormalizer**: Normalizes transaction data
5. **StatementAnalyzerService**: Analyzes files and handles deduplication
6. **StatementPersistenceService**: Persists transactions to the database

### Transaction Categorization

The Transaction Categorization system includes:

1. **Category Model**: Hierarchical structure with parent-child relationships
2. **CategoryRepository**: Interface and implementation for category data access
3. **CategoryService**: Business logic for category management
4. **TransactionCategorizer**: Interface for categorizing transactions
5. **TransactionCategorizationService**: Batch processing of uncategorized transactions

### Database Schema

The main tables are:

1. **transactions**: Transaction data, its category, and its other side
2. **accounts**: Your own money sources and destinations; owns statements, initial
   balances and import configs
3. **counterparties**: The people, companies and merchants you transact with
4. **categories**: Hierarchical categories
5. **enhancement_rules**: Pattern rules that assign a category and an other side
6. **statements**: Uploaded statements, belonging to an account
7. **uploaded_files** / **file_analysis_metadata**: Raw file content and the saved
   import config, keyed by file hash for deduplication

A transaction carries `counterparty_id` or `transfer_account_id`, never both — a
check constraint enforces it. See ARCHITECTURE.md for the full schema.

## Project Structure

The project follows Hexagonal Architecture (Ports and Adapters):

- `app/domain/models/`: Domain models (Transaction, Account, Counterparty, Category, UploadedFile, FileAnalysisMetadata)
- `app/ports/repositories/`: Repository interfaces (ports)
- `app/ports/categorizers/`: Categorization interfaces
- `app/adapters/repositories/`: Repository implementations (adapters)
- `app/services/`: Application services (business logic)
  - `transaction.py`: Transaction management
  - `category.py`: Category management
  - `account.py`: Account management
  - `counterparty.py`: Counterparty management
  - `account_conversion.py`: Converts an account that is really a person or company
    into a counterparty, repointing its references
  - `enhancement_rule_management.py`: Rule management and retroactive application
- `app/ai/`: LLM integration for schema detection
- `app/api/`: API endpoints and schemas
- `app/core/`: Core configuration and utilities
