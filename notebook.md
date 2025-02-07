# Engineering Notebook for Simple Chat

## Goal

Develop a messaging system using a client-server architecture with two different wire protocols (custom & JSON).

---

## Timeline

- **2/5/24**  
  - Begin brainstorming and planning the structure, logic, and specification **[COMPLETED]**

- **2/6/24**  
  - Start implementing the UI, client-server socket code, and SQLite Database **[IN_PROGRESS]**

---

## Summary of Key Requirements

1. **User Authentication:**  
   - Account creation  
   - Login

2. **Listing Accounts**

3. **Messaging:**  
   - Sending messages  
   - Receiving messages

4. **Message Storage and Retrieval**

5. **Account and Message Deletion**

6. **GUI Client Interface**

---

## Requirements and Structure Outline

### Language

- **Python** (fastest to build)

### Repository Structure

- **/server** — Server-side code
- **/client** — Client-side code
- **/docs** — Documentation
- **/tests** — Unit and integration tests
- **README.md** — Project overview and setup instructions


### Custom Protocol

- **Communication:** Use strings with a naive key/value pair implementation.
- **Client → Server Examples:**
  - **Log in:**
    - Send: `User [name]`
    - Send: `Password [hashed password]`
  - **Send message:**
    - Send: `Send [destination user] [source user] [message]`

### UI Flow

- **Sequence:** Login screen → Contact list → Chat window  
- **Initial Front End:** Tkinter (switched later to PyQt due to UI issues)

---

## Detailed Features

### 1. Account Creation & Login

#### Creating an Account

- **If the username exists:**
  - Prompt for the password.
  - If the hashed password (using `hashlib`) matches the stored value, proceed to the contact list.
  - Otherwise, display an error message and prompt the user to try again.
  - *[Optional]*: After multiple failed attempts (e.g., 3), offer a password reset or account recovery option.

- **If the username does not exist:**
  - Prompt the user to register by providing a password.
  - Hash the password and store the username/password pair securely.
    - **Note:** The initial implementation will use a simple dictionary. Later, this can be scaled to persistent storage with Redis or SQLite.

#### Logging into an Account

- Use a login name and password.
- If the username doesn’t exist or the password is incorrect, display an error.
- A successful login should also display the number of unread messages.

---

### 2. Listing Accounts (Contact List)

- Display all accounts with the number of unread messages.
- Allow filtering accounts using a text wildcard search.
- Support pagination or iteration if there are too many accounts to display at once.

---

### 3. Messaging

#### Sending a Message

- **Online Recipient:**  
  Deliver immediately if the recipient is logged in.
  
- **Offline Recipient:**  
  Store the message until the recipient logs in.
  
- **Idea:**  
  Each user has a dedicated receive queue. A dictionary maps login names to their queues, and messages are sent by specifying the recipient's login name.

#### Reading Messages

- Display undelivered messages.
- Allow the user to specify the number of messages they want delivered at once.

#### Deleting a Message

- Once deleted, the message is removed for both the sender and the recipient.

#### Deleting an Account

- Remove the username and password from the accounts table.
- Optionally, insert these details into an `old_accounts` table to prevent reuse of the username.

---

## Data Flow Outline

### Client GUI Initialization

- Establish a socket connection with the server before rendering the UI.

### Creating an Account

1. **Username Check:**  
   - User inputs a login name and presses enter.
   - The login name is sent to the server to verify that it does not already exist.
   - The server responds with a status (valid/invalid).

2. **Password Registration:**  
   - User inputs a password.
   - The username and hashed password are sent to the server.
   - The server stores the details in the accounts table and returns a success message along with a list of other usernames and their unread message counts.

### Logging into an Account

1. User sends the login name and password.
   - **Error Handling:**  
     - If the username is not found, the server returns an error.
     - If the password is incorrect, an error is returned.
   - **Success:**  
     - The server sends back a success message and a list of other users with their respective unread message counts.

### Chat Conversation & Messaging Panel

- **Chat History Request:**
  - When opening a conversation, the client requests the chat history (including sender, recipient, and the number of messages desired).
  - **Server:**  
    - Filters the messages table by sender and recipient.
    - Sorts messages by timestamp.
    - Sends the requested messages back to the client.
    - Each message is timestamped using the server’s clock.
  - **Client:**  
    - *[TODO]* Implement pagination for message viewing.

- **Real-Time Messaging:**
  - For every new message, the client sends:
    - Message content
    - Message UUID
    - Recipient info
  - **Update Options:**
    - **Push Mechanism:** The server pushes updates immediately.
    - **Polling:** Clients poll the server periodically for new updates.

### Deleting Messages and Accounts

- **Delete Message:**
  - The client GUI includes a delete button beside each message.
  - Upon clicking, the message ID is sent to the server for deletion.
  - The server may notify the other client about the deletion in real time.

- **Delete Account:**
  - A dedicated button sends a deletion request (with username) to the server.
  - **Note:**  
    Associated messages are not deleted to preserve the conversation history for other users.

---

## Wire Protocol Specification

### General Message Format

- [protocol version] [action] [data]


### Error Codes

- `USER_TAKEN`  = 1  
- `USER_DNE`    = 2  
- `WRONG_PASS`  = 3  
- `DB_ERROR`    = 4  
- `UNSUPPORTED_VERSION` = 5  
- `UNSPECIFIED_COMMAND` = 6  

### Server-to-Client Communication

- **Error Message:**
  - **Format:** `1.0 ERROR [error code]`
  - **Example:** `1.0 ERROR 1`
  
- **User List & Unread Count:**
  - **Format:** `1.0 USERS [list of users]`
  - **Example:** `1.0 USERS bridgetma04 6 jwaldo 1 ewang 2`
  
- **Chat History:**
  - **Format:**  
    `1.0 MSGS [user1] [num msgs] [msg ID, num words, msg1] [msg ID, num words, msg2] ...`
  - **Example:**  
    `1.0 MSGS henro 2 111 2 hello bridget 112 3 it's henry ! 113 1 Hi!`
  
- **Real-Time Message:**
  - **Format:** `1.0 PUSH_MSG [recipient] [msg]`
  - **Example:** `1.0 PUSH_MSG bridgetma04 hello bridget`
  
- **Real-Time Delete Message:**
  - **Format:** `1.0 DEL_MSG [sender] [msg ID]`
  - **Example:** `1.0 DEL_MSG bridgetma04 2241`

### Client-to-Server Communication

- **Create New Account:**
  - **Format:** `1.0 CREATE [username] [hashed_password]`
  - **Example:** `1.0 CREATE henro 2620`
  
- **Login:**
  - **Format:** `1.0 LOGIN [username] [hashed_password]`
  - **Example:** `1.0 LOGIN henro 2620`
  
- **Request Chat History:**
  - **Format:** `1.0 READ [username] [other user]`
  - **Example:** `1.0 READ henro bridgetma04`
  
- **Acknowledge Read Message:**
  - **Format:** `1.0 READ_ACK [username] [message ID]`
  - **Example:** `1.0 READ_ACK henro 2241`
  
- **Send Message:**
  - **Format:** `1.0 SEND [message ID] [sender] [recipient] [message]`
  - **Example:** `1.0 SEND 2241 henro bridgetma04 hello!`
  
- **Delete Message:**
  - **Format:** `1.0 DEL_MSG [sender] [recipient] [message ID]`
  - **Example:** `1.0 DEL_MSG henro bridgetma04 2241`
  
- **Delete Account:**
  - **Format:** `1.0 DEL_ACC [username]`
  - **Example:** `1.0 DEL_ACC bridgetma04`

---

## Implementation Progress

### UI Implementation

- **Completed:**
  1. **Main Menu:** Landing page with options to create an account or login.
  2. **Login Page:** Contains username and password fields with submit and back buttons.
  3. **Registration Page:** Contains username and password fields with submit and back buttons.

- **Upcoming:**
  - Develop a messaging page (and its associated UI logic) for users after a successful login.  
    *Note: The messaging page will initially be blank.*

> **Notes:**  
> - Initially attempted using Tkinter; however, labels and text entries were not displaying properly (while buttons worked fine).  
> - After extensive debugging (~2 hours), the decision was made to switch to PyQt.

### SQLite Database

- **Purpose:**  
  - Handle account registration and login.
- **Status:**  
  - Logic for account registration and login is implemented.
  - Tests for these functionalities have been created.

### Client-Server Socket Code

- **Server:**
  - Developed a multi-client server to handle message routing and persistence (inspired by Jim’s spinning servicing connections code).
  
- **Client:**
  - A client class has been created to be passed around in the UI pages.
  
- **Current Setup:**  
  - Using a loopback address.
  
> **Notes:**  
> - Testing was challenging due to issues with relative vs. absolute imports.  
> - Currently using relative imports for better compatibility during testing, treating both server and client as modules.

---

*This document is a living record. Future updates and refinements will be made as the project evolves.*
