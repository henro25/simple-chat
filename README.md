# simple-chat
A simple, client-server chat application that allows users to send and receive text messages.

# Setting Up
1. Create a virutal environment in the simple-chat root directory:
   1. `python3.10 -m venv venv`
   2. `source venv/bin/activate`
2. Run `pip install -r requirements.txt` to download required libraries

# Running the client and server

Starting the server: in terminal and from the root directory, run `python -m server.server`

Note: currently, if you want to run on your actual IP address, enter the command `ipconfig getifaddr en0` (for macOS) in terminal and find your IP address. Then, replace the SERVER_HOST in configs/config.py with this IP address, making sure it is still in single quotes!

Starting the client: 

1. In another terminal window and from the root directory, activate the environment again `source venv/bin/activate`
2. Run from the root directory `python -m client.main`

# Testing
To run the unit tests, simply run: `pytest`
