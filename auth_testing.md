# Auth-Gated App Testing Playbook

## Step 1: Create Test User & Session via MongoDB

```bash
mongosh --eval "
use('test_database');
var userId = 'test-user-' + Date.now();
var sessionToken = 'test_session_' + Date.now();
db.users.insertOne({
  user_id: userId,
  email: 'test.user.' + Date.now() + '@example.com',
  name: 'Test User',
  picture: 'https://via.placeholder.com/150',
  created_at: new Date()
});
db.user_sessions.insertOne({
  user_id: userId,
  session_token: sessionToken,
  expires_at: new Date(Date.now() + 7*24*60*60*1000),
  created_at: new Date()
});
print('Session token: ' + sessionToken);
print('User ID: ' + userId);
"
```

## Step 2: Test Backend API

```bash
# Auth endpoint
curl -X GET "https://your-app.com/api/auth/me" \
  -H "Authorization: Bearer YOUR_SESSION_TOKEN"

# Protected endpoints
curl -X GET "https://your-app.com/api/caos/sessions" \
  -H "Authorization: Bearer YOUR_SESSION_TOKEN"
```

## Step 3: Browser Testing

```python
await page.context.add_cookies([{
    "name": "session_token",
    "value": "YOUR_SESSION_TOKEN",
    "domain": "your-app.com",
    "path": "/",
    "httpOnly": True,
    "secure": True,
    "sameSite": "None"
}])
await page.goto("https://your-app.com")
```

## Success Indicators
- ✅ `/api/auth/me` returns user data
- ✅ Dashboard loads without redirect
- ✅ CRUD operations work with session token

## Failure Indicators
- ❌ "User not found" errors
- ❌ 401 Unauthorized responses
- ❌ Redirect to login page

## Key Rules
- User document has `user_id` field (custom UUID, separate from MongoDB `_id`)
- Session `user_id` matches user's `user_id` exactly
- All queries use `{"_id": 0}` projection
- Backend queries use `user_id` (not `_id` or `id`)
- Frontend uses `window.location.origin` for redirect, NEVER hardcode
