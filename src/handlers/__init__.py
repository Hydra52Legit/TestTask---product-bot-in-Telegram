from .common_handlers import router as common_router
from .card_handlers import router as card_router
from .payment_handlers import router as payment_router
from .balance_handlers import router as balance_router
from .admin_handlers import router as admin_router

__all__ = [
    'common_router',
    'card_router',
    'payment_router',
    'balance_router',
    'admin_router'
]
