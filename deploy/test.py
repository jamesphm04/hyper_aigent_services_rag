from lambda_function import lambda_handler
import sys

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python test.py <id>")
        sys.exit(1)
    event = {"id": sys.argv[1], "is_docker_build": True}  # Set is_docker_build to True for testing
    result = lambda_handler(event, None)
    print(result)