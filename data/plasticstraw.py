import os

#function to clear file content
def clear_file():
    # Open file in write mode which truncates content
    with open('countrydata.ttl', 'w') as file:
        pass

#execute if script is run directly
if __name__ == "__main__":
    try:
        clear_file()
        print("File content cleared successfully")
    except Exception as e:
        print(f"Error: {e}")