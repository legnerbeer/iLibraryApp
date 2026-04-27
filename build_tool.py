import subprocess
import sys
import os
import tomllib
import json


def run_build(platform="macos"):
    """
    Triggers the flet build process for a specific platform.
    Common platforms: windows, macos, linux, web, apk, ios
    """

    def load_app_info() -> bool:
        try:
            with open("pyproject.toml", "rb") as f:
                config = tomllib.load(f)
            os.makedirs("assets", exist_ok=True)

            with open("src/assets/app.json", "w", encoding="utf-8") as j:
                json.dump(config, j, indent=4)

            return True
        except Exception as e:
            print(f"Build Script Error: {e}")
            return False

    if not load_app_info():
        return

    print(f"--- Starting Build for {platform.upper()} ---")
    cmd = ["flet", "build", platform, "--clear-cache"]

    try:
        result = subprocess.run(cmd, check=True, text=True)
        if result.returncode == 0:
            print(f"--- Build Successful! Check the 'build/{platform}' folder. ---")
    except subprocess.CalledProcessError as e:
        print(f"Error during build: {e}")
        sys.exit(1)


if __name__ == "__main__":
    target_platform = sys.argv[1] if len(sys.argv) > 1 else "macos"
    run_build(target_platform)