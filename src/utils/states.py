from aiogram.fsm.state import State, StatesGroup

class CardCreationStates(StatesGroup):
    """Состояния для создания карточки"""
    waiting_for_title = State()
    waiting_for_description = State()
    waiting_for_price = State()
    waiting_for_photo = State()

class BalanceStates(StatesGroup):
    """Состояния для работы с балансом"""
    waiting_for_withdrawal_amount = State()
    waiting_for_withdrawal_requisites = State()

class AdminStates(StatesGroup):
    """Состояния для админки"""
    editing_card_attribute = State()
    waiting_for_new_value = State()

class PaymentStates(StatesGroup):
    """Состояния для платежей"""
    waiting_for_payment_confirmation = State()