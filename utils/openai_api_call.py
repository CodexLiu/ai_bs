from openai import OpenAI
from google import genai
from google.genai import types
import os
import json
from dotenv import load_dotenv
load_dotenv()

def create_client(model: str):
    """Create the appropriate client based on the model type"""
    if model.startswith("gemini"):
        api_key = os.getenv("GOOGLE_GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GOOGLE_GEMINI_API_KEY environment variable is not set")
        return genai.Client(api_key=api_key)
    else:
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY environment variable is not set")
        # Use OpenAI API
        return OpenAI(api_key=api_key)

def convert_openai_tools_to_gemini(openai_tools: list) -> list:
    """
    Convert OpenAI function calling tools to Gemini-friendly format.
    
    Args:
        openai_tools: List of OpenAI tool definitions
        
    Returns:
        List of Gemini tool definitions
    """
    if not openai_tools:
        return []
    
    gemini_function_declarations = []
    
    for tool in openai_tools:
        if tool.get("type") == "function":
            function_spec = tool["function"]
            
            # Convert OpenAI schema to Gemini schema
            gemini_function = types.FunctionDeclaration(
                name=function_spec["name"],
                description=function_spec["description"],
                parameters=convert_openai_schema_to_gemini(function_spec.get("parameters", {}))
            )
            
            gemini_function_declarations.append(gemini_function)
    
    # Return a single Tool object with all function declarations
    return [types.Tool(function_declarations=gemini_function_declarations)] if gemini_function_declarations else []

def convert_openai_schema_to_gemini(openai_schema: dict) -> types.Schema:
    """
    Convert OpenAI JSON schema to Gemini Schema format.
    
    Args:
        openai_schema: OpenAI JSON schema
        
    Returns:
        Gemini Schema object
    """
    if not openai_schema:
        return types.Schema(type="OBJECT")
    
    schema_type = openai_schema.get("type", "object").upper()
    
    # Handle different schema types
    if schema_type == "OBJECT":
        properties = {}
        if "properties" in openai_schema:
            for prop_name, prop_schema in openai_schema["properties"].items():
                properties[prop_name] = convert_openai_schema_to_gemini(prop_schema)
        
        return types.Schema(
            type="OBJECT",
            properties=properties,
            required=openai_schema.get("required", [])
        )
    
    elif schema_type == "ARRAY":
        items_schema = None
        if "items" in openai_schema:
            items_schema = convert_openai_schema_to_gemini(openai_schema["items"])
        
        return types.Schema(
            type="ARRAY",
            items=items_schema
        )
    
    elif schema_type == "STRING":
        schema = types.Schema(type="STRING")
        if "description" in openai_schema:
            schema.description = openai_schema["description"]
        if "enum" in openai_schema:
            schema.enum = openai_schema["enum"]
        return schema
    
    elif schema_type == "INTEGER":
        schema = types.Schema(type="INTEGER")
        if "description" in openai_schema:
            schema.description = openai_schema["description"]
        if "minimum" in openai_schema:
            schema.minimum = openai_schema["minimum"]
        if "maximum" in openai_schema:
            schema.maximum = openai_schema["maximum"]
        return schema
    
    elif schema_type == "NUMBER":
        schema = types.Schema(type="NUMBER")
        if "description" in openai_schema:
            schema.description = openai_schema["description"]
        return schema
    
    elif schema_type == "BOOLEAN":
        schema = types.Schema(type="BOOLEAN")
        if "description" in openai_schema:
            schema.description = openai_schema["description"]
        return schema
    
    else:
        # Default to string for unknown types
        return types.Schema(type="STRING")

def convert_openai_messages_to_gemini(messages: list) -> list:
    """
    Convert OpenAI messages format to Gemini contents format.
    
    Args:
        messages: List of OpenAI message objects
        
    Returns:
        List of Gemini content objects
    """
    gemini_contents = []
    
    for message in messages:
        role = message.get("role", "user")
        content = message.get("content", "")
        
        if role == "system":
            # System messages are typically handled differently in Gemini
            # We'll convert them to user messages with a system prefix
            gemini_content = types.Content(
                role="user",
                parts=[types.Part.from_text(text=f"System: {content}")]
            )
        elif role == "user":
            gemini_content = types.Content(
                role="user",
                parts=[types.Part.from_text(text=content)]
            )
        elif role == "assistant":
            gemini_content = types.Content(
                role="model",
                parts=[types.Part.from_text(text=content)]
            )
        else:
            # Default to user role
            gemini_content = types.Content(
                role="user",
                parts=[types.Part.from_text(text=content)]
            )
        
        gemini_contents.append(gemini_content)
    
    return gemini_contents

def convert_gemini_response_to_openai_format(gemini_response) -> dict:
    """
    Convert Gemini API response to OpenAI-compatible format.
    
    Args:
        gemini_response: The response from Gemini API
        
    Returns:
        OpenAI-compatible response dictionary
    """
    # Create OpenAI-like structure
    openai_response = type('OpenAIResponse', (), {})()
    openai_response.choices = []
    
    if gemini_response.candidates:
        candidate = gemini_response.candidates[0]
        
        # Create choice object
        choice = type('Choice', (), {})()
        choice.message = type('Message', (), {})()
        
        # Check if there are function calls
        if gemini_response.function_calls:
            choice.message.tool_calls = []
            
            for func_call in gemini_response.function_calls:
                tool_call = type('ToolCall', (), {})()
                tool_call.id = func_call.id if hasattr(func_call, 'id') else "call_" + func_call.name
                tool_call.type = "function"
                tool_call.function = type('Function', (), {})()
                tool_call.function.name = func_call.name
                tool_call.function.arguments = json.dumps(func_call.args)
                
                choice.message.tool_calls.append(tool_call)
            
            choice.message.content = None
        else:
            # Regular text response
            choice.message.content = gemini_response.text if hasattr(gemini_response, 'text') else ""
            choice.message.tool_calls = None
        
        openai_response.choices.append(choice)
    
    # Add usage information if available
    if hasattr(gemini_response, 'usage'):
        openai_response.usage = gemini_response.usage
    
    return openai_response

def get_openai_response(input_text: str, model: str = "gpt-4.1") -> str:
    try:
        client = create_client(model)
        
        if model.startswith("gemini"):
            # Use Gemini API
            response = client.models.generate_content(
                model=model,
                contents=input_text,
                config=types.GenerateContentConfig(
                    temperature=0.7
                )
            )
            return response.text
        else:
            # Use OpenAI API
            response = client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": input_text}],
                temperature=0.7
            )
            return response.choices[0].message.content
    except Exception as e:
        print(f"Error in get_openai_response with model {model}: {e}")
        raise

async def call_openai_api(prompt: str, model: str = "gpt-4o-mini", max_tokens: int = 1000, temperature: float = 0.7) -> str:
    """
    Make an async API call for summarization and other tasks.
    
    Args:
        prompt: The prompt to send to the API
        model: The model to use (supports both OpenAI and Gemini models)
        max_tokens: Maximum tokens in response (ignored for Gemini models)
        temperature: Temperature for randomness
        
    Returns:
        The response text from the API
    """
    try:
        print(f"🔍 DEBUG: Making API call with model: {model}")
        client = create_client(model)
        
        # For Gemini models, don't use max_tokens as it causes issues
        if model.startswith("gemini"):
            print(f"🔍 DEBUG: Using Gemini API for model: {model}")
            print(f"🔍 DEBUG: Prompt length: {len(prompt)} characters")
            
            response = client.models.generate_content(
                model=model,
                contents=prompt,
                config=types.GenerateContentConfig(
                    temperature=temperature
                )
            )
            result = response.text
        else:
            print(f"🔍 DEBUG: Using OpenAI API for model: {model}")
            response = client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=max_tokens,
                temperature=temperature
            )
            result = response.choices[0].message.content
        
        print(f"🔍 DEBUG: API call successful, response length: {len(result) if result else 0}")
        return result
        
    except Exception as e:
        print(f"❌ DEBUG: API call failed with model {model}")
        print(f"❌ DEBUG: Error type: {type(e).__name__}")
        print(f"❌ DEBUG: Error message: {str(e)}")
        
        # Check if it's a 404 error specifically
        if hasattr(e, 'response') and hasattr(e.response, 'status_code'):
            print(f"❌ DEBUG: HTTP Status Code: {e.response.status_code}")
            if hasattr(e.response, 'text'):
                print(f"❌ DEBUG: Response text: {e.response.text}")
        
        # Re-raise the original exception
        raise

async def call_openai_api_with_tools(
    messages: list, 
    model: str = "gpt-4o-mini", 
    tools: list = None,
    max_tokens: int = 1000, 
    temperature: float = 0.7
) -> dict:
    """
    Make an async API call with function calling support.
    
    Args:
        messages: List of messages for the conversation
        model: The model to use (supports both OpenAI and Gemini models)
        tools: List of tools/functions for function calling
        max_tokens: Maximum tokens in response (ignored for Gemini models)
        temperature: Temperature for randomness
        
    Returns:
        The full response object from the API
    """
    try:
        print(f"🔍 DEBUG: Making API call with tools for model: {model}")
        client = create_client(model)
        
        # For Gemini models, don't use max_tokens as it causes issues
        if model.startswith("gemini"):
            print(f"🔍 DEBUG: Using Gemini API for model: {model}")
            
            # Convert OpenAI messages to Gemini format
            gemini_contents = convert_openai_messages_to_gemini(messages)
            
            # Convert OpenAI tools to Gemini format
            gemini_tools = convert_openai_tools_to_gemini(tools) if tools else []
            
            # Create config
            config = types.GenerateContentConfig(
                temperature=temperature,
                automatic_function_calling=types.AutomaticFunctionCallingConfig(
                    disable=True  # Disable automatic calling to get function calls back
                )
            )
            
            if gemini_tools:
                config.tools = gemini_tools
            
            response = client.models.generate_content(
                model=model,
                contents=gemini_contents,
                config=config
            )
            
            # Convert Gemini response to OpenAI-like format for compatibility
            return convert_gemini_response_to_openai_format(response)
        else:
            print(f"🔍 DEBUG: Using OpenAI API for model: {model}")
            response = client.chat.completions.create(
                model=model,
                messages=messages,
                tools=tools,
                temperature=temperature,
                max_tokens=max_tokens
            )
            return response
        
        print(f"🔍 DEBUG: API call with tools successful")
        
    except Exception as e:
        print(f"❌ DEBUG: API call with tools failed for model {model}")
        print(f"❌ DEBUG: Error type: {type(e).__name__}")
        print(f"❌ DEBUG: Error message: {str(e)}")
        
        # Check if it's a 404 error specifically
        if hasattr(e, 'response') and hasattr(e.response, 'status_code'):
            print(f"❌ DEBUG: HTTP Status Code: {e.response.status_code}")
            if hasattr(e.response, 'text'):
                print(f"❌ DEBUG: Response text: {e.response.text}")
        
        # Re-raise the original exception
        raise

def main():
    input_text = "Tell me a three sentence bedtime story about a unicorn."
    response = get_openai_response(input_text)
    print(response)

if __name__ == "__main__":
    main()  