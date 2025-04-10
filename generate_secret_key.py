import secrets
import os

def generate_secret_key():
    # Generate a 32-byte (256-bit) hex token
    key = secrets.token_hex(32)
    
    # Path to .env file
    env_path = os.path.join(os.path.dirname(__file__), '.env')
    
    # Read existing .env file or create new
    existing_env = {}
    if os.path.exists(env_path):
        with open(env_path, 'r') as f:
            for line in f:
                if '=' in line:
                    key, value = line.strip().split('=', 1)
                    existing_env[key] = value
    
    # Update or add SECRET_KEY
    existing_env['SECRET_KEY'] = key
    
    # Write back to .env file
    with open(env_path, 'w') as f:
        for k, v in existing_env.items():
            f.write(f"{k}={v}\n")
    
    print(f"New SECRET_KEY generated and saved to {env_path}")
    print(f"Generated Key: {key}")

if __name__ == "__main__":
    generate_secret_key()