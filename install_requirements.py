import subprocess
import sys
import os

def install_requirements():
    """
    Install required packages for the application
    """
    print("Installing required packages...")
    
    # Update pip first if needed
    try:
        print("Checking for pip updates...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "--upgrade", "pip"])
        print("Pip has been upgraded to the latest version.")
    except subprocess.CalledProcessError:
        print("Warning: Unable to upgrade pip. Continuing with existing version.")
    
    # Define the packages we need
    requirements = [
        "flask==2.3.3",
        "flask-sqlalchemy==3.1.1",
        "flask-migrate==4.0.4",
        "flask-login==0.6.2", 
        "flask-mail==0.10.0",
        "sqlalchemy-utils==0.40.0",
        "werkzeug==2.3.7",
        "python-dotenv==1.0.0",
        "wtforms==3.0.1",
        "gunicorn==21.2.0"
    ]
    
    # Install each package
    failed_packages = []
    for package in requirements:
        print(f"Installing {package}...")
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install", package])
        except subprocess.CalledProcessError:
            print(f"Warning: Failed to install {package}")
            failed_packages.append(package)
    
    if failed_packages:
        print("\nThe following packages failed to install:")
        for package in failed_packages:
            print(f"  - {package}")
        print("\nPlease check the error messages above and resolve any issues.")
        print("You may need to install these packages manually.")
    else:
        print("\nAll required packages installed successfully!")
        print("\nSQLite database will be created automatically when you run the application.")
        
    print("\nYou can now run the application with:")
    print("python app.py")

if __name__ == "__main__":
    install_requirements()
