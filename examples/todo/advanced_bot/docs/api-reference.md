# API Reference

## Authentication

All API requests require authentication using an API key:

```
Authorization: Bearer YOUR_API_KEY
```

## Endpoints

### GET /api/users
Retrieve user information

**Parameters:**
- `limit` (optional): Maximum number of users to return
- `offset` (optional): Number of users to skip

**Response:**
```json
{
  "users": [...],
  "total": 100,
  "page": 1
}
```

### POST /api/projects
Create a new project

**Body:**
```json
{
  "name": "My Project",
  "description": "Project description"
}
```