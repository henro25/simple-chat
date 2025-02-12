# Wire Protocol Specification

This document details the wire protocol used for communication between the server and client. Every message follows a consistent format, allowing both sides to correctly interpret commands, data, and errors. The protocol supports real-time notifications, error handling, account operations, messaging, and more.

---

## General Message Format

Every message sent over the wire adheres to the following structure: `[protocol_version] [action] [data]`

- **protocol_version**: Indicates the version of the protocol (e.g., `1.0`). This allows for backward compatibility and future enhancements.
- **action**: A command or event indicator (such as `ERROR`, `LOGIN`, `SEND`), which tells the receiver what type of message it is.
- **data**: One or more parameters that provide additional context or information for the action.

---

## Protocol Versions

- **Custom Protocol (String)**:  
  Uses protocol version **1.0**. All messages following the custom protocol are sent as plain strings using the format detailed above.

- **JSON Protocol**:  
  Uses protocol version **2.0**. Messages are sent in JSON format as described below. The parsing is extremely similar to custom protocol.

---

## Error Codes

When an error occurs, the server uses specific numeric codes to represent common issues. Here are the error codes along with their meanings:

- **`USER_TAKEN`** = 1  
  The username provided is already in use.
- **`USER_DNE`** = 2  
  The specified user does not exist.
- **`WRONG_PASS`** = 3  
  The password provided is incorrect.
- **`DB_ERROR`** = 4  
  A database error occurred.
- **`UNSUPPORTED_VERSION`** = 5  
  The protocol version used is not supported.
- **`UNSPECIFIED_COMMAND`** = 6  
  The command received is not recognized.
- **`ID_DNE`** = 7  
  The specified message or user ID does not exist.

---

## Server-to-Client Communication

The server sends various types of messages to the client. Each type of message is formatted to include all necessary information for the client to process the event.

### 1. Error Message

When an error occurs, the server notifies the client with an error message.

- **Format:** `1.0 ERROR [error code]`
- **Example:** `1.0 ERROR 1`
  - This indicates a `USER_TAKEN` error (error code `1`).

---

### 2. User List & Unread Count

To update the client with a list of users and their corresponding unread message counts, the server uses this format:

- **Format:** `1.0 USERS [page code] [client username] [user1] [unread_count1] [user2] [unread_count2] ...`
- **Example:** `1.0 USERS 10 henro bridgetma04 6 jwaldo 1 ewang 2`
  - **`10`**: Page code identifying the view or segment.
  - **`henro`**: The current client’s username.
  - Followed by pairs: `bridgetma04` has 6 unread messages, `jwaldo` has 1, and `ewang` has 2.

---

### 3. Chat History

When the client requests chat history, the server responds with a detailed message containing the messages and relevant metadata.

- **Format:** `1.0 MSGS [page code] [number of unread messages] [flag] [num_msgs] [msg1 details] [msg2 details] ...`
  - - **`page code`**: Identifier for the conversation or page.
  - **`number of unread messages`**: Count of unread messages in the conversation.
  - **`flag`**: Indicates if the sender of the earliest message is the same as the recipient (`1` for yes, `0` for no).
  - **`num_msgs`**: Number of messages being sent.
  - **`msg details`**: For each message, the details include the message ID, the number of words in the message, and the message text itself.
- **Example 1:** (Earliest message sender **is** the recipient)
  - `1.0 MSGS 13 1 3 111 2 hello bridget 112 3 it's henry ! 113 1 Hi!`
- **Example 2:** (Earliest message sender **is not** the recipient)
  - `1.0 MSGS 12 0 2 2 hello bridget 3 it's henry ! 1 Hi! 1 2241 2 Hello Back`

---

### 4. Client Sent Message Acknowledgement

After the client sends a message, the server acknowledges the receipt of that message.

- **Format:** `1.0 ACK [msg ID]`
  - A `msg ID` of `-1` indicates that the recipient is deactivated.
- **Example:** `1.0 ACK 2241`

---

### 5. Real-Time Send Message

For real-time communications, the server can push messages to the client immediately upon receipt.

- **Format:** `1.0 PUSH_MSG [sender] [msg_id] [msg]`
- **Example:** `1.0 PUSH_MSG henro 111 hello bridget`

---

### 6. Real-Time Delete Message

When a message is deleted, the server informs the client with this notification.

- **Format:** `1.0 DEL_MSG [sender of message] [msg ID] [read status]`
  - **`read status`**: `1` if the message was unread, `0` if it had already been read.
- **Example:** `1.0 DEL_MSG henro 2241 0`

---

### 7. Real-Time Create Account

When a new user account is created, the server sends a notification to the client.

- **Format:** `1.0 PUSH_USER [username]`
- - **Example:** `1.0 PUSH_USER henro`

---

### 8. Delete Account Acknowledgement

Upon account deletion, the server sends a simple acknowledgement message.

- **Format:** `1.0 DEL_ACC`
- **Example:** `1.0 DEL_ACC`


---

## Client-to-Server Communication

The client initiates various actions by sending commands to the server. The following sections detail each type of client-to-server message.

### 1. Create New Account

To register a new account, the client sends a create account command with the username and a hashed password.

- **Format:** `1.0 CREATE [username] [hashed_password]`
- **Example:** `1.0 CREATE henro 2620`

---

### 2. Login

For user authentication, the client sends a login request with the username and hashed password.

- **Format:** `1.0 LOGIN [username] [hashed_password]`
- **Example:** `1.0 LOGIN henro 2620`

---

### 3. Request Chat History

To fetch a conversation's history with another user, the client sends a read request. The request includes a starting message ID (or `-1` to fetch the most recent messages) and the number of messages desired.

- **Format:** `1.0 READ [username] [other user] [oldest_msg_id] [number of messages requested]`
  - **Note:** When first loading the messaging page, `oldest_msg_id` is set to `-1` to indicate that the most recent messages should be retrieved.

- **Example:** `1.0 READ henro bridgetma04 121 10`

---

### 4. Send Message

To send a message to another user, the client uses the following format:

- **Format:** `1.0 SEND [sender] [recipient] [message]`
- **Example:** `1.0 SEND henro bridgetma04 hello!`

---

### 5. Acknowledge Read Message

After a message is read, the client sends an acknowledgment back to the server. This helps update the message's read status.

- **Format:** `1.0 READ_ACK [num_msgs]`
- **Examples:**
- If the user is currently in the conversation:
  ```
  1.0 READ_ACK 2
  ```
- If the user is not in the active conversation:
  ```
  1.0 READ_ACK 0
  ```

---

### 6. Delete Message

To delete one or more messages, the client sends a delete message command including all relevant message IDs.

- **Format:** `1.0 DEL_MSG [message IDs...]`
- **Example:** `1.0 DEL_MSG 2241 2622`

---

### 7. Delete Account

To remove an account, the client issues a delete account command with the username.

- **Format:** `1.0 DEL_ACC [username]`
- **Example:** `1.0 DEL_ACC bridgetma04`

---

### 8. Real-Time Delivered Message Acknowledgement

After a real-time message is delivered, the client sends an acknowledgment to confirm receipt.

- **Format:** `1.0 REC_MSG [msg_id]`
- **Example:** `1.0 REC_MSG 11`

---

## JSON Protocol Specification

When using protocol version **2.0**, messages are sent as a JSON object immediately following the protocol number. The JSON object contains the following fields:

- **opcode**: Specifies the type of message or command.
- **data**: A list of words representing the message data.

**Example JSON Protocol Message:**

```json
{
  "opcode": "SOME_OPCODE",
  "data": ["word1", "word2", "word3"]
}
```

In practice, the transmitted message starts with the protocol version 2.0, followed by the JSON payload, which signifies that the JSON-based protocol is being used.

---

## Summary

This wire protocol is designed to provide a structured and consistent approach to communication between the client and server. Key aspects include:

- **Versioning:**  
Every message starts with a protocol version (e.g., `1.0`) for future-proofing.

- **Action-Based Commands:**  
The `action` field dictates how the rest of the message should be interpreted.

- **Data Payload:**  
Commands carry a payload that includes all necessary information for performing the requested operation, from error codes and user details to message contents.

- **Real-Time Communication:**  
Both client and server can send real-time notifications (e.g., new messages, account creation, deletions) to keep the UI up-to-date.

Adhering strictly to these formats ensures reliable and error-resistant communication across your application.
