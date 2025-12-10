from aiogram.fsm.state import State, StatesGroup

class CardCreationStates(StatesGroup):
    waiting_for_title = State()
    waiting_for_description = State()
    waiting_for_price = State()
    waiting_for_photo = State()

class BalanceStates(StatesGroup):
    waiting_for_withdrawal_amount = State()
    waiting_for_withdrawal_requisites = State()

class AdminStates(StatesGroup):
    editing_card = State()
    waiting_for_new_value = State()