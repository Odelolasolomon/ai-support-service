FAQS= {

    "refunds": (
        "Customers refunds should be implemented withing 14 business days"
        "ensuring smooth and clear processing and info off hand"

    ),

    "delivery":(
        "all customers orders should be delivered quite on time"
        "otherwise inform customer about delay"
        
    ),

    "password":(
        "custometrs or  users should be able to change passwords"
        "via authenticated means alone"
    )



}


ORDERS = {

    "ord_1": {
        "customer_id": "cust_1",
        "order_status": "shipped"
    },

    "ord_2": {
        "customer_id": "cust_2",
        "order_status": "delivered"
    }
}


def search_knowledge(message: str):
    message= message.lower()

    for keyword, answer, in FAQS.items():
        if keyword in message:
            return answer

    return None


def get_order_status(order_id: str, customer_id: str):
    normalized_id = order_id.lower().replace("-", "_")
    order = ORDERS.get(normalized_id)

    if not order:
        return None

    if order["customer_id"].lower() != customer_id.lower():
        return None

    return order["order_status"]


def get_order(order_id: str, customer_id: str):
    return get_order_status(order_id, customer_id)
