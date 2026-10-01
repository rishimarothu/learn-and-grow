# Learn & Grow - Code Architecture & Documentation

This document explains the structure of the codebase, why each file exists, and how they interact with each other.

## 1. Backend Engine (Python / FastAPI)
The backend is split into three main modules to follow the **MVC (Model-View-Controller)** pattern conceptually, keeping the code clean and avoiding circular dependency crashes.

- **`main.py` (The Controller / Router)**
  - *Why it's here:* This is the brain of the application. It listens for HTTP requests from the browser (like GET `/dashboard` or POST `/login`). It contains all the routing, authentication logic (JWT), and business logic (calculating coins, checking if a user is an admin). 
  - *What it does:* It fetches data from the database, processes it, and injects it into the HTML templates.

- **`models.py` (The Data Schema)**
  - *Why it's here:* To tell SQLAlchemy (our database manager) exactly what our database tables look like. 
  - *What it does:* It defines Python classes (User, Resource, ExchangeRequest, etc.) that map directly to rows and columns in the `learnandgrow.db` SQLite database.

- **`database.py` (The Database Connection)**
  - *Why it's here:* To establish the actual connection to the SQLite file. 
  - *What it does:* It creates the SQLAlchemy `engine` and `SessionLocal` factories. Keeping this separate ensures that both `main.py` and `models.py` can import the connection without importing each other and causing an infinite loop.

## 2. Frontend Templates (`/templates` folder)
We use **Jinja2** templates. These are HTML files infused with Python-like syntax (e.g., `{% if user.role == 'admin' %}`). 

- *Why they are here:* Instead of building a complex React/Vue frontend, we use Server-Side Rendering (SSR). FastAPI takes these HTML files, injects the live database data into them, and sends the finished HTML to the browser.
- *Key Files:*
  - `dashboard.html`: The main hub. Contains logic to show either the Admin Dashboard or the Student Dashboard based on the user's role.
  - `all_users.html`, `reports.html`, `admin_requests.html`: Dedicated pages specifically for the Admin to manage the platform.
  - `upload.html`, `search.html`, `my_resources.html`: Student-facing pages for interacting with the resource hub.

## 3. Static Assets (`/static` folder)
- *Why it's here:* To store raw files that don't need any Python processing.
- *What it does:* Holds uploaded resource images (`/static/uploads`) so the HTML can display them via standard `<img src="...">` tags.

## 4. The Database (`learnandgrow.db`)
- *Why it's here:* This is the actual local SQLite database file where all users, hashes, resources, and updates are physically stored on the hard drive. If this file is deleted, all platform data is lost.
