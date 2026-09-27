\# ARCHITECTURE.md: Connect Four Extensible Platform



\## 1. Vision \& Purpose

A modular, extensible web platform for the Connect Four game (and generalized M,N,K variations) written in Python. The platform supports human-vs-human, human-vs-bot, and bot-vs-bot matches, with a pluggable rule/modifier system (teleports, collapsing shelves, board shifts).



\## 2. Layered Architecture

The project strictly enforces separation of concerns:



1\. \*\*Domain / Core Engine (`src/engine/`)\*\*

&#x20;  - Pure Python 3.11+. Zero external dependencies (no FastAPI, no DB imports).

&#x20;  - Deterministic state machine.

&#x20;  - Core concepts:

&#x20;    - `Board`: Grid data structure and spatial representation.

&#x20;    - `Rules`: Turn management, gravity application, win/draw condition checks.

&#x20;    - `Modifiers`: Pipeline/hooks (`before\_move`, `after\_move`, `on\_turn\_end`).

&#x20;  - 100% test coverage via `pytest`.



2\. \*\*Application / API Layer (`src/api/`)\*\*

&#x20;  - Framework: \*\*FastAPI\*\*.

&#x20;  - Input/Output data schemas powered by \*\*Pydantic v2\*\*.

&#x20;  - Manages game sessions (in-memory storage for MVP, pluggable to DB later).

&#x20;  - Exposes REST API for both the Web Frontend and external Bots.



3\. \*\*Presentation / Web Layer (`src/web/`)\*\*

&#x20;  - Lightweight frontend interacting exclusively via HTTP REST (or optional SSE/polling).



\## 3. Modifiers Philosophy (Open-Closed Principle)

\- The base engine must support classic $(M, N, K)$ rules without modifier logic overhead.

\- Modifiers are implemented as pluggable strategy objects/middleware hooks:

&#x20; - `on\_piece\_drop(board, col, player)`

&#x20; - `on\_turn\_finished(board, current\_state)`

\- Core engine invokes modifier hooks without hardcoded assumptions about specific modifier mechanics.



\## 4. Coding Standards \& Tooling

\- \*\*Typing:\*\* Strict Python type hints (`mypy --strict` compliant).

\- \*\*Code Style:\*\* PEP 8 enforced via `ruff`.

\- \*\*Testing:\*\* Unit tests written using `pytest`. Test cases follow the Arrange-Act-Assert (AAA) pattern.

\- \*\*LLM Context Rule:\*\* When generating code, generate strictly modular files with full type annotations, docstrings, and zero framework leakage into `src/engine/`.

