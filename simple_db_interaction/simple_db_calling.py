import asyncio
from ollama import ChatResponse
import ollama
import pandas as pd

# Load the product dataset
PRODUCTS_FILE = "products.csv"
products_df = pd.read_csv(PRODUCTS_FILE)


# Define a single versatile function for querying
def query_products(field: str, condition: str, value: str) -> str:
    """
    Query the products dataset based on a field, condition, and value.

    Args:
      field (str): The column to filter (e.g., "Price", "Category").
      condition (str): The condition to apply (e.g., "=", ">", "<", "like").
      value (str): The value to compare against.

    Returns:
      str: Matching records or a not found message.
    """
    if field not in products_df.columns:
        return f"Field '{field}' does not exist in the dataset."

    try:
        # Convert value to lowercase if it's a string
        if isinstance(value, str):
            value = value.lower()

        # Apply the appropriate condition
        if condition == "=":
            filtered_df = products_df[products_df[field].str.lower() == value]
        elif condition == ">=" or condition == ">":
            filtered_df = products_df[products_df[field] > float(value)]
        elif condition == "<=" or condition == "<":
            filtered_df = products_df[products_df[field] < float(value)]
        elif condition.lower() == "like":
            # Perform a case-insensitive substring match
            filtered_df = products_df[products_df[field].str.contains(value, case=False, na=False)]
        else:
            return f"Condition '{condition}' is not supported."

        # Return results
        if not filtered_df.empty:
            return filtered_df.to_string(index=False)
        else:
            return "No matching records found."
    except Exception as e:
        return f"Error processing query: {e}"


# Define a tool for querying products
query_products_tool = {
    'type': 'function',
    'function': {
        'name': 'query_products',
        'description': 'Query products based on a field, condition, and value.',
        'parameters': {
            'type': 'object',
            'required': ['field', 'condition', 'value'],
            'properties': {
                'field': {
                    'type': 'string',
                    'description': 'The column to query (e.g., "Price", "Category").'
                },
                'condition': {
                    'type': 'string',
                    'description': 'The condition to apply (e.g., "=", ">", "<", "like").'
                },
                'value': {
                    'type': 'string',
                    'description': 'The value to compare against.'
                }
            }
        }
    }
}


# Main function to integrate Ollama with the single query tool
async def main():
    client = ollama.AsyncClient()

    # User query
    prompt = "Find all products with 'Mouse' in the name."
    # prompt = "Find Products with price > 700"
    print('Prompt:', prompt)

    # Available functions
    available_functions = {
        'query_products': query_products,
    }

    system_role = ("Use these column names: product_id,product_name,category,price,stock,description. "
                   "You can use 'like' to filter description only if needed. Send value in lowercase without % sign")

    # Get response from the model
    response: ChatResponse = await client.chat(
        'qwen2.5-coder:7b',
        messages=[{'role':'system', 'content':system_role},
                  {'role': 'user', 'content': prompt}],
        tools=[query_products_tool],
    )
    print(f"Response: {response}")

    # Handle function calls
    if response.message.tool_calls:
        for tool in response.message.tool_calls:
            # Call the appropriate function
            if function_to_call := available_functions.get(tool.function.name):
                print('Calling function:', tool.function.name)
                print('Arguments:', tool.function.arguments)
                function_output = function_to_call(**tool.function.arguments)
                print('Function output:', function_output)
            else:
                print('Function', tool.function.name, 'not found')
    else:
        print('No functions found')
        print(response.message.content)


# Run the main function
if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print('\nGoodbye!')
