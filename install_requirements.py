import subprocess
import sys
import os

def install_requirements():
    """
    Install required packages for the application
    """
    print("Installing required packages...")
    
    # Define the packages we need
    requirements = [
        "flask",
        "flask-sqlalchemy",
        "flask-login", 
        "flask-mail",
        "mysql-connector-python",  # Use this instead of MySQLdb
        "sqlalchemy-utils",
        "werkzeug"
    ]
    
    # Install each package
    for package in requirements:
        print(f"Installing {package}...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", package])
    
    print("\nAll required packages installed successfully!")
    print("\nYou can now run the application with:")
    print("python app.py")

if __name__ == "__main__":
    install_requirements()
