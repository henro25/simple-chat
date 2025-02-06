# simple-chat
A simple, client-server chat application that allows users to send and receive text messages.

# Install Requiremnents
1. Create a virutal environment in the simple-chat root directory:
   1. python3.10 -m venv venv
   2. source venv/bin/activate
2. Run `pip install -r requirements` to download required libraries

# Running the client and server
In terminal, run `python -m server.server` from the root directory to start the server.
Then, in another terminal window, run `python -m client.main` from the root directory to start the client.

# Testing
To test in `tests/`, simply cd into `tests` and run: `pytest`
