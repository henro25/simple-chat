# Overall Architecture Documentation

This document describes the architecture of our client–server chat application. It covers the main components on both the client and server sides, their interactions, and important design decisions. The application supports two wire protocols: a custom, string-based protocol (version 1.0) and a JSON-based protocol (version 2.0).

---

## 1. Client-Side Architecture

### Components

- **UI Pages**  
  The client’s graphical user interface is built using **PyQt5** and organized as several distinct pages:
  - **Main Menu (main_menu.py):**  
    The landing page that provides options for account creation and login.
  - **Login Page (login_page.py):**  
    Contains a login form for entering username and password.
  - **Registration Page (register_page.py):**  
    Provides a form for creating a new account.
  - **Conversation List Page (list_convos_page.py):**  
    Displays a list of chat conversations along with unread message counts. It allows filtering, sorting, and selection of a conversation.
  - **Messaging Page (messaging_page.py):**  
    The chat interface where messages are sent, received, and can be deleted. It includes a scrollable chat history area, message input, and controls for real-time updates.

- **Client Core (client.py)**  
  This module handles the socket connection with the server. It manages asynchronous communication using non-blocking sockets and Python’s **selectors** module. The client class is responsible for:
  - Establishing and maintaining the connection.
  - Sending requests and receiving responses.
  - Routing incoming messages to the appropriate UI pages.

- **Protocol Interface (protocol_interface.py)**  
  Acts as a dispatcher that selects the correct protocol module based on the current protocol version (configured in `configs/config.py`):
  - **Custom Protocol (version 1.0):**  
    Uses plain text messages with a fixed format.
  - **JSON Protocol (version 2.0):**  
    Encapsulates message data as a JSON object with fields like `opcode` and `data`.

- **Configurations (config.py)**  
  Contains global settings, such as the server’s IP/port, current protocol version (`CUR_PROTO_VERSION`), supported versions, and error codes. The file centralizes important constants for both the client and server.

### Interaction Flow

1. **Initialization:**  
   When the client application starts, it establishes a socket connection to the server and initializes the UI using a `QStackedWidget` to manage multiple pages.
   
2. **User Authentication:**  
   - **Account Creation:** The registration page sends a “CREATE” request with the username and hashed password.
   - **Login:** The login page sends a “LOGIN” request. Upon success, the server responds with a list of conversations (with unread counts), and the client navigates to the conversation list page.
   
3. **Conversation and Messaging:**  
   - The conversation list page displays available chats, allowing the user to select one.
   - The messaging page is then used to send messages (via the “SEND” command) and request chat history.
   - Real-time messaging is supported by push notifications (e.g., `PUSH_MSG`, `DEL_MSG`) that update the UI as new messages or deletions occur.

4. **Protocol Handling:**  
   All outgoing requests and incoming responses are processed by the protocol interface. Depending on the current protocol version:
   - Version **1.0** uses string-based commands.
   - Version **2.0** uses JSON objects with the fields `opcode` and `data`.

---

## 2. Server-Side Architecture

### Components

- **Main Server (server.py)**  
  The entry point for the server application. It:
  - Listens for incoming connections using a non-blocking socket.
  - Uses the **selectors** module to manage multiple client connections concurrently.
  - Dispatches incoming messages to the appropriate protocol handler based on the protocol version.

- **Database Management (database.py)**  
  Uses **SQLite** to manage persistent data, including:
  - **Accounts:** User registration, authentication, and deactivation.
  - **Messages:** Storing, retrieving, and deleting chat messages.
  - **Conversation Data:** Querying conversations and managing unread message counts.
  
- **Protocol Handlers**  
  Similar to the client, the server supports two protocol modules:
  - **Custom Protocol (custom_protocol.py):** Handles string-based messages.
  - **JSON Protocol (json_protocol.py):** Processes JSON formatted messages.
  
  The server’s protocol interface parses each incoming message, executes the requested action (e.g., login, send message, delete message), and sends back a response using the appropriate protocol.

- **Utilities (utils.py)**  
  Contains helper functions for logging, error handling, and tracking active clients (to support real-time messaging).

### Interaction Flow

1. **Connection Management:**  
   - The server listens on a specified port.
   - New client connections are accepted and registered for event notifications using **selectors**.
   
2. **Message Processing:**  
   - Incoming data is buffered until a complete message (terminated by a newline) is received.
   - The protocol version is determined from the message prefix, and the appropriate protocol handler processes the message.
   - The server performs operations such as user authentication, storing messages, fetching chat history, and updating unread counts.
   
3. **Real-Time Communication:**  
   - For messages like real-time pushes (e.g., `PUSH_MSG` and `DEL_MSG`), the server checks if the target client is online (tracked via an active clients dictionary).
   - If so, the server immediately pushes the update to the recipient.

---

## 3. Wire Protocol Overview

### Custom Protocol (Version 1.0)

- **Format:**  
  `1.0 [COMMAND] [data]`
- **Usage:**  
  Used for all message exchanges when `CUR_PROTO_VERSION` is set to `"1.0"`.

### JSON Protocol (Version 2.0)

- **Format:**  
  `2.0 {"opcode": "<COMMAND>", "data": ["arg1", "arg2", ...]}`
- **Usage:**  
  When using JSON protocol, every message is prefixed with `2.0` followed by a JSON object containing:
  - **opcode:** A string indicating the command.
  - **data:** An array of strings representing the message parameters.

---

## 4. Summary of Interactions

- **Client Initialization:**  
  - Establish socket connection.
  - Load UI pages and set initial protocol based on configuration.
  
- **User Actions:**  
  - Registration/Login requests trigger server-side authentication and account management.
  - Selection of a conversation prompts retrieval of chat history.
  - Sending and receiving messages are handled in real time with immediate UI updates.

- **Protocol Abstraction:**  
  Both client and server use a protocol interface to abstract away the details of the wire format. This design allows easy switching between custom and JSON protocols without changing the core application logic.

---

This architecture provides a modular and scalable approach to building a real-time chat application. The separation of concerns between the UI, networking, protocol processing, and database management ensures that each component can be maintained and updated independently.
