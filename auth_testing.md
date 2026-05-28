# Auth-Gated App Testing Playbook

## Step 1: Create Test User & Session
```
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
```
curl -X GET "URL/api/auth/me" -H "Authorization: Bearer YOUR_SESSION_TOKEN"
curl -X GET "URL/api/chat/sessions" -H "Authorization: Bearer YOUR_SESSION_TOKEN"
curl -X POST "URL/api/chat/sessions" -H "Authorization: Bearer YOUR_SESSION_TOKEN"
```

## Step 3: Browser Testing
Set the `session_token` cookie via `page.context.add_cookies`, navigate to the app, verify chat works and lists only user's own sessions.

## Checklist
- [ ] users collection has `user_id` (custom UUID)
- [ ] user_sessions.user_id matches user.user_id
- [ ] All queries use `{"_id": 0}` projection
- [ ] /api/auth/me returns user
- [ ] /api/chat/sessions returns only the authed user's sessions
- [ ] No 401/404 on chat endpoints with valid token

## Success / Failure
✅ /api/auth/me → user JSON
✅ Sessions endpoint scoped per user
❌ "User not found"
❌ 401 Unauthorized
