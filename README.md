# simple-chat
A simple, client-server chat application that allows users to send and receive text messages.

# Setting Up
1. Download this repo by running `git clone https://github.com/henro25/simple-chat.git` in terminal
2. Create a virutal environment in the simple-chat root directory:
   1. `python -m venv venv`
   2. `source venv/bin/activate`
3. Run `pip install -r requirements.txt` to download required libraries
4. To use gRPC as the communication protocol, run `python -m grpc_tools.protoc -I. --python_out=. --grpc_python_out=. chat_service.proto`

# Running the client and server

Starting the server: in terminal and from the root directory, run `python -m server.server`

Note: the console will return the server IP address and port number that clients can connect to. The server connects to the machine's IP address and a random open port number.
- Specifically, the console will print: `Listening on ('<server_IP_address>', <port_num>)`

Starting the client: 

1. In another terminal window and from the root directory, activate the environment again `source venv/bin/activate`
2. Run from the root directory `python -m client.main <protocol_version> <server_ip> <server_port>`
   1. Usage: use 1.0 for custom protocol version, 2.0 for JSON protocol version, and 3.0 for gRPC protocol
   2. Example: `python -m client.main 1.0 127.0.0.1 65432`

# Testing
To run the unit tests, simply run: `pytest`
