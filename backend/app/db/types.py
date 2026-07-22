from sqlalchemy import Uuid as SA_UUID

# Re-export for models that need dialect-friendly UUIDs
Uuid = SA_UUID
