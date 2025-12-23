# config_validator.py

from pydantic import BaseModel, ValidationError, Field
import json

class ConfigSchema(BaseModel):
    # Define your configuration schema here
    api_key: str = Field(..., description="API key for accessing the service")
    timeout: int = Field(..., description="Timeout in seconds for API requests")
    retries: int = Field(..., description="Number of retries on failure")

    @classmethod
    def validate_config(cls, config_data):
        try:
            # Parse and validate the configuration data
            config = cls(**config_data)
            return config
        except ValidationError as e:
            # Handle validation errors and provide useful error messages
            error_messages = [f"{err['loc'][0]}: {err['msg']}" for err in e.errors()]
            raise ValueError("Configuration validation failed:\n{}".format('\n'.join(error_messages)))
def main():
    # Example usage of the ConfigSchema validator
    config_data = {
        "api_key": "your_api_key_here",
        "timeout": 30,
        "retries": 5
    }
    try:
        validated_config = ConfigSchema.validate_config(config_data)
        print("Configuration is valid.")
        print(validated_config.json(indent=2))
    except ValueError as e:
        print(e)

if __name__ == "__main__":
    main()
