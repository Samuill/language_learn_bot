# -*- coding: utf-8 -*-
import importlib
import sys
import subprocess
import os

def check_and_install_packages():
    """Check and install required packages."""
    # List of required packages
    required_packages = [
        "telebot",
        "pandas",
        "googletrans==4.0.0-rc1",  # Specific version to avoid bugs in newer versions
        "apscheduler",
        "requests",
        "psutil"  # For PID checking in main.py
    ]
    
    missing_packages = []
    
    # Check if each package is installed
    for package in required_packages:
        package_name = package.split("==")[0]  # Extract package name without version
        try:
            importlib.import_module(package_name)
            print(f"✅ {package} is already installed")
        except ImportError:
            print(f"❌ {package} is not installed")
            missing_packages.append(package)
    
    # Install missing packages
    if missing_packages:
        print(f"\nInstalling missing packages: {', '.join(missing_packages)}")
        try:
            # Use pip to install missing packages
            subprocess.check_call([sys.executable, "-m", "pip", "install"] + missing_packages)
            print("\nAll required packages have been installed successfully!")
        except subprocess.CalledProcessError as e:
            print(f"\n❌ Error installing packages: {e}")
            print("Please install the missing packages manually and try again.")
            sys.exit(1)
    else:
        print("\nAll required packages are already installed!")

def run_main():
    """Run the main program."""
    main_file = os.path.join(os.path.dirname(__file__), "main.py")
    if not os.path.exists(main_file):
        print(f"❌ Main file not found: {main_file}")
        sys.exit(1)
    
    print("\nStarting the main program...\n")
    try:
        # Run the main program
        sys.path.insert(0, os.path.dirname(__file__))
        import main
        main.main()
    except Exception as e:
        print(f"❌ Error running main program: {e}")
        sys.exit(1)

if __name__ == "__main__":
    print("Checking dependencies before starting the bot...\n")
    check_and_install_packages()
    run_main()
