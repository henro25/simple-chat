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

# 2/5/24

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
- **/configs** - Configurations (Connection Info)
- **/tests** — Unit and integration tests
- **README.md** — Project overview and setup instructions


### Custom Protocol [DEPRECATED]

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

- [protocol_version] [action] [data]

### Error Codes

- `USER_TAKEN`  = 1  
- `USER_DNE`    = 2  
- `WRONG_PASS`  = 3  
- `DB_ERROR`    = 4  
- `UNSUPPORTED_VERSION` = 5  
- `UNSPECIFIED_COMMAND` = 6  
- `ID_DNE` = 7

### Server-to-Client Communication

- **Error Message:**
  - **Format:** `1.0 ERROR [error code]`
  - **Example:** `1.0 ERROR 1`
  
- **User List & Unread Count:**
  - **Format:** `1.0 USERS [list of (users, number of unread messages)]`
  - **Example:** `1.0 USERS bridgetma04 6 jwaldo 1 ewang 2`
  
- **Chat History:**
  - **Format:**  
    `1.0 MSGS [1 if user who sent the ealiest message is same as the user receiving this history else 0] [num msgs] [msg ID (if 1), num words, msg1] [msg ID (if 1), num words, msg2] ...`
  - **Example:**  
    - User this message is being sent to is user1: `1.0 MSGS 1 3 111 2 hello bridget 112 3 it's henry ! 113 1 Hi!`
    - User this message is being sent to is NOT user1: `1.0 MSGS 0 2 2 hello bridget 3 it's henry ! 1 Hi! 1 2241 2 Hello Back`

- **Client Sent Message Acknowledgement**
  - **Format:** `1.0 ACK [msg ID]`
  - **Example:** `1.0 ACK 2241`
  
- **Real-Time Send Message:**
  - **Format:** `1.0 PUSH_MSG [recipient] [msg]`
  - **Example:** `1.0 PUSH_MSG bridgetma04 hello bridget`
  
- **Real-Time Delete Message:**
  - **Format:** `1.0 DEL_MSG [msg IDs]`
  - **Example:** `1.0 DEL_MSG 2241 2622`

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
  
- **Send Message:**
  - **Format:** `1.0 SEND [sender] [recipient] [message]`
  - **Example:** `1.0 SEND henro bridgetma04 hello!`
  
- **Acknowledge Read Message:**
  - **Format:** `1.0 READ_ACK [num_msgs that was sent to this user that was read]`
  - **Example:** `1.0 READ_ACK 2` if user is in current conversation with sender, and `1.0 READ_ACK 0` if user is NOT in current conversation with sender
  
- **Delete Message:**
  - **Format:** `1.0 DEL_MSG [message IDs]`
  - **Example:** `1.0 DEL_MSG 2241 2622`
  
- **Delete Account:**
  - **Format:** `1.0 DEL_ACC [username]`
  - **Example:** `1.0 DEL_ACC bridgetma04`

---

# 2/6/24

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
- **Tables**
  - accounts
  - old_accounts
  - chat_history
    - Fields: msg id, timestamp, sender, recipient, msg content
  - num_unread_msgs
    - Fields: recipient, sender, number of unread messages

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

#### Questions to Answer:

1. How do we want to pagination our results -- what do we want the UI chat to look like
   1. This will influence how we want to create custom wire
   2. How many messsages do we want to send from server to client at once?
      1. ANSWER: up to 20
      2. Should we multithread or simple keep polling to send real-time updates?
   3. We should diagram the information flow and edge cases of live streaming messages to another user!
2. Come to a concensous on how to manage read/unread information flow
   1. Assume they read number of messages sent by the server (we can always increase num msgs sent by server)
3. Delete Accounts should need another database to make sure the same account name is not used twice? Should we even specify this?
4. How to delete messages:
   1. Client: has a text box that the user can write message IDs into and press a button to delete
   2. How do we create message IDs?
      1. ANSWER: server keeps a counter that increases by 1 every time a message is sent between two people
         1. Once a server receives a chat message, not only does it increment that counter, but it also sends the message ID back to the client
            1. Client displays message ID next to every message they sent
         2. Delete mesasge from database
         3. If the recipient is online, send a real time delete to that recipient
         4. To handle set of messages, simply use commas to separate message IDs to delete
5. What data structures should the client have?
   1. Chat Conversations (LIST)
      1. Element: (user, num_unreads)
   2. Chat Histories (DICT)
      1. Key: Other User
      2. Value: [
        (msg id, user sent, message content)
      ]

#### TODOs:

1. [DONE] Substitute error codes with their actual information [Henry]
   1. [DONE] Handle this in `/configs`
2. [DONE] Implement Conversation List Page UI [Henry]
   1. [DONE] Data Structure: Chat Conversations (LIST)
   2. [DONE] Sort by most recent conversation, then alphabetical if no chat history
   3. [DONE] Show num unread msgs next to each user
      1. [DONE] Make each a button
   4. [DONE] Scroll feature
   5. [DONE] Search Bar
   6. [DONE] Display total unreads
3. Implement Chat Page UI [Bridget]
   1. [DONE] Data Structure: Chat Histories (LIST)
   2. [DONE] Scroll feature
   3. Back button
      1. Send msg to server to reset its num msgs sent chat counter
      2. Redirect back to conversation list page
   4. request more chat history
      1. [DONE] Button
      2. Update num unread
   5. Delete messages
      1. Show msg ID of YOUR messages
      2. [DONE] Text Entry to types msgs to delete
      3. [DONE] Button to send msg IDs for deletion to the server
   6. Set max msg length
   7. Pulling user down when a live message is sent
      1. Send back msg if in current chat page with user who sent the live message
4. [DONE] Create num_unread_mgs db in server [Henry/Bridget]
   1. [DONE] Handle num_unread_msgs logic (related to protocol)
5. Handle protocol parsing in `/protocols` [Henry/Bridget]
6. Delete Account (UI + Protocol) [Bridget]
7. Implement Old Accounts DB in server [Bridget]
    1.  Add logic to server for invalid registration or logins

#### Later TODOs:
1. JSON (version 2.0)
2. dynamically increasing num msgs sent by server when requested chat history
3. Hashing the passwords
4. Tests
5. Documentation
6. Modify the config so that messages can be sent to a real host (not loopback aka `localhost`)
7. Clean All Accounts funtion on the server

---

# 2/7/24

## Implementing Conversation List Page UI
  **Client-side**:
  1. [DONE] Data Structure: Chat Conversations (LIST)
  2. [DONE] Sort by most recent conversation (actually no need since we will be receiving users in most recent order)
  3. [DONE] Show num unread msgs next to each user
    1. [DONE] Make each a button
  4. [DONE] Scroll feature [can be click to see next set of users too if too tricky]
  5. [DONE] Search Bar
  6. [DONE] Display total unreads
  **Server-side**:
  1. [DONE] Create table `num_unread_msgs`, logic for handling get convo list (with num unreads) and updating num unreads, and tests
    - Columns: recipient, sender, timestamp, number of unread messages
  2. [DONE] Add protocol functionality to handle get convo list request
     1. [DONE] Added message parsing and logic to load chat conversations with unreads
     2. [DONE] Server is integrated with client

---

# 2/8/24

## Implementing Messaging Page UI
  **Client-side**:
  1. [DONE] Data Structure: Chat History (List) combined with Message Info (Dict). Message info is a map that maps message ids to sender and text.
  2. [DONE] Send messages and messages being stored in server database
  3. [DONE] Delete messages and messages being deleted from server database
  4. [DONE] Get chat history from server and populating chat box with history when click on conversation
  **Server-side**:
  1. [DONE] Create table `messages`, logic for handling get chat histroy and updating chat history, and tests
    - Columns: id, sender, recipient, message, timestamp
  2. [DONE] Add protocol functionality to handle get chat history request
     1. [DONE] Added message parsing and logic to load chat history
     2. [DONE] Server is integrated with client
  3. [DONE] Add protocol functionality to handle get send message request
  4. [DONE] Add protocol functionality to handle get delete message request
  **Changed Wire Protocol**:
  1. Modified wording of chat history protocol such that it is clearer
  2. Modified client and server side delete message protocol to only include message id
  3. Added error code 7 for message id DNE when trying to delete

*This document is a living record. Future updates and refinements will be made as the project evolves.*
