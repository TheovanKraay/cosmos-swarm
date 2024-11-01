import os

from azure.cosmos import CosmosClient, PartitionKey, exceptions

# Initialize the Cosmos client
# reference environment variables for the values of these variables
endpoint = os.environ['AZURE_COSMOSDB_ENDPOINT']
key = os.environ['AZURE_COSMOSDB_KEY']
client = CosmosClient(endpoint, key)

# Database and container names
database_name = "PersonalShopperDB"
users_container_name = "Users"
purchase_history_container_name = "PurchaseHistory"
products_container_name = "Products"

# Create database and containers if they don't exist
def create_database():
    try:
        database = client.create_database_if_not_exists(id=database_name)
        users_container = database.create_container_if_not_exists(
            id=users_container_name,
            partition_key=PartitionKey(path="/user_id"),
            offer_throughput=400
        )
        purchase_history_container = database.create_container_if_not_exists(
            id=purchase_history_container_name,
            partition_key=PartitionKey(path="/user_id"),
            offer_throughput=400
        )
        products_container = database.create_container_if_not_exists(
            id=products_container_name,
            partition_key=PartitionKey(path="/product_id"),
            offer_throughput=400
        )
    except exceptions.CosmosHttpResponseError as e:
        print(f"Database creation failed: {e}")

def add_user(user_id, first_name, last_name, email, phone):
    database = client.get_database_client(database_name)
    container = database.get_container_client(users_container_name)
    user = {
        "id": str(user_id),
        "user_id": user_id,
        "first_name": first_name,
        "last_name": last_name,
        "email": email,
        "phone": phone
    }
    try:
        container.create_item(body=user)
    except exceptions.CosmosResourceExistsError:
        print(f"User with user_id {user_id} already exists.")

def add_purchase(user_id, date_of_purchase, item_id, amount):
    database = client.get_database_client(database_name)
    container = database.get_container_client(purchase_history_container_name)
    purchase = {
        "id": f"{user_id}_{item_id}_{date_of_purchase}",
        "user_id": user_id,
        "date_of_purchase": date_of_purchase,
        "item_id": item_id,
        "amount": amount
    }
    try:
        container.create_item(body=purchase)
    except exceptions.CosmosResourceExistsError:
        print(f"Purchase already exists for user_id {user_id} on {date_of_purchase} for item_id {item_id}.")

def add_product(product_id, product_name, price):
    database = client.get_database_client(database_name)
    container = database.get_container_client(products_container_name)
    product = {
        "id": str(product_id),
        "product_id": product_id,
        "product_name": product_name,
        "price": price
    }
    try:
        container.create_item(body=product)
    except exceptions.CosmosResourceExistsError:
        print(f"Product with product_id {product_id} already exists.")

def preview_table(container_name):
    database = client.get_database_client(database_name)
    container = database.get_container_client(container_name)
    items = container.query_items(
        query="SELECT * FROM c",
        enable_cross_partition_query=True
    )
    for item in items:
        print(item)

# Initialize and load database
def initialize_database():
    create_database()

    # Add some initial users
    initial_users = [
        (1, "Alice", "Smith", "alice@test.com", "123-456-7890"),
        (2, "Bob", "Johnson", "bob@test.com", "234-567-8901"),
        (3, "Sarah", "Brown", "sarah@test.com", "555-567-8901"),
        # Add more initial users here
    ]

    for user in initial_users:
        add_user(*user)

    # Add some initial purchases
    initial_purchases = [
        (1, "2024-01-01", 101, 99.99),
        (2, "2023-12-25", 100, 39.99),
        (3, "2023-11-14", 307, 49.99),
    ]

    for purchase in initial_purchases:
        add_purchase(*purchase)

    initial_products = [
        (7, "Hat", 19.99),
        (8, "Wool socks", 29.99),
        (9, "Shoes", 39.99),
    ]

    for product in initial_products:
        add_product(*product)