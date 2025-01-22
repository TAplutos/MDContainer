#!/usr/bin/env python3

import wmill

def run_python_code_async_on_windmill(script_code: str, script_name: str, api_token: str):
    """
    Takes Python code as a string and executes it asynchronously on Windmill using the wmill client.

    :param script_code: The Python code to run (as a string).
    :param script_name: A unique name for the script on Windmill.
    :param api_token: Your Windmill API token.
    """
    # Initialize Windmill client with your credentials
    client = wmill.Client(api_token=api_token)

    # Upsert (create or update) a script with the given code
    client.scripts.upsert(
        name=script_name,
        code=script_code,
        runtime="python3"   # or the specific runtime supported by your Windmill instance
    )

    # Run the script asynchronously
    run_response = client.scripts.run(
        name=script_name,
        async_execution=True  # indicates an asynchronous run
        # You can pass arguments here if your script requires them
        # arguments={"some_param": "some_value"}
    )

    # The run_response typically includes a run ID to track execution
    run_id = run_response.get("runId")
    print(f"Script '{script_name}' started asynchronously with run ID: {run_id}")


if __name__ == "__main__":
    # Example usage: Provide your Python code as a string
    code_to_run = """
print("Hello from Windmill!")
x = 2 + 2
print("2 + 2 =", x)
return x
"""

    # Replace with your Windmill API token
    windmill_api_token = "FaIv0EC2Gfy3dpqtWqGWS0ZjlStCYL8m"

    # Give a unique name for the script
    script_name_on_windmill = "my_async_python_script"

    run_python_code_async_on_windmill(
        script_code=code_to_run,
        script_name=script_name_on_windmill,
        api_token=windmill_api_token
    )
