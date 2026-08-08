# ==========================================
# Frontend & URLs
# ==========================================
DEFAULT_FRONTEND_ORIGIN = "http://localhost:3000"

# Default redirect URIs
DEFAULT_API_V1_REDIRECT_URI_TEMPLATE = "http://localhost:8000/api/v1/auth/{provider}/callback"
DEFAULT_API_REDIRECT_URI_TEMPLATE = "http://localhost:8000/api/auth/{provider}/callback"

# Integration callbacks
INTEGRATION_DASHBOARD_SUCCESS_URL = f"{DEFAULT_FRONTEND_ORIGIN}/dashboard?integration_success={{provider}}"
INTEGRATION_V1_CALLBACK_URL = "http://localhost:8000/api/v1/workspaces/integrations/{provider}/callback"

# OAuth URLs
# GitHub
GITHUB_AUTHORIZE_URL = "https://github.com/login/oauth/authorize"
GITHUB_ACCESS_TOKEN_URL = "https://github.com/login/oauth/access_token"
GITHUB_USER_INFO_URL = "https://api.github.com/user"
GITHUB_USER_EMAILS_URL = "https://api.github.com/user/emails"

# Google
GOOGLE_AUTHORIZE_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_USER_INFO_URL = "https://www.googleapis.com/oauth2/v3/userinfo"

# Slack
SLACK_AUTHORIZE_URL = "https://slack.com/oauth/v2/authorize"
SLACK_ACCESS_TOKEN_URL = "https://slack.com/api/oauth.v2.access"
SLACK_USER_IDENTITY_URL = "https://slack.com/api/users.identity"

# ==========================================
# Database & Redis Defaults
# ==========================================
DEFAULT_DATABASE_URL = "postgresql+asyncpg://atlas:atlas_secure_pass@localhost:5432/atlas_dev"
DEFAULT_DATABASE_SYNC_URL = "postgresql://atlas:atlas_secure_pass@localhost:5432/atlas_dev"
DEFAULT_REDIS_URL = "redis://localhost:6379/0"

# ==========================================
# JWT & Security Tokens
# ==========================================
JWT_ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 15
REFRESH_TOKEN_EXPIRE_DAYS = 7

# ==========================================
# Memory Manager Limits
# ==========================================
MEMORY_LIMIT_PREFERENCES = 2
MEMORY_LIMIT_TOOL_RESULTS = 1
MEMORY_LIMIT_SUMMARIES = 2
MEMORY_LIMIT_ENTITIES = 10
MEMORY_MIN_MEANINGFUL_LEN = 8

# ==========================================
# Utilities
# ==========================================
DEFAULT_ERROR_MESSAGE = "I hit an unexpected snag."
