# Frontend Architecture (templates/ & static/)

This file explains the frontend code structure of the Learn & Grow application.

## 1. Directory Structure
The frontend code is split into logical folders inside the 	emplates/ directory to keep everything organized.
- **admin/**: Contains all the HTML pages exclusively used by Administrators (e.g., admin dashboard, user management).
- **users/**: Contains all the HTML pages used by regular students and users (e.g., search, upload, requests, rewards).
- **shared/**: Contains pages that both admins and users share (e.g., login, global chat, profile viewing).

## 2. Technologies Used
- **HTML & Jinja2:** The pages are written in HTML. Jinja2 syntax (like {{ user.name }}) is used to inject real-time data from the backend into the page before it is sent to the browser.
- **Tailwind CSS:** All styling, colors, and layouts are handled by Tailwind CSS directly within the class attributes of the HTML elements.
- **JavaScript:** Native vanilla JS is used at the bottom of pages like chat.html and riends.html to handle live updates (polling), interactive modals, and image previews without needing to reload the page.
- **Flatpickr:** Used for clean date and time selection inputs on forms.
