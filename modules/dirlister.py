import os


# This module lists the files in the current directory
def run(**args):
    print("[*] In dirlister module.")
    files = os.listdir(".")
    return str(files)