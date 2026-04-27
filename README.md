# iLibrary App 
![iLibraryApp](https://legner.beer/iLibrary-morph.png)

Whether you are managing legacy systems or modernizing your workflow, 
iLibrary eliminates command-line friction, helping you handle essential 
IBM i tasks with greater speed and efficiency.

Experience a faster way to secure your data by generating Savefiles
(SAVF) instantly and downloading them directly to your local machine. 
iLibrary bridges the gap between the green screen and your desktop, 
turning complex backup tasks into a simple, one-click process.

## Features
* **Quick SAVF Creation:** Generate Savefiles directly from the UI without manual command entry.
* **Direct Download:** One-click transfer of Savefiles from the IBM i to your local machine.
* **User Lookup:** Rapid search functionality for system user profiles.

## Download it
Download [v0.0.4](https://github.com/legnerbeer/iLibraryApp/releases/tag/v.0.0.4)


## Build the app

## Quick Start & Build Guide

Follow these steps to set up your environment and build the application.

### 1. Clone & Prepare
Download the source files to your local machine and navigate to the project's root directory.

### 2. Initialize Virtual Environment
Create a clean, isolated environment to manage your dependencies:
```bash
python -m venv .venv
````
### 3. Install Dependencies
Install all required libraries once the virtual environment is active:

```Bash
pip install -r ./requirements.txt
````

### macOS
```
python3 ./build_tool.py macos
```
### Linux
```
python3 ./build_tool.py linux
```
### Windows
```
python3 ./build_tool.py windows
```
