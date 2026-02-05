# LakeTrace Architecture

## Component Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                        Your Application                          │
│                    (Spark Job / Notebook)                        │
└────────────────────┬────────────────────────────────────────────┘
                     │
                     ▼
            ┌────────────────────┐
            │  get_logger(name)  │
            │  LakeTraceLogger   │
            └────────┬───────────┘
                     │
         ┌───────────┼───────────┐
         │           │           │
         ▼           ▼           ▼
    ┌────────┐  ┌───────┐  ┌──────────┐
    │ Config │  │Runtime│  │ Security │
    │Manager │  │Detect │  │ Features │
    └────────┘  └───────┘  └──────────┘
         │           │           │
         └───────────┼───────────┘
                     │
                     ▼
        ┌────────────────────────┐
        │   Core Logger Engine   │
        │  (Message Processing)  │
        └────────┬───────────────┘
                 │
        ┌────────┼────────┐
        │        │        │
        ▼        ▼        ▼
    ┌─────┐ ┌──────┐ ┌──────────┐
    │Format│ │Filter│ │ Handlers │
    └─────┘ └──────┘ └─────┬────┘
                           │
           ┌───────────────┼───────────────┐
           │               │               │
           ▼               ▼               ▼
      ┌─────────┐     ┌──────────┐   ┌──────────┐
      │ File    │     │ Rotation │   │Retention │
      │ Handler │     │ Manager  │   │ Manager  │
      └─────────┘     └──────────┘   └──────────┘
           │
      ┌────┴────┐
      │          │
      ▼          ▼
   ┌──────┐  ┌──────────┐
   │Local │  │Compress  │
   │Files │  │(gz, bz2) │
   └──────┘  └──────────┘
      │
      └─────────────────┐
                        │
            ┌───────────┴──────────┐
            │                      │
            ▼                      ▼
        ┌────────┐            ┌──────────────┐
        │ Stdout │            │   Lakehouse  │
        │ Emit   │            │   Upload     │
        │(Job    │            │  (End-of-run)│
        │ Logs)  │            │              │
        └────────┘            └──────────────┘
```

---

## Core Components Detail

### 1. Configuration Layer
```
┌──────────────────────────────┐
│    LakeTrace Config          │
├──────────────────────────────┤
│ • log_dir                    │
│ • rotation strategy          │
│ • retention policy           │
│ • compression type           │
│ • log level                  │
│ • json output                │
│ • async mode (enqueue)       │
│ • error catching             │
└──────────────────────────────┘
```

### 2. Runtime Detection
```
┌──────────────────────────────┐
│   Runtime Detection          │
├──────────────────────────────┤
│ Detects:                     │
│ • Fabric (OneLake)           │
│ • Databricks                 │
│ • Local Python               │
│ • PySpark active             │
│                              │
│ Provides:                    │
│ • Platform type              │
│ • Environment info           │
│ • Spark session metadata     │
└──────────────────────────────┘
```

### 3. Security Features
```
┌──────────────────────────────┐
│   Security Layer             │
├──────────────────────────────┤
│ • Field Whitelisting         │
│ • PII Masking                │
│ • Data Leak Detection        │
│ • Sensitive Redaction        │
│ • Log Integrity (SHA256)     │
│ • Encryption (Fernet)        │
│ • File Permissions (0o600)   │
└──────────────────────────────┘
```

### 4. Message Processing
```
┌──────────────────────────────┐
│   Core Logger Processing     │
├──────────────────────────────┤
│ Input:  log message + args   │
│         │                    │
│         ▼                    │
│     Format message           │
│     Add context              │
│     Add metadata             │
│     Security checks          │
│         │                    │
│         ▼                    │
│ Output: Structured record    │
└──────────────────────────────┘
```

### 5. Output Sinks
```
┌─────────────────────────────────────┐
│         Output Sinks                │
├─────────────────────────────────────┤
│                                     │
│ File Sink (with Rotation):          │
│   • Size-based rotation             │
│   • Time-based rotation             │
│   • Custom rotation                 │
│   • Automatic compression           │
│   • Retention cleanup               │
│                                     │
│ Stdout Sink:                        │
│   • Console output                  │
│   • Job log visibility              │
│                                     │
│ Lakehouse Sink (Optional):          │
│   • End-of-run upload               │
│   • Single write (no append)        │
│   • Fabric/Databricks support       │
└─────────────────────────────────────┘
```

---

## Data Flow

```
User Code
   │
   ├─→ logger.info("message", key=value)
   │
   ▼
┌─────────────────────────────────┐
│  Config Lookup                  │
│  • Get settings                 │
│  • Apply defaults               │
└──────────┬──────────────────────┘
           │
           ▼
┌─────────────────────────────────┐
│  Runtime Context                │
│  • Detect platform              │
│  • Add environment info         │
│  • Add process info             │
└──────────┬──────────────────────┘
           │
           ▼
┌─────────────────────────────────┐
│  Security Checks                │
│  • Leak detection               │
│  • Field validation             │
│  • PII masking                  │
│  • Data redaction               │
└──────────┬──────────────────────┘
           │
           ▼
┌─────────────────────────────────┐
│  Format Record                  │
│  • JSON or text                 │
│  • Add timestamp                │
│  • Add context fields           │
│  • Add integrity hash           │
└──────────┬──────────────────────┘
           │
           ├──────────────────┬───────────────┐
           │                  │               │
           ▼                  ▼               ▼
      File Sink          Stdout Sink    Async Queue
           │                  │          (optional)
           ▼                  ▼               │
      Local File         Console        Background
      + Rotation                        Thread
      + Retention                           │
      + Compress                           ▼
           │                            Batch Write
           │
           └──────────────────┬────────────────┘
                              │
                    (On demand or schedule)
                              │
                              ▼
                         Lakehouse Upload
                         (e.g., OneLake)
```

---

## Feature Layers

### Layer 1: Core Logging
- Basic message logging
- Timestamp addition
- Level classification

### Layer 2: Context & Metadata
- Bound context fields
- Runtime platform detection
- Process/execution info
- Hostname and PID

### Layer 3: Formatting
- JSON structure
- Plain text alternative
- Custom formatters
- Message escaping

### Layer 4: Security
- PII detection and masking
- Credential redaction
- Field whitelisting
- Data leak detection
- Log integrity hashing
- Field encryption

### Layer 5: Storage Management
- File rotation (size, time, custom)
- Retention policies (count, time)
- Compression (gzip, bzip2)
- Async queue (enqueue mode)
- Error handling and catching

### Layer 6: Output
- Local file I/O
- Stdout emission (for job logs)
- Lakehouse upload (end-of-run)
- No remote append (performance)

---

## Thread Safety & Concurrency

```
┌──────────────────────────────────────┐
│   Thread-Safe Operations             │
├──────────────────────────────────────┤
│                                      │
│  Logger Instance:                    │
│    • Single shared logger            │
│    • Safe for concurrent access      │
│    • Lock-protected critical paths   │
│                                      │
│  Context Binding:                    │
│    • Per-thread local storage        │
│    • Thread-safe field propagation   │
│                                      │
│  File I/O:                           │
│    • Queue-based writes              │
│    • Atomic file operations          │
│    • No race conditions               │
│                                      │
│  Spark Executors:                    │
│    • Driver-only logging             │
│    • No executor logging             │
│    • No distributed serialization    │
│                                      │
└──────────────────────────────────────┘
```

---

## Configuration Hierarchy

```
┌──────────────────────────────┐
│   Built-in Defaults          │
│   (sensible for all use)      │
└────────────┬─────────────────┘
             │
             ▼
┌──────────────────────────────┐
│   Environment Variables      │
│   (override defaults)        │
└────────────┬─────────────────┘
             │
             ▼
┌──────────────────────────────┐
│   User Config Dict           │
│   (explicit overrides)       │
└────────────┬─────────────────┘
             │
             ▼
┌──────────────────────────────┐
│   Active Logger Config       │
│   (merged final config)      │
└──────────────────────────────┘
```

---

## See Also

- [README.md](../README.md) - Main documentation
- [docs/SECURITY.md](SECURITY.md) - Security features
- [docs/TESTING.md](TESTING.md) - Testing guide
- [laketrace/core_logger.py](../laketrace/core_logger.py) - Core implementation
- [laketrace/logger.py](../laketrace/logger.py) - Main API
