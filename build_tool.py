import subprocess
import sys
import os
import tomllib
import json
from os import write


def run_build(platform="macos"):
    """
    Triggers the flet build process for a specific platform.
    Common platforms: windows, macos, linux, web, apk, ios
    """

    def load_app_info() -> bool:
        try:
            # 1. Read the TOML (Standard in Python 3.11+)
            with open("pyproject.toml", "rb") as f:
                config = tomllib.load(f)

            # Extract specific flet metadata if needed
            # app_data = config.get("tool", {}).get("flet", {})

            # 2. Ensure the assets directory exists
            os.makedirs("assets", exist_ok=True)

            # 3. Write to JSON (Text mode 'w' is safer for JSON)
            with open("src/assets/app.json", "w", encoding="utf-8") as j:
                json.dump(config, j, indent=4)

            return True
        except Exception as e:
            print(f"Build Script Error: {e}")
            return False

    if not load_app_info():
        return

    print(f"--- Starting Build for {platform.upper()} ---")

    # 1. (Optional) Run pre-build tasks
    # e.g., os.system("python generate_assets.py")

    # 2. Construct the command
    # 'flet build' handles the heavy lifting of Flutter integration
    cmd = ["flet", "build", platform, "--clear-cache"]

    try:
        # 3. Execute the build
        result = subprocess.run(cmd, check=True, text=True)
        if result.returncode == 0:
            print(f"--- Build Successful! Check the 'build/{platform}' folder. ---")
    except subprocess.CalledProcessError as e:
        print(f"Error during build: {e}")
        sys.exit(1)


if __name__ == "__main__":
    # You can pass the platform as a command line argument
    target_platform = sys.argv[1] if len(sys.argv) > 1 else "macos"
    run_build(target_platform)