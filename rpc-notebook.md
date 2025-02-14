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
