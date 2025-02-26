# Engineering Notebook for Simple Chat with RPC

## Goal: Migrating a Chat Application to gRPC

This outline describes how to **re-implement a chat application** (originally using sockets and a custom wire protocol or JSON) with **gRPC** and Protocol Buffers. It covers the **changes required** on both **client and server**, the **steps** to tackle in **logical order**, and **important considerations** regarding data, testing, and overall architecture.

---

## 1. Introduction & Hypothesis

We hypothesize that replacing the raw socket + custom/JSON protocol with **gRPC** will:

- **Simplify** our communication model by leveraging automatically generated stubs and typed RPCs.
- **Reduce** message size via Protocol Buffers’ binary format (often smaller than text/JSON).
- **Improve** developer productivity, because we no longer need to parse or serialize custom wire formats manually.
- **Potentially ease** real-time features like message streaming using gRPC’s server streaming or bidirectional streaming capabilities.

We will confirm these improvements by measuring:

1. **Implementation overhead** (lines of code, time spent).
2. **Performance** (message sizes, network overhead).
3. **Maintainability** (ease of adding new endpoints).

---

## 2. Architecture Changes

### 2.1 From Custom Protocol to gRPC

- **Before**:  
  - A custom protocol parsed using `selectors` in Python, splitting lines and tokens.  
  - Or JSON-based commands using string-based message parsing.

- **After**:  
  - **Define a `.proto` file** describing services and messages.
  - Generate Python **stubs** for both client and server.
  - **Server** uses `grpc.Server(...)` to handle incoming RPC calls.
  - **Client** uses an auto-generated `Stub` class instead of manually connecting a socket.

### 2.2 Data Size Implications

- **Protocol Buffers** produce a binary format typically smaller than JSON.  
- Text-based formats often have repeated separators or syntactic overhead.  
- So we expect a **reduction in data size** on the wire (hypothesis: “up to 30–70% smaller messages,” depending on content).

### 2.3 Real-Time Messaging

- gRPC easily supports:
  - **Server streaming**: Keep a stream open for notifications.
  - **Bidirectional streaming**: Client and server exchange messages continuously on one channel.
- If you do **not** implement streaming, you can do **poll-based** calls to fetch updates at intervals.

---

## 3. What Has Been Implemented So Far

### 3.1 The New Protocol Definition

- A new **`.proto` file** has been created that defines:
  - **Authentication** messages (`LoginRequest`, `RegisterRequest`, `LoginResponse`, etc.).
  - **Chat History** messages (`ChatHistoryRequest`, `ChatHistoryResponse`, and the `Message` type).
  - **Send Message** and **Delete Message** RPCs, with corresponding request and response messages.
  - **Live Updates** via a bidirectional streaming RPC (`UpdateStream`) for push notifications.
  - **Acknowledgement** for push messages.

### 3.2 Integration with Existing Protocols

- One of the really cool things we achieved was integrating **protocol 3.0 (gRPC)** with the existing **protocol 1.0 (custom)** and **protocol 2.0 (JSON)**.
- The client now contains logic that chooses the proper protocol based on configuration. If protocol 3.0 is active, it sends requests using the auto-generated gRPC stubs.

### 3.3 Client-Side gRPC Integration

- A new module, `grpc_client_protocol.py`, was created to encapsulate the gRPC logic on the client side.
- **Key Features:**
  - **Request Handling:** Functions like `send_grpc_request()` determine which RPC to call based on the type of request.
  - **Response Processing:** Specialized functions (e.g., `handle_login_response()`, `handle_chat_history()`) process the structured gRPC responses.
  - **Live Updates:**  
    - A separate thread is launched to handle a bidirectional streaming RPC.  
    - When live updates are received on this background thread, a custom Qt event is posted to the main thread so that UI components can be updated accordingly.

### 3.4 Server-Side gRPC Integration

- A new module, `grpc_server_protocol.py`, was created for the gRPC server implementation.
- **Key Features:**
  - Implements the `ChatServiceServicer` with all RPC endpoints (e.g., `Login`, `Register`, `SendMessage`, `DeleteMessage`, etc.).
  - Integrates with the existing database and client management logic to handle account registration, login, and message delivery.
  - Implements the bidirectional streaming RPC (`UpdateStream`) for live updates, including logic to push messages (such as new chat messages, user updates, or message deletions) to connected clients.
  - Uses a shared RPC send queue to manage messages destined for clients over gRPC.

### 3.5 Concurrency and UI Integration

- **Threading:**  
  - The client launches a separate thread dedicated to managing the streaming RPC for live updates.
  - This ensures that the UI remains responsive while handling real-time communication.
- **Event Handling:**  
  - Upon receiving an update on the live updates thread, a custom Qt event (`LiveUpdateEvent`) is posted to the main thread.
  - The main thread then processes the update, refreshing the UI components (e.g., chat windows, conversation lists).

---

## 4. Lessons Learned and Challenges

- **Socket vs. RPC Integration:**  
  - One challenge was managing the different lifecycles of raw socket connections (for protocols 1.0 and 2.0) versus gRPC streams (protocol 3.0).  
  - We had to ensure that client connections were handled appropriately in both models.
  
- **Threading and UI Updates:**  
  - Integrating background threads for streaming RPC with a Qt-based UI required careful event posting to prevent thread safety issues.
  - Debugging race conditions between the streaming thread and UI updates was particularly time-consuming.

- **Error Handling:**  
  - Handling errors from both synchronous RPC calls and asynchronous stream updates required a robust and unified error handling strategy.
  - We improved our logging and debugging output to better trace issues like unconnected sockets or protocol conversion errors.

---

## 5. Next Steps

1. **Measure Performance:**  
   - Benchmark message sizes between the custom protocols and gRPC.

2. **Expand Functionality:**  
   - Check if there's bugs or other functionalities that need to be completed.

3. **Comprehensive Testing:**  
   - Develop integration tests that simulate concurrent clients interacting over both traditional sockets and gRPC.
   - Automate testing of real-time message delivery and UI event handling.

4. **Documentation & Deployment:**  
   - Finalize documentation to help future developers understand the integration between protocols.
   - Prepare deployment scripts and configuration management for production environments.

---

## Implemented Benchmarking for Message Size

### Overview
We benchmarked two communication protocols—**custom** and **gRPC**—to evaluate differences in Message Size (Data Overhead). The goal was to evaluate which protocol is more efficient and lightweight in handling operations such as: Registering a user, Logging in, Sending a message, Retrieving chat history, Deleting account, Deleting message.
To measure data size, we first directly meassured Protobuf-encoded message size then we measured the data size with transport metadata.

### Hypothesis
- **Custom Protocol Efficiency:** gRPC would have smaller message sizes without metadata, as it employs binary encoding for Protobuf so it should be more compact than our text-based custom protocol. gRPC should have larger datasizes with metadata due to extra metadata overhead.

### Implementation Details
- **Custom Protocol:**
  - **Pros:** 
    - No metadata overhead
  - **Cons:** 
    - Rigid parsing requirements: Each opcode must be precisely caught, redirected, and parsed.
    - More error-prone when handling complex structures.
- **gRPC Protocol:**
  - **Pros:** 
    - Strong type enforcement and automatic serialization.
    - Supports automatic message parsing and structured data transmission.
    - Scales better with complex data structures.
  - **Cons:** 
    - Larger metadata overhead due to Protobuf encoding.
    - Potentially slower due to extra serialization/deserialization steps.

### Observations and Trade-offs
Experimental results are available in the `test/benchmarking_protocols.ipynb` notebook. The graphs shown at the end of the notebook help validate our hypothesis and provide a visual confirmation of the data size differences between the two protocols.
- **Data Size Comparison:**  
    - Withoout metadata: For most operations, gRPC and Custom Protocol had similar message sizes, except for "Send Message", where gRPC was significantly larger. This was most likely due to the message having single field "msg_id" therefore our custom protocol not having field keys at all outperformed gRPC. 
    - With metadata: For all operationsm, gRPC data sizes (including metadata) are approximately 2x to 3x larger than their Custom Protocol counterparts. The extra size in gRPC comes from mostly the structural metadata.
- **Maintenance:** The tight coupling of opcode handling in the custom protocol has led to occasional errors, particularly when expanding functionality. Custom Protocol optimizes for minimal size but sacrifices flexibility.
- **Flexibility vs. Efficiency:** The larger gRPC request size is a cost of using a more structured and type-safe approach. gRPC's additional time cost is justified by built-in reliability and structured communication. Custom Protocol, while faster, is harder to scale with complex data formats.


### Conclusion
Our benchmarking results show a slight trade-off between size efficiency (Custom Protocol) (especially for smaller messages) and scalability/maintainability (gRPC). We conclude that Custom Protocol is best for speed-critical, lightweight messaging apps and gRPC is better for scalable, structured applications with complex data. Moving forward, we might also explore hybrid solutions where Custom Protocol is used for real-time messaging, while gRPC is used for backend services that might balance performance with flexibility.

---

## 6. Summary

In this phase of the project, we:
- Defined a comprehensive Protocol Buffers specification for a chat application.
- Integrated gRPC into an existing chat application, coexisting with legacy protocols.
- Implemented client-side and server-side modules to handle gRPC calls and live update streams.
- Solved challenging issues around multi-threading, event handling, and error management.

The work so far has demonstrated the feasibility and benefits of migrating to gRPC. The next phase will focus on performance optimization, error handling refinement, and expanding the application's features.

## 7. Reflections
We attempt to address the following questions:
- Does the use of this tool make the application easier or more difficult?
  - The use of gRPC makes the application easier as it removes all the manual parsing and message construction logic and instead uses gRPC stubs to call methods. 
  - Additionally, Protobuf must follow a defined structure which prevents inconsistent messages that makes the applicaiton less error prone while having high flexibility for modifications so gRPC makes long-term maintenance easier. We see this most clearly in how new fields can be added to Protobuf messages without breaking compatibility and requiring many changes. 
- How does it change the structure of the client?
  - The client no longer has to format messages and send them over a socket. Instead, the client now uses an auto-generated stub and calls methods directly to interact with the server. The data that is sent to server is more structured as it uses Protobuf and there is no more need to manually format requests or parse responses.
- How does it change the structure of the server?
  - The server doesn’t handle raw sockets manually anymore and gRPC automatically routes incoming requests to the correct function based on the proto definition, and instead of manually parsing data, the server implements gRPC service methods. Previously, the server also had to deal with handling concurrent connections using asyn sockets, but now gRPC is Multi-Threaded by default so the concurrency is built-in. 
-  How does this change the testing of the application?
  - Preivously, to implement unit tests we had to create mock sockets to simulate server responses. Now we can just use a gRPC stub hat allow function calls without real network communication. Errors are also caught not by string matching but by the built-in error handling property of gRPC. 

*End of Notebook Entry*
