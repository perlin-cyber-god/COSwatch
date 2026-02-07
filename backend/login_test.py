#login_test.py for login test with "email": "test@test.com","password": "12345678"
from supabase import create_client

SUPABASE_URL = "https://toamgacouwrwtibzbwyo.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InRvYW1nYWNvdXdyd3RpYnpid3lvIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzA0MzMwMzIsImV4cCI6MjA4NjAwOTAzMn0.RF1k9QJG6sL6N1CBwPfHH-Zv0Jou1Lh3202dHolkmL0"

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

res = supabase.auth.sign_in_with_password({
    "email": "test@test.com",
    "password": "12345678"
})

print(res.session.access_token)
