# PRD: Skjaya Data Intelligence Parser

## 1. Project Overview
**Skjaya Data Intelligence** is a high-performance web application designed to automate the extraction of inventory, sales, and administrative data from the `https://skjaya.id` platform. It leverages internal API endpoints for highly accurate and fast data retrieval.

## 2. Problem Statement
The current process of monitoring stock levels and sales reports on Seltrak (skjaya.id) requires manual login and manual navigation. Users need a way to quickly fetch this data into a structured format (like CSV or JSON) for analysis without performing repetitive manual tasks.

## 3. Goals
- **Full Data Sync**: Automatically discover and fetch all available API endpoints.
- **Universal Consolidation**: Save all fetched data into a single, structured `data.json` file.
- **Limitless Extraction**: Ensure all records are fetched by bypassing pagination limits (`limit=999999`).
- **User Experience**: Provide a modern, professional, and easy-to-use web interface for monitoring extraction progress.

## 4. Target Audience
- Store Owners (Owner account).
- Data Analysts and Inventory Managers.

## 5. Functional Requirements
### 5.1. Authentication
- Secure login using existing Seltrak credentials (owner/admin).
- Persistent session handling via Playwright browser context.

### 5.2. Data Extraction (Universal API-Based)
- **Automated Discovery**: Fetch data from all major internal API endpoints:
    - `inventory`, `deposit`, `restock`, `lost_return`
    - `employee`, `big_query`, `attendance`, `branch`, `category`
    - `customer`, `customer_movement`, `product`
    - `transaction_po`, `transaction_report`
- **Zero-Limit Policy**: All API calls use `limit=999999` to ensure complete data retrieval.
- **Consolidated Output**: Save all results into a unified `data.json` for easy programmatic access.

### 5.3. Web Interface
- **Progress Dashboard**: Real-time summary of records fetched per API.
- **Data Previewer**: Interactive dataframes and JSON viewers for immediate inspection.
- **Mass Export**: One-click download for the consolidated JSON file.

## 6. Technical Specifications
- **Language**: Python 3.x
- **UI Framework**: Streamlit
- **Browser Engine**: Playwright (Chromium)
- **Data Storage**: Local JSON (`data.json`)
- **Styling**: Premium Dark Mode with CSS Glassmorphism.

## 7. Non-Functional Requirements
- **Efficiency**: Fetching all APIs in a single authenticated session.
- **Data Integrity**: Preserving raw JSON structures from the source API.

## 8. Future Roadmap
- **Historical Tracking**: Comparative analysis between different sync timestamps.
- **Cloud Storage**: Auto-upload `data.json` to Supabase or Google Drive.
