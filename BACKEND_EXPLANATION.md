# Backend Architecture (main.py, models.py, database.py)

This file explains the backend code structure of the Learn & Grow application.

## 1. Database (database.py & models.py)
The database is built using SQLAlchemy and SQLite (learnandgrow.db).
- **database.py:** Contains the connection logic to link the Python application to the SQLite file.
- **models.py:** Defines the database tables (e.g., User, Resource, ItemRequest, ChatMessage, PrivateMessage). Each class here corresponds to a table in the database where information is stored permanently.

## 2. Server Configuration (main.py)
main.py is the heart of the application. It uses FastAPI to route web traffic.
- **Static Files:** The /static folder is mounted to serve images, CSS, and user uploads.
- **Templates:** Jinja2 is used to render the HTML pages located in the /templates folder.

## 3. Core Logic & Routing (main.py)
The backend uses @app.get and @app.post to handle user requests:
- **Authentication:** Handles user login, signup, and session management using cookies.
- **Admin Panel:** Routes starting with /admin allow administrators to view metrics and manage users.
- **User Dashboard:** Routes like /dashboard and /search allow users to explore resources.
- **Chat System:** Routes like /api/chat and /api/private-chat handle live messaging and file uploads.
- **Auto-Cleanup:** The uto_delete_expired function automatically removes events and requests that have passed their deadline.
