"""
Services
"""
from app.services.encryption import encrypt_data, decrypt_data, EncryptionService

# TDengine client lib may be missing in some runtime images (e.g., celery-beat).
# Import it lazily to avoid hard crash.
try:
    from app.services.tdengine import TDengineService, tdengine_service
except Exception:  # noqa: S110
    TDengineService = None
    tdengine_service = None

# AI optimizers (optional)
try:
    from app.services.ai.dqn_optimizer import DQNPublisher, ReplayBuffer
    from app.services.ai.ga_optimizer import GAPublisher
except Exception:  # noqa: S110
    DQNPublisher = None
    ReplayBuffer = None
    GAPublisher = None

__all__ = [
    'encrypt_data',
    'decrypt_data', 
    'EncryptionService',
    'TDengineService',
    'tdengine_service',
    'DQNPublisher',
    'ReplayBuffer',
    'GAPublisher'
]