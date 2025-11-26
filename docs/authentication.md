# Authentication

Binbot API uses JWT (JSON Web Token) authentication to protect API endpoints.

## Overview

- **Authentication Method**: JWT tokens with OAuth2 password flow
- **Token Type**: Bearer tokens
- **Library**: `python-jose` for JWT handling, `passlib` with bcrypt for password hashing
- **Token Expiration**: Configurable via `ACCESS_TOKEN_EXPIRE_MINUTES` environment variable (default: 1 year in development)

## Protected Endpoints

All API endpoints require authentication **except**:
- `GET /` - Health check endpoint
- `POST /user/login` - Login endpoint to obtain access token

### Protected Endpoint Categories

The following endpoint groups require authentication:

1. **Bots** (`/bot/*`) - All bot management endpoints
2. **Account** (`/account/*`) - All account and balance endpoints  
3. **Orders** (`/order/*`) - All order management endpoints
4. **Symbols** (`/symbols`, `/symbol/*`) - All symbol/pair management endpoints
5. **Paper Trading** (`/paper-trading/*`) - All paper trading endpoints
6. **Autotrade Settings** (`/autotrade-settings/*`) - All autotrade configuration endpoints
7. **Charts** (`/charts/*`) - All chart and market data endpoints
8. **Asset Index** (`/asset-index/*`) - All asset index management endpoints
9. **User Management** (`/user`, `/user/{email}`, `/user/register`) - User CRUD operations (except login)

## Getting Started

### 1. Obtain an Access Token

To authenticate, first obtain a JWT token by logging in:

**Request:**
```bash
curl -X POST "http://localhost:8008/user/login" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=your-email@example.com&password=yourpassword"
```

**Response:**
```json
{
  "message": "Successfully logged in!",
  "data": {
    "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "token_type": "bearer",
    "expires_in": "2026-01-26 12:00:00"
  },
  "error": 0
}
```

### 2. Use the Token

Include the token in the `Authorization` header for all subsequent requests:

**Request:**
```bash
curl -X GET "http://localhost:8008/bot" \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
```

**Response (Success):**
```json
{
  "message": "Successfully found bots!",
  "data": [...],
  "error": 0
}
```

**Response (No Token/Invalid Token):**
```json
{
  "detail": "Not authenticated"
}
```
HTTP Status: `401 Unauthorized`

## Environment Configuration

The following environment variables configure JWT authentication:

```bash
# Required: Secret key for signing JWT tokens
# Use a strong, random secret in production
SECRET_KEY="your-secret-key-here"

# Token expiration time in minutes
# Default shown is 1 year (525600 minutes)
ACCESS_TOKEN_EXPIRE_MINUTES="525600"
```

⚠️ **Security Warning**: 
- Always use a strong, randomly generated `SECRET_KEY` in production
- Never commit the `SECRET_KEY` to version control
- Consider using shorter token expiration times in production

## User Registration

New users can be registered by authenticated administrators:

**Request:**
```bash
curl -X POST "http://localhost:8008/user/register" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "newuser@example.com",
    "password": "securepassword123",
    "role": "admin",
    "full_name": "New User"
  }'
```

**Response:**
```json
{
  "message": "Added new user!",
  "data": {
    "email": "newuser@example.com",
    "is_active": true,
    "role": "admin",
    "full_name": "New User",
    "created_at": 1234567890
  },
  "error": 0
}
```

## Token Structure

JWT tokens contain the following claims:

```json
{
  "sub": "user@example.com",  // Subject: user's email
  "exp": 1735689600           // Expiration: Unix timestamp
}
```

## Error Handling

### 401 Unauthorized

You'll receive a 401 status code in these scenarios:

1. **No token provided**
   ```json
   {"detail": "Not authenticated"}
   ```

2. **Invalid token format**
   ```json
   {"detail": "Could not validate credentials"}
   ```

3. **Expired token**
   ```json
   {"detail": "Could not validate credentials"}
   ```

4. **Token signature verification failed**
   ```json
   {"detail": "Could not validate credentials"}
   ```

### How to Handle 401 Errors

When your application receives a 401 error:
1. Clear any stored tokens
2. Redirect user to login
3. After successful login, retry the original request with the new token

## Best Practices

### Frontend Integration

**Example using JavaScript fetch:**
```javascript
// Login
async function login(email, password) {
  const formData = new URLSearchParams();
  formData.append('username', email);
  formData.append('password', password);
  
  const response = await fetch('http://localhost:8008/user/login', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/x-www-form-urlencoded',
    },
    body: formData
  });
  
  const data = await response.json();
  
  if (data.error === 0) {
    // Store token (example uses localStorage for simplicity)
    // For production, consider more secure options like httpOnly cookies
    localStorage.setItem('access_token', data.data.access_token);
    return data.data.access_token;
  }
  throw new Error(data.message);
}

// Make authenticated request
async function getBots() {
  const token = localStorage.getItem('access_token');
  
  const response = await fetch('http://localhost:8008/bot', {
    headers: {
      'Authorization': `Bearer ${token}`
    }
  });
  
  if (response.status === 401) {
    // Handle unauthorized - redirect to login
    window.location.href = '/login';
    return;
  }
  
  return await response.json();
}
```

### Python Client Example

```python
import requests

class BinbotClient:
    def __init__(self, base_url="http://localhost:8008"):
        self.base_url = base_url
        self.token = None
    
    def login(self, email, password):
        """Authenticate and store token"""
        response = requests.post(
            f"{self.base_url}/user/login",
            data={"username": email, "password": password}
        )
        response.raise_for_status()
        data = response.json()
        
        if data.get("error") == 0:
            self.token = data["data"]["access_token"]
            return True
        raise Exception(data.get("message", "Login failed"))
    
    def get_headers(self):
        """Get headers with authentication token"""
        if not self.token:
            raise Exception("Not authenticated. Call login() first.")
        return {"Authorization": f"Bearer {self.token}"}
    
    def get_bots(self):
        """Get all bots"""
        response = requests.get(
            f"{self.base_url}/bot",
            headers=self.get_headers()
        )
        response.raise_for_status()
        return response.json()

# Usage
client = BinbotClient()
client.login("user@example.com", "password")
bots = client.get_bots()
```

## Security Considerations

1. **HTTPS in Production**: Always use HTTPS in production to prevent token interception
2. **Token Storage**: 
   - **Web Apps**: The example above uses localStorage for simplicity, but consider these more secure alternatives:
     - **httpOnly cookies**: Most secure for web apps (not accessible via JavaScript)
     - **sessionStorage**: Cleared when tab closes, better than localStorage
     - **In-memory only**: Most secure but lost on page refresh
   - **Mobile Apps**: Use platform-specific secure storage (Keychain, Keystore)
3. **Token Rotation**: Implement token refresh mechanism for long-running sessions
4. **CORS Configuration**: The API currently allows all origins (`allow_origins=["*"]`). Restrict this in production.
5. **Password Requirements**: Enforce strong passwords (min 8 characters as currently configured)

## Testing

Comprehensive authentication tests are available in `tests/test_authentication.py`:

```bash
# Run authentication tests
cd api
uv run pytest tests/test_authentication.py -v
```

The test suite verifies:
- All protected endpoints return 401 without authentication
- Valid tokens allow access to protected endpoints
- Invalid/malformed tokens are rejected
- Login endpoint doesn't require authentication
- Health check endpoint doesn't require authentication

## Implementation Details

### Authentication Flow

1. **Password Storage**: Passwords are hashed using bcrypt before storage
2. **Token Generation**: JWT tokens are signed using HS256 algorithm with the `SECRET_KEY`
3. **Token Validation**: FastAPI dependency `decode_access_token` validates tokens on each request
4. **OAuth2 Scheme**: Uses `OAuth2PasswordBearer` with `tokenUrl="/user/login"`

### Code References

- **Auth Service**: `api/user/services/auth.py` - Core authentication logic
- **User Routes**: `api/user/routes.py` - Login and user management endpoints
- **Protected Routes**: All route files in `api/*/routes.py` use `dependencies=[Depends(decode_access_token)]`

## Troubleshooting

### "Not authenticated" Error

**Cause**: No Authorization header or missing Bearer prefix

**Solution**: Ensure header format is exactly:
```
Authorization: Bearer YOUR_TOKEN_HERE
```

### "Could not validate credentials" Error

**Possible causes**:
1. Token has expired - re-authenticate
2. Token is malformed - check token format
3. Wrong SECRET_KEY - ensure SECRET_KEY environment variable matches between token generation and validation
4. Token signature invalid - token may have been tampered with

**Solution**: Re-authenticate to get a new token

### Token Works Locally But Not in Production

**Cause**: Different `SECRET_KEY` environment variable

**Solution**: Ensure the same `SECRET_KEY` is set in production environment

## API Documentation

Once the API is running, interactive API documentation is available at:

- Swagger UI: `http://localhost:8008/docs`
- ReDoc: `http://localhost:8008/redoc`

Both interfaces include an "Authorize" button where you can enter your bearer token to test authenticated endpoints.
