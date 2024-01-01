from .models import StateDataToGet
from .models import StateData
import qrcode
from .models import QRData
import io
from datetime import datetime
from passlib.context import CryptContext
from telebot.types import Message, CallbackQuery

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def welcome_message(message: Message):
    if message.from_user.username:
        return f"""Hello 👋 @{message.from_user.username}
Welcome to TextPay. What would you like to do today?
This is a list of the commands:
/create_wallet - To create a wallet.

/wallet_balance - To know how much you have in your wallet.

/make_payment - To add money into your wallet.

/text_to_other - To text money to another user.

/create_payment_qr - Generate a QR code for accepting payments.

/scan_payment_qr - To scan a QR code for making payment.

/transaction_history - To see your last 10 transaction history.

/cancel - To cancel any thing you are doing.

/purchase_history - To check your purchase history.

/get_my_id - To get your id.

/delete - To Delete your wallet.

/liquidate - To liquidate money into your bank account.

/support - For support information."""
    else:
        return f"""Hello 👋
Welcome to TextPay. What would you like to do today?
This is a list of the commands:
/create_wallet - To create a wallet.

/wallet_balance - To know how much you have in your wallet.

/make_payment - To add money into your wallet.

/text_to_other - To text money to another user.

/create_payment_qr - Generate a QR code for accepting payments.

/scan_payment_qr - To scan a QR code for making payment.

/transaction_history - To see your last 10 transaction history.

/cancel - To cancel any thing you are doing.

/purchase_history - To check your purchase history.

/get_my_id - To get your id.

/delete - To Delete your wallet. We are supposed to refund the money but I haven't implemented that yet.

/support - For support information."""


def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def get_user_id_and_chat_id_from_message_or_call(message: Message | None = None, call: CallbackQuery | None = None):
    if not call:
        return message.from_user.id, message.chat.id
    return call.from_user.id, call.message.chat.id


def get_current_time():
    current_datetime = datetime.now()
    sql_current_datetime_format = current_datetime.strftime(
        "%Y-%m-%d %H:%M:%S")
    return sql_current_datetime_format


def create_qr(qr_data: QRData):
    qr = qrcode.QRCode(
        version=2,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=2
    )
    qr.add_data(f"{qr_data.user_id}:{qr_data.amount_to_charge}:{qr_data.qr_id}")
    qr_img = qr.make_image(back_color="white", fill_color='black')

    # We create a io.BytesIO buffer to store the QR code image in memory without saving it as a file.
    buffer = io.BytesIO()
    # The QR code is generated and saved to the buffer as a PNG image.
    qr_img.save(buffer, format='PNG')
    buffer.seek(0)
    return buffer


def update_state_data(existing_state_data: StateData, update_state_data: StateData):
    update_state_data: dict = update_state_data.model_dump(exclude_unset=True)
    for key, val in update_state_data.items():
        setattr(existing_state_data, key, val)
    return existing_state_data


def get_state_data(existing_state_data: StateData, state_data_to_get: StateDataToGet):
    state_data_to_get: dict = state_data_to_get.model_dump(exclude_unset=True)
    state_data_to_return = StateData()
    for key, val in state_data_to_get.items():
        setattr(state_data_to_return, key, getattr(existing_state_data, key))
    return state_data_to_return
