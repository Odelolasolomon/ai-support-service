
from sys import flags
import os 
import re 

from openai import OpenAI

from app.knowledge import (search_knowledge, get_order_status)

def classify_intent(message: str):
    text= message.lower()

    if "ord_" in text:
        return "order_status"

    if any(word in text for word in ["refund", "delivery", "password"]):
        return "knowledge_question"

    return " unknown_intent"



def extract_order_id(message: str):
    match = re.search (r"\bORD_\d+\b", message, flags=re.IGNORECASE)


    if match:
        return match.group().upper()
    return None 


def generate_answer(message:str, context: str):

    client= OpenAI(
        api_key=os.getenv("open_api_key"),
        timeout=8.0,
        max_retries=0
    )


    response = client.chat.completions.create(
        model= os.getenv(
            "open_ai_model",
            "gpt-4o-mini"
        ),

        messages= [
            {
                "role": "system",
                "content": (
                    "you are a customersupport assistant. "
                    "Answer only using the supplied grounded information "
                    "Don not provide information when you are not sure and do not leak customers provider info"

                )

            },

            {

            "role": "user",
            "content": (
                f"context: {context}\n"
                f"Question: {message}"

            )

        }


        ],
        temperature=0,
        max_tokens=100

    )

    return ( 
        response.choices[0].message.content or ""

    ).strip()


def handle_message(customer_id: str, message: str):
    intent = classify_intent(message) 

    if intent == "order_status":
        order_id = extract_order_id(message)
        if not order_id:
            return escalate(intent)

        status = get_order_status(order_id, customer_id)
        if status is None:
            return escalate(intent)

        return {
            "intent": intent,
            "answer": f"Your order {order_id} is currently {status}.",
            "escalate": False
        }

    elif intent == "knowledge_question":
        context = search_knowledge(message)
        if context is None:
            return escalate(intent)

        try:
            answer = generate_answer(message, context)
        except Exception:
            return escalate(intent)

        if not answer or "escalate" in answer.lower():
            return escalate(intent)

        return {
            "intent": intent,
            "answer": answer,
            "escalate": False
        }

    return escalate(intent)



def escalate(intent: str):
    return {
        "intent": intent, 
        "answer": (
            "I cannot give a very reliable answer or resolve to this request. "
            "I will refer it to a human support agent."
            
        ),
        "escalate": True  
    }

            




