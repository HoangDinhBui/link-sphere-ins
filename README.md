# LinkSphere - Backend API 🌐

This is the backend API for **LinkSphere** - a mini social network where people can connect, share posts, and interact with each other. The project is built entirely with **Django** & **Django REST Framework (DRF)**.

## 🚀 Features

The system is divided into smaller apps to keep things modular and easy to maintain:

*   **Users & Auth (`apps.users`)**: Registration, login (using JWT Tokens), and profile viewing. Also includes Follow / Unfollow functionality.
*   **Posts (`apps.posts`)**: Create new posts and view post lists. Supports Liking / Unliking posts.
*   **Comments (`apps.comments`)**: Comment on other people's posts.
*   **Feed (`apps.feed`)**: The newsfeed. Divided into 2 types:
    *   `Feed`: Only shows posts from people you follow.
    *   `Explore`: Shows all posts (for discovering new content).
*   **Notifications (`apps.notifications`)**: Automatically triggers notifications when someone likes your post, comments, or follows you. Includes an API to mark them as read.
*   **Search (`apps.search`)**: Search for Users and Posts.

## ☁️ Cloud & External APIs Integration (In Development)

To adhere to modern Web application standards and enterprise requirements, LinkSphere integrates with external Cloud Services:

*   **Cloudinary**: Solves the static and media file storage problem (Cloud Infrastructure). It is used for handling image uploads (Avatars, Post images) directly to the cloud, which is a mandatory standard for modern scalable Web applications.
*   **Resend (Email API)**: Handles user interaction workflows. This perfectly fulfills the requirement of "calling a 3rd-party API" by sending automated welcome and verification emails when a user interacts with the system (e.g., during Registration).

## 📦 Standardized API Response

This project is set up with a custom Response & Exception Handler. Whether it's a success (200), an error (400, 404), or paginated data, everything returned to the Frontend is wrapped in a consistent, standardized format:

**Success Response:**
```json
{
    "success": true,
    "message": "User registered successfully",
    "data": {
        "id": 1,
        "username": "diep"
    },
    "timestamp": "2026-05-23T10:00:00Z"
}
```

**Error Response (with field validation errors):**
```json
{
    "success": false,
    "message": "Validation failed",
    "errors": [
        {
            "field": "username",
            "message": "This username already exists."
        }
    ],
    "errorCode": "VALIDATION_ERROR",
    "timestamp": "2026-05-23T10:00:00Z"
}
```

## 🛠 Local Setup Guide

1. Clone the repo.
2. Create and activate a virtual environment:
   ```bash
   python -m venv venv
   # On Windows:
   venv\Scripts\activate
   ```
3. Install the required dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Run migrations to set up the database:
   ```bash
   python manage.py migrate
   ```
5. Start the development server:
   ```bash
   python manage.py runserver
   ```
   The server will be running at: `http://localhost:8000`

## 🧪 Testing

The project uses `pytest` for API testing. To run the tests, simply execute:
```bash
pytest
```
Test files are located in the `tests.py` of each respective app. They cover all core flows (Auth, Feed, Post, User).
