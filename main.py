import datetime
import os
import random

import cosmosdb
from swarm import Swarm, Agent
from swarm.repl import run_demo_loop
from openai import AzureOpenAI

# Azure OpenAI API configuration
aoai_client = AzureOpenAI(
    api_key=os.getenv("AZURE_OPENAI_API_KEY"),
    api_version="2024-09-01-preview",
    azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT")
)

# Initialize Swarm client with Azure OpenAI client
swarm_client = Swarm(client=aoai_client)


def refund_item(user_id, item_id):
    """Initiate a refund based on the user ID and item ID.
    Takes as input arguments in the format '{"user_id":1,"item_id":3}'
    """
    try:
        database = cosmosdb.client.get_database_client(cosmosdb.database_name)
        container = database.get_container_client(cosmosdb.purchase_history_container_name)
        query = "SELECT c.amount FROM c WHERE c.user_id=@user_id AND c.item_id=@item_id"
        parameters = [
            {"name": "@user_id", "value": int(user_id)},
            {"name": "@item_id", "value": int(item_id)}
        ]
        items = list(container.query_items(query=query, parameters=parameters, enable_cross_partition_query=True))
        if items:
            amount = items[0]['amount']
            print(f"Refunding ${amount} to user ID {user_id} for item ID {item_id}.")
        else:
            print(f"No purchase found for user ID {user_id} and item ID {item_id}.")
        print("Refund initiated")
    except Exception as e:
        print(f"An error occurred during refund: {e}")


def notify_customer(user_id, method):
    """Notify a customer by their preferred method of either phone or email.
    Takes as input arguments in the format '{"user_id":1,"method":"email"}'"""
    try:
        database = cosmosdb.client.get_database_client(cosmosdb.database_name)
        container = database.get_container_client(cosmosdb.users_container_name)
        query = "SELECT c.email, c.phone FROM c WHERE c.user_id=@user_id"
        parameters = [{"name": "@user_id", "value": int(user_id)}]
        items = list(container.query_items(query=query, parameters=parameters, enable_cross_partition_query=True))
        if items:
            email, phone = items[0]['email'], items[0]['phone']
            if method == "email" and email:
                print(f"Emailed customer {email} a notification.")
            elif method == "phone" and phone:
                print(f"Texted customer {phone} a notification.")
            else:
                print(f"No {method} contact available for user ID {user_id}.")
        else:
            print(f"User ID {user_id} not found.")
    except Exception as e:
        print(f"An error occurred during notification: {e}")


def order_item(user_id, product_id):
    """Place an order for a product based on the user ID and product ID.
    Takes as input arguments in the format '{"user_id":1,"product_id":2}'"""
    try:
        date_of_purchase = datetime.datetime.now().isoformat()
        item_id = random.randint(1, 300)

        database = cosmosdb.client.get_database_client(cosmosdb.database_name)
        container = database.get_container_client(cosmosdb.products_container_name)
        query = "SELECT c.product_id, c.product_name, c.price FROM c WHERE c.product_id=@product_id"
        parameters = [{"name": "@product_id", "value": product_id}]
        items = list(container.query_items(query=query, parameters=parameters, enable_cross_partition_query=True))
        if items:
            product = items[0]
            product_id, product_name, price = product['product_id'], product['product_name'], product['price']
            print(f"Ordering product {product_name} for user ID {user_id}. The price is {price}.")
            # Add the purchase to the database
            cosmosdb.add_purchase(user_id, date_of_purchase, item_id, price)
        else:
            print(f"Product {product_id} not found.")
    except Exception as e:
        print(f"An error occurred during order placement: {e}")


# Initialize the database
cosmosdb.initialize_database()

# Preview tables
cosmosdb.preview_table("Users")
cosmosdb.preview_table("PurchaseHistory")
cosmosdb.preview_table("Products")

# Define the agents

refunds_agent = Agent(
    name="Refunds Agent",
    description="""You are a refund agent that handles all actions related to refunds after a return has been processed.
    You must ask for both the user ID and item ID to initiate a refund. Ask for both user_id and item_id in one message.
    If the user asks you to notify them, you must ask them what their preferred method of notification is. For notifications, you must
    ask them for user_id and method in one message.""",
    functions=[refund_item, notify_customer],
)

sales_agent = Agent(
    name="Sales Agent",
    description="""You are a sales agent that handles all actions related to placing an order to purchase an item.
    Regardless of what the user wants to purchase, must ask for BOTH the user ID and product ID to place an order.
    An order cannot be placed without these two pieces of information. Ask for both user_id and product_id in one message.
    If the user asks you to notify them, you must ask them what their preferred method is. For notifications, you must
    ask them for user_id and method in one message.
    """,
    functions=[order_item, notify_customer],
)

triage_agent = Agent(
    name="Triage Agent",
    instructions="""You are to triage a users request, and call a tool to transfer to the right intent.
    Once you are ready to transfer to the right intent, call the tool to transfer to the right intent.
    You dont need to know specifics, just the topic of the request.
    If the user request is about making an order or purchasing an item, transfer to the Sales Agent.
    If the user request is about getting a refund on an item or returning a product, transfer to the Refunds Agent.
    When you need more information to triage the request to an agent, ask a direct question without explaining why you're asking it.
    Do not share your thought process with the user! Do not make unreasonable assumptions on behalf of user.""",
    agents=[sales_agent, refunds_agent],
    add_backlinks=True,
)


def transfer_to_sales():
    return sales_agent


def transfer_to_refunds():
    return refunds_agent


for f in triage_agent.functions:
    print(f.__name__)

triage_agent.functions = [transfer_to_sales, transfer_to_refunds]

if __name__ == "__main__":
    # Run the demo loop
    run_demo_loop(triage_agent, debug=False)
