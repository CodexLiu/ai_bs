from openai import OpenAI
import os
from dotenv import load_dotenv
load_dotenv()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def get_openai_response(input_text: str) -> str:
    response = client.responses.create(
        model="gpt-4.1",
        input=input_text
    )
    return response.output[0].content[0].text

def main():
    input_text = "Tell me a three sentence bedtime story about a unicorn."
    response = get_openai_response(input_text)
    print(response)

if __name__ == "__main__":
    main()  