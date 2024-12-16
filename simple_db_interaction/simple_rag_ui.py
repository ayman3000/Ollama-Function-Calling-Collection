import streamlit as st
import pandas as pd
import asyncio
from ollama import ChatResponse
import ollama

# Load the product dataset
PRODUCTS_FILE = "products.csv"
products_df = pd.read_csv(PRODUCTS_FILE)


# Define the query function
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

# Define the Streamlit app
st.title("Interactive Product Query")

# Chat log container
if "log" not in st.session_state:
    st.session_state.log = []

# User input prompt
user_prompt = st.text_input("Enter your prompt:")

if st.button("Submit"):
    if user_prompt:
        # Add the user prompt to the log
        st.session_state.log.append(f"User: {user_prompt}")

        # Define system role for Ollama
        system_role = ("Translate into English first. Use query_products if function caling is needed."
                       " Use these column names: product_id,product_name,category,price,stock,description. Use 'like' "
                       "to filter description only if needed. Send value in lowercase without % sign.")


        async def process_prompt():
            client = ollama.AsyncClient()

            # Send user prompt to the model
            response: ChatResponse = await client.chat(
                'qwen2.5-coder:7b',
                messages=[{'role': 'system', 'content': system_role},
                          {'role': 'user', 'content': user_prompt}],
                tools=[query_products_tool]
            )

            # Check if the model requested a function call
            if response.message.tool_calls:
                for tool in response.message.tool_calls:
                    # Extract function name and arguments
                    function_name = tool.function.name
                    arguments = tool.function.arguments

                    if function_name == "query_products":
                        # Call the query_products function
                        query_result = query_products(**arguments)

                        # Send the query result back to the model for natural response
                        followup_response: ChatResponse = await client.chat(
                            'qwen2.5-coder:7b',
                            messages=[
                                {'role': 'system', 'content': 'Rephrase the result in  bullets  friendly conversational tone.'},
                                {'role': 'user', 'content': query_result},
                            ]
                        )
                        return followup_response.message.content, query_result
            else:
                # No tool call requested, return the raw response
                return response.message.content, None


        # Run the async function
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        final_response, raw_data = loop.run_until_complete(process_prompt())

        # Add the assistant response to the log
        st.session_state.log.append(f"Assistant: {final_response}")

        # Display the assistant's response
        st.markdown("### Assistant Response:")
        st.write(final_response)

        # Optionally show raw data if available
        if raw_data:
            st.markdown("### Query Results (Raw Data):")
            st.code(raw_data)
    else:
        st.warning("Please enter a prompt.")

# Display the chat log
st.markdown("### Chat Log:")
for log_entry in st.session_state.log:
    st.write(log_entry)
