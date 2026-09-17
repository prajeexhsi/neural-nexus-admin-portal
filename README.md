# Neural Nexus Administrative & Staff Portal

A clean Flask-based internal portal for Neural Nexus.

## Stack

- Flask
- Supabase PostgreSQL
- Vercel
- HTML/CSS/JavaScript
- Supabase Python client

Django is not used.

## Modules

- Dashboard
- Students
- Projects
- Payments
- Staff
- Reports
- Search and status filters
- Project workflow
- Revenue / collected / outstanding calculations
- GitHub and Drive project links
- Responsive dark Neural Nexus UI

## Local setup

PowerShell:

```powershell
cd neural_nexus_admin_portal_flask
py -3.14 -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
python app.py
```

Open:

`http://127.0.0.1:8000`

Default demo login:

- Username: `admin`
- Password: `Neural@123`

Change these in `.env` before using the portal for real data.

## Supabase setup

1. Create a Supabase project.
2. Open SQL Editor.
3. Run `database/schema.sql`.
4. Copy the project URL and server-side service role key into `.env`.
5. Never expose the service role key in frontend JavaScript.
6. Restart Flask.

When both `SUPABASE_URL` and `SUPABASE_SERVICE_ROLE_KEY` are present, the portal uses Supabase. Without them, it runs in local demo mode using SQLite.

## Vercel deployment

Import the GitHub repository into Vercel.

Add these environment variables in Vercel:

- `FLASK_SECRET_KEY`
- `ADMIN_USERNAME`
- `ADMIN_PASSWORD`
- `SUPABASE_URL`
- `SUPABASE_SERVICE_ROLE_KEY`

Then deploy.

## Important security notes

- Use a long random `FLASK_SECRET_KEY`.
- Use a strong admin password.
- Keep the Supabase service role key private.
- This starter uses server-side authentication with environment credentials.
- For a larger multi-user deployment, move authentication to Supabase Auth and add role-based access control.

## Brand

The supplied Neural Nexus artwork is preserved at:

`static/images/neural-nexus-brand.jpg`

The UI uses the artwork's dark navy / electric blue / cyan visual language.
