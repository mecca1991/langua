# Langua Frontend

Next.js 14 frontend for Langua, a voice-first Japanese language learning app with AI-powered conversation practice and quiz modes.

## Prerequisites

- Node.js 18+
- The Langua backend API running (default: `http://localhost:8000`)
- A Supabase project configured for authentication
- Docker Compose running Postgres and Redis (for the backend)

## Environment Variables

Create a `.env` file in this directory:

```env
NEXT_PUBLIC_SUPABASE_URL=https://your-project.supabase.co
NEXT_PUBLIC_SUPABASE_PUBLISHABLE_DEFAULT_KEY=sb_publishable_...
NEXT_PUBLIC_API_URL=http://localhost:8000
```

| Variable | Description |
|---|---|
| `NEXT_PUBLIC_SUPABASE_URL` | Your Supabase project URL |
| `NEXT_PUBLIC_SUPABASE_PUBLISHABLE_DEFAULT_KEY` | Supabase publishable (anon) key |
| `NEXT_PUBLIC_API_URL` | Backend API base URL (default: `http://localhost:8000`) |

## Supabase Configuration

In your Supabase dashboard under **Authentication > URL Configuration**:

- **Site URL**: `http://localhost:3000`
- **Redirect URLs**: `http://localhost:3000/auth/callback`

Under **Authentication > Providers**, enable:
- Google OAuth
- GitHub OAuth

Both providers should use `http://localhost:3000/auth/callback` as the redirect URI.

## Local Development

```bash
# Install dependencies
npm install

# Start dev server
npm run dev
```

The app runs at `http://localhost:3000`.

Ensure the backend is running at the URL specified by `NEXT_PUBLIC_API_URL`. The backend requires its own environment variables (Supabase JWT secret, OpenAI/Anthropic API keys). See the root `.env.example` for the full list.

## Scripts

| Command | Description |
|---|---|
| `npm run dev` | Start development server |
| `npm run build` | Production build (includes lint + typecheck) |
| `npm run lint` | Run ESLint |
| `npm test` | Run tests with Vitest |

## Auth Flow

1. **Sign-in** (`/sign-in`) — user clicks Google or GitHub OAuth button
2. **Supabase OAuth** — browser redirects to the provider, then back to `/auth/callback`
3. **Callback** (`/auth/callback`) — exchanges the OAuth code or hash tokens for a Supabase session
4. **Redirect** — on success, navigates to the `returnTo` path (default `/`); on failure, back to `/sign-in?error=auth_callback_failed`
5. **AuthProvider** — a single React context (`AuthProvider` in root layout) owns the Supabase auth listener and provides `user`/`session` to all components via `useAuth()`
6. **AuthGuard** — the `(protected)` route group layout wraps children in `AuthGuard`, which redirects unauthenticated users to `/sign-in?returnTo=<current-path>`
7. **Sign-out** — calls `supabase.auth.signOut()` then navigates to `/sign-in` via full page load

## Project Structure

```
src/
  app/
    layout.tsx              Root layout (AuthProvider)
    sign-in/page.tsx        Sign-in page
    auth/callback/page.tsx  OAuth callback handler
    (protected)/
      layout.tsx            AuthGuard wrapper
      page.tsx              Home / session start
      conversation/[sessionId]/page.tsx
      results/[sessionId]/page.tsx
      sessions/page.tsx
      sessions/[sessionId]/page.tsx
  components/               Shared UI components
  contexts/                 React contexts (AuthContext)
  hooks/                    Custom hooks (useAuth, useRecorder, useApiQuery)
  lib/                      Utilities (API client, config, auth routing)
```

## Backend Dependencies

The frontend expects these backend endpoints:

| Endpoint | Used by |
|---|---|
| `GET /topics?language=ja` | Home page — topic list |
| `POST /conversation/start` | Home page — start session |
| `POST /conversation/turn` | Conversation page — submit audio turn |
| `POST /conversation/end` | Conversation page — end session |
| `GET /sessions` | Session history list |
| `GET /sessions/:id` | Session detail, conversation hydration, results |
| `GET /sessions/:id/feedback-status` | Results page — polling |
| `POST /sessions/:id/retry-feedback` | Results page — retry failed feedback |

All endpoints except `/auth/callback` (handled by Supabase) require a `Bearer` token from the Supabase session in the `Authorization` header. The backend verifies this using the Supabase JWT secret.
