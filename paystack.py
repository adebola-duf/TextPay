import os
from dotenv import load_dotenv
import requests
import json
import os
import hmac
import hashlib

from fastapi import BackgroundTasks, FastAPI
from fastapi import FastAPI, HTTPException, Request, status, BackgroundTasks
from fastapi.responses import JSONResponse

from app.utils import get_current_time
from app.crud import get_transactions

load_dotenv(".env")

app = FastAPI()
secret = bytes(os.getenv("PAYSTACK_SECRET_KEY"), 'UTF-8')

load_dotenv(".env")

app = FastAPI()


def handle_webhook_stuff_on_my_end(event):
    # The second part after the and prolly doesn't matter because they only send the event after a successful charge.
    if event["event"] == "charge.success" and event["data"]["status"] == "success":
        metadata: str = event["data"]["metadata"]
        index_of_first_opening_square_bracket_in_metadata: int = metadata.index(
            "[")
        index_of_first_closing_square_bracket_in_metadata: int = metadata.index(
            "]")
        custom_fields_string: str = metadata[index_of_first_opening_square_bracket_in_metadata: (
            index_of_first_closing_square_bracket_in_metadata + 1)]
        # this gets the first dictionary in like the lemme call it string list. So even though we have multiple custom fields, for now, we still just want to get the first one.
        custom_fields_dict: dict = json.loads(custom_fields_string)[0]
        # handle the case where the user puts in a non convertible to integer stuff instead of their user_id
        enterd_user_id = custom_fields_dict["value"]

        amount_without_paystack_charge = event["data"]["amount"] / 100
        first_name = event["data"]["customer"]["first_name"]
        last_name = event["data"]["customer"]["last_name"]
        paystack_charge = event["data"]["fees"] / 100
        amount_with_paystack_charge = amount_without_paystack_charge - paystack_charge
        paystack_payment_reference = event["data"]["eference"]
        if event["data"]["domain"] == "live":
            transaction = get_transactions(
                paystack_transaction_reference=paystack_payment_reference)
            if transaction:
                return

            # if the that payment reference doesn't exist
            message = f"You have just added ₦ {amount_without_paystack_charge} into your wallet, ₦{paystack_charge} was deducted as charges. So you paid ₦{amount_with_paystack_charge} into your wallet. Thanks for texting with us 👍😉."
            data = {
                "user_id": enterd_user_id,
                "message": message,
                "amount": str(amount_with_paystack_charge),
                "operation": "add_to_wallet",  # could be anything
                "paystack_payment_reference": paystack_payment_reference,
                "time_of_payment": get_current_time()
            }
            response = requests.post(f"https://textpay.onrender.com/send-notification-to-user",
                                     json=data, headers={"Authorization": f"Bearer {os.getenv('NOTIFICATION_TOKEN')}"})
            # if response.status_code == 404:
            #     print(response.json()["detail"])
            # elif response.status_code == 401:
            #     print(response.json()["detail"])
            # elif response.status_code == 200:
            #     print(
            #         f"successful payment of ₦{amount_without_paystack_charge} by {first_name} {last_name}, user id: {enterd_user_id}. A fee of ₦{paystack_charge} was deducted. So you have just paid ₦{amount_with_paystack_charge}")
            #     print(response.content.decode("utf-8"))
            # return

        print(event)
        # maybe you should send this message to my telegram using maybe notify bot
        print(
            f"Adebola user id: {enterd_user_id} just tried to use the test payment page. Maybe you should send them a warning message.")

    # i don't think paystack sends events when the transation fails so imma comment this out
    # else:
    #     print("failed payment.")


@app.post(path="/paystack-webhook")
async def receive_webhook(request: Request, background_tasks: BackgroundTasks):
    try:
        body = await request.body()
        signature = request.headers['x-paystack-signature']

        hash = hmac.new(secret, body, hashlib.sha512).hexdigest()

        if hash == signature:
            event = await request.json()
            background_tasks.add_task(handle_webhook_stuff_on_my_end, event)
            response_content = {"message": "Webhook received and acknowledged"}
            return JSONResponse(content=response_content, status_code=200)

        else:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid webhoook signature.")

    except Exception as e:
        if isinstance(e, HTTPException):
            pass
        else:
            print(f"An exception occurred: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"An exception occurred: {e}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0")
