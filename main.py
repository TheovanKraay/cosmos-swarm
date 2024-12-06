import datetime
import json
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

openai_completions_deployment = "completions"

# Initialize Swarm client with Azure OpenAI client
swarm_client = Swarm(client=aoai_client)

#global chat history list
chat_history = []


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
        parameters = [{"name": "@product_id", "value": int(product_id)}]
        items = list(container.query_items(query=query, parameters=parameters, enable_cross_partition_query=True))
        if items:
            product = items[0]
            product_id, product_name, price = product['product_id'], product['product_name'], product['price']
            print(f"Ordering product {product_name} for user ID {user_id}. The price is {price}.")
            # Add the purchase to the database
            cosmosdb.add_purchase(int(user_id), date_of_purchase, item_id, price)
        else:
            print(f"Product {product_id} not found.")
    except Exception as e:
        print(f"An error occurred during order placement: {e}")

def product_information_chat(user_prompt):
    # Perform a vector search on the Cosmos DB container
    vectors = cosmosdb.generate_embedding(user_prompt)
    vector_search_results = vector_search(cosmosdb.products_container_name, vectors)
    results = generate_completion(user_prompt, vector_search_results, chat_history=[])
    return results

# Perform a vector search on the Cosmos DB container
def vector_search(container, vectors, similarity_score=0.02, num_results=3):
    # Execute the query
    database = cosmosdb.client.get_database_client(cosmosdb.database_name)
    container = database.get_container_client(cosmosdb.products_container_name)
    results = container.query_items(
        query= '''
        SELECT TOP @num_results c.product_id, c.product_description, VectorDistance(c.product_description_vector, @embedding) as SimilarityScore 
        FROM c
        WHERE VectorDistance(c.product_description_vector,@embedding) > @similarity_score
        ORDER BY VectorDistance(c.product_description_vector,@embedding)
        ''',
        parameters=[
            {"name": "@embedding", "value": vectors},
            {"name": "@num_results", "value": num_results},
            {"name": "@similarity_score", "value": similarity_score}
        ],
        enable_cross_partition_query=True, populate_query_metrics=True)
    print("Executed vector search in Azure Cosmos DB... \n")
    results = list(results)
    # Extract the necessary information from the results
    formatted_results = []
    for result in results:
        score = result.pop('SimilarityScore')
        #convert product_id to string
        result['product_id'] = str(result['product_id'])
        #apend product id to the beginning of each product description
        result['product_description'] ="product id "+result['product_id'] + ": " + result['product_description']
        formatted_result = {
            'SimilarityScore': score,
            'document': result
        }
        #print(formatted_result)
        formatted_results.append(formatted_result)
    return formatted_results


def generate_completion(user_prompt, vector_search_results, chat_history):
    system_prompt = '''
    You are an intelligent assistant for product information. You are designed to provide helpful answers to user questions about products in the database.
    You are friendly, helpful, and informative and can be lighthearted. Be concise in your responses, but still friendly.
        - Only answer questions related to the information provided below.
        - Write two lines of whitespace between each answer in the list.
    '''

    # Create a list of messages as a payload to send to the OpenAI Completions API

    # system prompt
    messages = [{'role': 'system', 'content': system_prompt}]

    # user prompt
    messages.append({'role': 'user', 'content': user_prompt})

    # vector search results
    for result in vector_search_results:
        messages.append({'role': 'system', 'content': json.dumps(result['document'])})

    # print("Messages going to openai", messages)
    # Create the completion
    response = aoai_client.chat.completions.create(
        model=openai_completions_deployment,
        messages=messages,
        temperature=0.1
    )
    #print("Response to product query: \n")
    completions_results = response.model_dump()

    #print(completions_results['choices'][0]['message']['content'])
    return completions_results['choices'][0]['message']['content']



# Initialize the database
cosmosdb.initialize_database()

# Preview tables
cosmosdb.preview_table("Users")
cosmosdb.preview_table("PurchaseHistory")
cosmosdb.preview_table("Products")

def transfer_to_sales():
    return sales_agent


def transfer_to_refunds():
    return refunds_agent

# Define the agents

refunds_agent = Agent(
    name="Refunds Agent",
    description="""You are a refund agent that handles all actions related to refunds after a return has been processed.
    You must ask for both the user ID and item ID to initiate a refund. Ask for both user_id and item_id in one message.
    Do not use any other context information to determine whether the right user id or item id has been provided - just accept the input as is.
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
    agents=[refunds_agent],
    functions=[order_item, notify_customer, transfer_to_refunds],
)

triage_agent = Agent(
    name="Triage Agent",
    instructions="""You are to triage a users request, and call a tool to transfer to the right intent.
    If the user asks for product information, you should call the product_information_chat function, 
    passing their question to it, and returning the results.
    Otherwise, once you are ready to transfer to the right intent, call the tool to transfer to the right intent.
    You dont need to know specifics, just the topic of the request.
    If the user request is about making an order or purchasing an item, transfer to the Sales Agent.
    If the user request is about getting a refund on an item or returning a product, transfer to the Refunds Agent.
    When you need more information to triage the request to an agent, ask a direct question without explaining why you're asking it.
    Do not share your thought process with the user! Do not make unreasonable assumptions on behalf of user.""",
    agents=[sales_agent, refunds_agent],
    functions=[product_information_chat],
    add_backlinks=True,
)

for f in triage_agent.functions:
    print(f.__name__)

triage_agent.functions = [transfer_to_sales, transfer_to_refunds, product_information_chat]

if __name__ == "__main__":
    # Run the demo loop
    run_demo_loop(triage_agent, debug=False)
