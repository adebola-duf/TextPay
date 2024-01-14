from sqlmodel import SQLModel, Field, Relationship
from datetime import datetime
from telebot.handler_backends import State, StatesGroup  # states
from decimal import Decimal
from typing import Any, Annotated
from pydantic import model_validator, BaseModel


class BaseUser_Wallet(SQLModel):
    username: str = Field(max_length=40, index=True, default=None)
    first_name: str = Field(max_length=40)
    last_name: str = Field(max_length=40)


class User_WalletCreate(BaseUser_Wallet):
    user_id: int
    transaction_password: str


class User_WalletRead(BaseUser_Wallet):
    user_id: int
    wallet_balance: Decimal
    wallet_creation_date: datetime


class User_Wallet(BaseUser_Wallet, table=True):
    user_id: int = Field(primary_key=True)
    transaction_password: str
    wallet_balance: Decimal = Decimal(0)
    wallet_creation_date: datetime = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    transactions: list["Transaction"] = Relationship(back_populates="user")
    qrs: list["QR_Info"] = Relationship(back_populates="user")


class User_WalletUpdate(BaseUser_Wallet):
    username: str | None = Field(max_length=40, index=True, default=None)
    first_name: str | None = Field(max_length=40, default=None)
    last_name: str | None = Field(max_length=40, default=None)
    transaction_password: str | None = None

    # i put before here so that if it passes this test, it still has to go through pydantic's test and if it fails that one. Then error
    @model_validator(mode="before")
    @classmethod
    def check_if_we_are_updating_wallet_balance(cls, data: Any) -> Any:
        amount_to_update_wallet_balance = data["amount_to_update_wallet_balance"]
        add_amount = data["add_amount"]
        if amount_to_update_wallet_balance and add_amount == None:
            raise ValueError(
                "You didn't indicate whether amount should be added or subtracted from user wallet")
        return data


class StateData(SQLModel):
    receiver_id: int | None = None
    receiver_first_name: str | None = None
    receiver_last_name: str | None = None
    receiver_wallet_balance: Decimal | None = None
    receiver_username: str | None = None
    wallet_balance: Decimal = None
    username: str | None = Field(max_length=40, index=True, default=None)
    first_name: str | None = Field(max_length=40, default=None)
    last_name: str | None = Field(max_length=40, default=None)
    transaction_password: str | None = None
    no_trials_left: int | None = None
    is_receiver_id: bool | None = None
    charger_id: int | None = None
    amount_to_charge: Decimal | None = None
    qr_id: int | None = None
    charger_first_name: str | None = None
    charger_last_name: str | None = None
    amount_to_liquidate: Decimal | None = None
    account_number: int | None = None
    bank_name: str | None = None


class StateDataToGet(SQLModel):
    receiver_id: bool | None = None
    receiver_first_name: bool | None = None
    receiver_last_name: bool | None = None
    receiver_wallet_balance: bool | None = None
    receiver_username: bool | None = None
    wallet_balance: bool = None
    username: bool | None = Field(index=True, default=None)
    first_name: bool | None = Field(default=None)
    last_name: bool | None = Field(default=None)
    transaction_password: bool | None = None
    no_trials_left: bool | None = None
    is_receiver_id: bool | None = None
    charger_id: bool | None = None
    amount_to_charge: bool | None = None
    qr_id: bool | None = None
    charger_first_name: bool | None = None
    charger_last_name: bool | None = None
    amount_to_liquidate: bool | None = None
    account_number: bool | None = None
    bank_name: bool | None = None

# This one would be the one we use for validation because the table = true one doesn't do any forms of data validation for us.
# I on't know if i should it for the remaining models. OR i should just remove it. But  remember that when you make anything table=True, there is no data validation
# class TransactionBase(SQLModel):


class BaseTransaction(SQLModel):
    transaction_id: Annotated[int | None, "It is None because in the db we put BIGSERIAL. So the db inputs values for us automtically"] = Field(
        primary_key=True, default=None)
    receiver_id: int | None = None
    time_of_transaction: datetime
    amount_transferred: Decimal
    paystack_transaction_reference: str | None = None
    sender_id: int = Field(foreign_key="user_wallet.user_id")
    acct_number_liquidated_to: int | None = None
    bank_acct_number_belongs_to: str | None = None
    # check if you can use an enum class for this type_transaction
    type_transaction: str

# import enum
# class TypeTrnsaction(enum):
#     transfer,


class Transaction(BaseTransaction, table=True):
    user: User_Wallet = Relationship(back_populates="transactions")


class TransactionRead(BaseTransaction):
    pass


class QR_Info(SQLModel, table=True):
    user_id: int = Field(foreign_key="user_wallet.user_id", primary_key=True)
    qr_id: int = Field(primary_key=True, default=None)
    qr_used: bool = False
    reverse_qr: Annotated[bool,
                          "if set to True, you scan to receive rather than to pay"] = False
    user: User_Wallet = Relationship(back_populates="qrs")


class QR_InfoUpdate(SQLModel):
    user_id: int
    qr_id: int
    qr_used: bool = True

# This one is what is needed to create a qr. HAs nothing to do with the database


class QRData(BaseModel):
    user_id: int
    amount_to_charge: Decimal
    qr_id: int


class UserDetails(BaseModel):
    user_id: int
    amount: Decimal


class NotificationData(BaseModel):
    chat_id: int = None
    user_id: int
    message: str
    operation: str = None
    authentication_token: str
    amount: Decimal
    paystack_payment_reference: str
    time_of_payment: str


class MyStates(StatesGroup):
    # Each attribute in the class represents a different state: first_name, last_name
    xontinue = State()
    first_name = State()
    last_name = State()
    password = State()
    registration_info_given = State()
    # i know some of these variable names are wack but like i've got no better thing
    user_wanna_delete = State()
    delete_confirmation = State()
    password_for_delete = State()
    password_for_text_to_other = State()
    receiver_id_for_text_to_other = State()
    actual_send_to_other_state = State()
    # this is the state for when you want to create a qr
    enter_amount_to_charge_for_create_qr_state = State()

    # this is the state for when you want to scan a qr
    qr_scanned = State()
    qr_text_confirmation = State()
    password_for_qr_scan = State()

    liquidate_enter_password = State()
    liquidate_enter_amount_to_liquidate = State()
    liquidate_enter_account_number = State()
    liquidate_enter_bank_name = State()
