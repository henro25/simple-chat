# Simple Chat – Overall Architecture

Below is an overall architecture document of our client–server chat application. It covers the main components on both the client and server sides, their interactions, and important design decisions. The application supports two wire protocols: a custom, string-based protocol (version 1.0) and a JSON-based protocol (version 2.0).

---

## 1. High-Level Overview

The application follows a **classic client–server** model:

1. **Server**  
   - Listens for incoming client connections using Python’s `selectors`.
   - Handles authentication, message storage, retrieval, and account operations.
   - Communicates with a SQLite database for persistence.

2. **Client**  
   - A PyQt-based desktop GUI that allows users to:
     - **Register** or **log in**.
     - View conversations and unread counts.
     - Send and receive messages in real time.
     - Delete messages or their account.
   - Exchanges data with the server over a TCP socket.
   - Supports two wire protocols—**Custom** (1.0) or **JSON** (2.0)—based on user configuration.

3. **Database (SQLite)**  
   - Maintains tables for:
     - **Accounts** (username, hashed password, and deactivation flag)  
     - **Messages** (sender, recipient, message content, timestamps, read/unread status)  
   - Provides queries to fetch or update user data, chat histories, unread counts, etc.

---

## 2. Major Components

### 2.1 Client-Side Components

1. **Main GUI (PyQt)**  
   - **`main_menu.py`**: Landing page with “Create Account” and “Login” options.  
   - **`login_page.py`** and **`register_page.py`**: Forms to submit credentials for account login or creation.  
   - **`list_convos_page.py`**: Shows a list of conversations, including total unread counts. Offers search/filter and account deletion.  
   - **`messaging_page.py`**: Main chat interface for sending and receiving messages and for loading additional chat history.

2. **`client.py`**  
   - Manages the **TCP connection** to the server:
     - Uses non-blocking I/O (`selectors`) to send/receive data asynchronously.
     - Stores references to the active GUI pages to trigger UI updates (e.g., new message arrivals).
   - Maintains user-specific info such as `username`, the currently opened conversation, etc.
   - Invokes *protocol-specific* serialization or parsing methods before sending/receiving data.

3. **Protocol Interface (Client-Side)**  
   - **`protocol_interface.py`**: For each high-level operation (login, registration, send message, etc.), it selects the **Custom** or **JSON** protocol implementation.  
   - **`custom_protocol`** / **`json_protocol`**: Each module defines how to construct and parse messages. The system can switch protocols by setting `CUR_PROTO_VERSION` in the config.
     - **Custom Protocol (version 1.0):**  
    Uses plain text messages with a fixed format.
     - **JSON Protocol (version 2.0):**  
       Encapsulates message data as a JSON object with fields like `opcode` and `data`.

---

### 2.2 Server-Side Components

1. **`server.py`**  
   - Main entry point for running the server:
     - Binds to a socket (`SERVER_HOST`, `SERVER_PORT`) and listens for client connections.
     - Uses `selectors` to handle multiple clients concurrently.
   - For each connected client:
     - Reads incoming data, splits it by newline, and **detects the protocol** (1.0 vs. 2.0).
     - Calls the corresponding protocol handler (custom or JSON).
     - Gathers outgoing data to send back via non-blocking writes.

2. **Protocol Modules (Server-Side)**  
   - **`custom_protocol`**  
     - Defines string-based message parsing and serialization (e.g., `1.0 LOGIN username password`).  
   - **`json_protocol`**  
     - Defines JSON-based message parsing (e.g., `{"opcode":"LOGIN","data":["username","password"]}`).
   - Both modules rely on shared logic to coordinate with the database or to push real-time updates to recipients.

3. **Database Integration**  
   - **`database.py`**  
     - Manages the SQLite database connection and schema (`accounts`, `messages`).  
     - Common queries:
       - **Register / verify** accounts (checking for duplicates, passwords, deactivation status).
       - **Store / fetch** chat messages (plus marking messages read or unread).
       - **Delete** messages or deactivate accounts.  
     - All data is stored in `chat.db`.  
   - **`utils.py`**  
     - Tracks `active_clients` (username → socket mapping) for real-time pushes (e.g., if user A sends a message to user B who is online, the server pushes it immediately).

---

## 3. Data Flows & Interactions

Below is a brief look at the core flows:

1. **User Registration**  
   - Client’s “Register” page collects `username` + `password`, hashes the password, and invokes `protocol_interface.create_registration_request(...)`.
   - Server checks if username already exists. If not, it inserts a row in the `accounts` table.
   - Returns success or error code to the client. If successful, the client transitions to the conversations list.

2. **User Login**  
   - Client’s “Login” page sends `username` + hashed `password`.
   - Server validates credentials against `accounts`.  
   - On success, sends back a list of existing conversations (plus unread counts).  
   - Client displays the **ListConvosPage**.

3. **Listing Conversations**  
   - The server fetches the relevant data from `messages` and `accounts`.
   - The client displays each conversation with the number of unread messages. Also shows the total unread count on top.

4. **Chat Messaging**  
   1. **Sending**:  
      - Client uses `create_send_message_request(...).`  
      - Server stores the message in `messages`.  
      - If the recipient is online, the server immediately pushes a **“new message”** notification.  
      - Server replies with an acknowledgement containing the new message ID.  
   2. **Receiving**:  
      - If the user is in that conversation, the client immediately appends the new message to the chat window.  
      - Otherwise, the unread count is updated so that user sees the new unread message next time they check.

5. **Loading More Chat History**  
   - The client can request older messages (e.g., pressing “Load Chat”).  
   - Server queries older entries from the `messages` table (by message ID, descending) and returns them.  
   - Client prepends them to the conversation display and maintains the scroll position.

6. **Deleting a Message**  
   - The client sends `create_delete_message_request(msg_id).`  
   - Server removes the message from `messages`.  
   - If the other user is online and also has that message in their UI, the server pushes a **“delete message”** event so they can remove it from the chat window.

7. **Deleting an Account**  
   - User can click “Delete Account.”  
   - Client sends a deletion request.  
   - Server sets `deactivated` in `accounts`. The user is effectively logged out and cannot log back in.  
   - The server returns a confirmation, and the client navigates back to the Main Menu.

---

## 4. Notable Implementation Details

1. **Non-Blocking I/O**  
   - Both server and client use Python’s `selectors` to handle concurrent communication without multiple threads.

2. **Protocol Selection**  
   - A **single configuration** variable `CUR_PROTO_VERSION` dictates whether the client (and server) uses the custom wire format or JSON format.
   - The code in `protocol_interface.py` (client) and the server’s logic in `service_connection` will detect and dispatch the correct protocol routines.

3. **SQLite Database**  
   - Stores **user accounts** (with a `deactivated` flag) and **messages** (with `unread` as an integer).  
   - The schema is initialized on server startup via `database.initialize_db()`.
   - Queries for:
     - **Registration/Login** (`register_account`, `verify_login`)  
     - **Messages** (`store_message`, `get_recent_messages`, `delete_message`)  
     - **Conversation & unread** retrieval (`get_conversations`).

4. **Real-Time Updates**  
   - The server keeps a dictionary `active_clients` that maps `username → socket`.  
   - Whenever a message or deletion occurs, if the recipient (or other relevant party) is in `active_clients`, the server sends a push message so the UI updates immediately.

5. **Security Considerations**  
   - Passwords are hashed client-side using `hashlib.sha256(...)`.  
   - The server does not store raw passwords, only their hashes.  
   - This is a minimal approach: no SSL/TLS or advanced crypto is used in the sample code.

---

## 5. Summary

In summary, **Simple Chat** is a full-stack, event-driven application designed around a **client–server** pattern:

- A **PyQt** client GUI that manages multiple pages (Main Menu, Login/Register, Conversation List, Chat).  
- A **non-blocking** Python server that delegates requests and updates a persistent **SQLite** database.  
- **Two protocols** (Custom 1.0 or JSON 2.0) for message serialization, switchable by a single config variable.

This design provides a foundation that is:
- **Modular** (UI, client logic, server logic, DB operations, and protocols all separated).
- **Extensible** (additional features, alternative protocols, or changes to the message schema can be integrated with minimal disruption).
- **Maintainable** (clear boundaries between data access and user interface code, plus well-defined internal protocol interfaces).

**End of Architecture Overview**
