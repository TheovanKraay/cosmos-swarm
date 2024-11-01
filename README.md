# Multi-agent AI sample with Azure Cosmos DB

A personal shopping agent that can help with making sales and refunding orders by transferring to different agents for those tasks.
This example uses the helper function `run_demo_loop`, which allows us to create an interactive [OpenAI Swarm](https://github.com/openai/swarm) session.
We use [Azure Cosmos DB](https://learn.microsoft.com/azure/cosmos-db/introduction) to store customer information and transaction data.

## Demo

![Demo](./media/demo.gif)

## Overview

The personal shopper example includes three main agents to handle various customer service requests:

1. **Triage Agent**: Determines the type of request and transfers to the appropriate agent.
2. **Refund Agent**: Manages customer refunds, requiring both user ID and item ID to initiate a refund.
3. **Sales Agent**: Handles actions related to placing orders, requiring both user ID and product ID to complete a purchase.

## Setup

Install dependencies:

```shell
pip install git+https://github.com/openai/swarm.git
pip install azure-cosmos==4.7.0
```

Ensure you have the following environment variables set:
```shell
AZURE_COSMOSDB_ENDPOINT=your_cosmosdb_account_uri
AZURE_COSMOSDB_KEY=your_cosmosdb_account_key
OPENAI_API_KEY=your_openai_api_key
```

Once you have installed dependencies and Swarm, run the example using:

```shell
python3 main.py
```
