# Platform Super Admin setup

1. Copy `.env.example` to `.env` if needed.
2. Set `PLATFORM_ADMIN_EMAIL` and `PLATFORM_ADMIN_PASSWORD` in `.env`.
3. Run `docker compose down` then `docker compose up --build`.
4. Alembic applies migration `0004`; API startup creates the platform user once if it does not exist.
5. Open `http://localhost:5173/login` and sign in with the platform credentials.
6. Platform users are redirected to `http://localhost:5173/platform`.
7. Approve a pending tenant request. The UI shows the initial tenant-admin email and temporary password.
8. Sign out, then sign in with the tenant-admin credentials. Tenant admins are redirected to `/app/workspaces` and can manage their tenant from Team.

Security note: for production, bootstrap the first platform user from a secret manager/one-time command and remove the plaintext bootstrap password from runtime environment after creation. The temporary tenant password response is demo-only and should become an invite/reset flow before production.
