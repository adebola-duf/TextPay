from typing import Annotated, Optional
from sqlmodel import Session, select
from .models import User_Wallet, QR_Info, Transaction, User_WalletUpdate, QR_InfoUpdate
from .database import engine


def get_user_wallet(user_id: int = None, username: str = None) -> Optional[User_Wallet]:
    if not user_id and not username:
        return None
    with Session(engine) as session:
        if user_id:
            user = session.get(User_Wallet, user_id)
        else:
            user = session.exec(select(User_Wallet).where(
                User_Wallet.username == username)).first()
        if user:
            return user
    return None


def create_user_wallet(user_wallet: User_Wallet):
    with Session(engine) as session:
        session.add(user_wallet)
        session.commit()
        session.refresh(user_wallet)
        return user_wallet


def delete_user_wallet(user_id: int):
    with Session(engine) as session:
        transactions = get_transactions(sender_id=user_id)
        for transaction in transactions:
            session.delete(transaction)
        qrs = get_qr_info(user_id=user_id)
        for qr in qrs:
            session.delete(qr)
        user_wallet = get_user_wallet(user_id)
        # i think there is a better way to do this by doing something called cascading. IDK sha
        session.delete(user_wallet)
        session.commit()


# I am thinking of creating transactions everytime we update wallet balance
def update_user_wallet(user_id: Optional[int] = None, update_data: Optional[User_WalletUpdate] = None, transaction: Optional[Transaction] = None):
    if update_data:
        update_data: dict = update_data.model_dump(exclude_unset=True)
    with Session(engine) as session:
        if transaction:
            sender = session.get(User_Wallet, transaction.sender_id)
            if transaction.type_transaction == "transfer":
                receiver = session.get(User_Wallet, transaction.receiver_id)
                receiver.wallet_balance += transaction.amount_transferred
                sender.wallet_balance -= transaction.amount_transferred
                session.add(receiver)
                session.add(sender)
                session.add(transaction)
                session.commit()
                session.refresh(sender)
                session.refresh(receiver)
                return [sender, receiver]
            elif transaction.type_transaction == "liquidate":
                sender.wallet_balance -= transaction.amount_transferred
            elif transaction.type_transaction == "paystack_payment":
                sender.wallet_balance += transaction.amount_transferred
            session.add(sender)
            session.add(transaction)
            session.commit()
            session.refresh(sender)
            return sender
        else:
            user_wallet = get_user_wallet(user_id=user_id)
            # If we are updating stuffs other than the wallet balance
            for key, value in update_data.items():
                setattr(user_wallet, key, value)
            session.add(user_wallet)
            session.commit()
            session.refresh(user_wallet)
            return user_wallet


def create_transaction(transaction: Transaction):
    with Session(engine) as session:
        session.add(transaction)
        session.commit()
        session.refresh(transaction)
        return transaction


def get_transactions(sender_id: int | None = None, paystack_transaction_reference: str | None = None, receiver_id: int | None = None) -> list[Transaction]:
    if not sender_id and not paystack_transaction_reference:
        return None
    with Session(engine) as session:
        if sender_id:
            return session.get(User_Wallet, sender_id).transactions
        elif receiver_id:
            return session.exec(select(Transaction).where(Transaction.receiver_id == sender_id)).all()
        elif paystack_transaction_reference:
            return session.exec(select(Transaction).where(Transaction.paystack_transaction_reference == paystack_transaction_reference)).one()

    return None


def get_qr_info(user_id: int, qr_id: int | None = None) -> list[QR_Info] | QR_Info:
    with Session(engine) as session:
        if not qr_id:  # we want to return all the qrs associated with a particular user
            return session.exec(select(QR_Info).where(QR_Info.user_id == user_id)).all()
        return session.exec(select(QR_Info).where(QR_Info.user_id == user_id, QR_Info.qr_id == qr_id)).first()


def create_qr_info(qr_info: QR_Info):
    with Session(engine) as session:
        session.add(qr_info)
        session.commit()


def update_qr_info(qr_info: QR_InfoUpdate):
    # Baba check if we have confirmed that the user exists before calling the update_qr_info function
    with Session(engine) as session:
        qr = session.exec(select(QR_Info).where(
            QR_Info.user_id == qr_info.user_id, QR_Info.qr_id == qr_info.qr_id)).one()
        qr.qr_used = qr_info.qr_used
        session.add(qr)
        session.commit()
