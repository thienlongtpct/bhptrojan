import os


# This module lists the environment variables
def run(**args):
    print("[*] In environment module.")
    return str(os.environ)