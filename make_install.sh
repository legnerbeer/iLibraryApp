#!/bin/bash

# --- CONFIGURATION ---
APP_NAME="iLibrary"
BUILD_DIR="build/macos"
APP_BUNDLE="$BUILD_DIR/$APP_NAME.app"
PYODBC_PATH="$APP_BUNDLE/Contents/Frameworks/serious_python_darwin.framework/Versions/A/Resources/python.bundle/Contents/Resources/site-packages/pyodbc.cpython-312-darwin.so"
BREW_LIB="/opt/homebrew/opt/unixodbc/lib/libodbc.2.dylib"

echo "Starting Production Build for $APP_NAME..."

#Security Cleanup (Remove sensitive files before packaging)
echo "Removing sensitive environment and auth files..."


rm -rf "$APP_BUNDLE/Contents/Resources/app/src/content/.auth"
rm -f "$APP_BUNDLE/Contents/Resources/app/src/content/.env"

#Cleanup old artifacts
echo "🧹 Cleaning old DMG and mounts..."
rm -f "$APP_NAME-Installer.dmg"
hdiutil detach "/Volumes/$APP_NAME Installer" 2>/dev/null || true

#Inject the Library
echo "Injecting libodbc into Frameworks..."
mkdir -p "$APP_BUNDLE/Contents/Frameworks"
cp "$BREW_LIB" "$APP_BUNDLE/Contents/Frameworks/"

#Patch the Binary (The "Surgical Fix")
echo "Patching pyodbc paths..."
install_name_tool -change "/usr/local/opt/unixodbc/lib/libodbc.2.dylib" "@rpath/libodbc.2.dylib" "$PYODBC_PATH" 2>/dev/null
install_name_tool -change "/opt/homebrew/opt/unixodbc/lib/libodbc.2.dylib" "@rpath/libodbc.2.dylib" "$PYODBC_PATH" 2>/dev/null
install_name_tool -change "@loader_path/../../../../../../Frameworks/libodbc.2.dylib" "@rpath/libodbc.2.dylib" "$PYODBC_PATH" 2>/dev/null

#Add the search path (RPath)
install_name_tool -add_rpath "@executable_path/../Frameworks/" "$PYODBC_PATH" 2>/dev/null

echo "Generating Styled DMG..."
create-dmg \
  --volname "$APP_NAME Installer" \
  --volicon "src/assets/icon.png" \
  --background "src/assets/background.png" \
  --window-pos 200 120 \
  --window-size 640 480 \
  --icon-size 100 \
  --icon "$APP_NAME.app" 160 240 \
  --hide-extension "$APP_NAME.app" \
  --app-drop-link 480 240 \
  "$APP_NAME-Installer.dmg" \
  "$BUILD_DIR/"

echo "Build Complete: $APP_NAME-Installer.dmg"