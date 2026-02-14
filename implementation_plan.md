# QC-Check 02 — Implementation Plan & Roadmap

## Phase 1: Capture Station (✅ Completed)
**Status**: deployed to production (v1.0)
**Core Features**:
-   [x] **WebRTC Camera Interface**: Low-latency preview, 1280x720 capture.
-   [x] **Image Storage**: Local file system, organized by date/status.
-   [x] **Metadata**: Cable ID, Timestamp, OK/NG Label saved to CSV.
-   [x] **Gallery**: Filtering, Search, Deletion.
-   [x] **Reporting**: Daily statistics, Pass Rate visualization.

## Phase 2: AI Integration (✅ Completed)
**Status**: deployed to production (v1.1)
**Core Features**:
-   [x] **Python 3.12 Migration**: Unified environment for Flask & AI.
-   [x] **Anomalib Engine**: PatchCore implementation for unsupervised learning.
-   [x] **Training Pipeline**: `train()` API to model "OK" samples.
-   [x] **Inference API**: Real-time anomaly scoring (PyTorch fallback).
-   [x] **Viewer UI**: "AI判定" button, Score display, Color-coded badges.

## Phase 3: Automation & Scaling ( 🚧 Planned )
**Status**: in planning
**Objectives**:
1.  **Hardware Integration**:
    -   [ ] Connect PLC/Relay to signal tower lights (Green=OK, Red=NG).
    -   [ ] Implement foot-pedal or sensor trigger for hands-free capture.
2.  **Advanced AI**:
    -   [ ] **Heatmap Overlay**: Visualize exact defect location on image.
    -   [ ] **Auto-Training**: Schedule nightly retraining on new validated data.
3.  **Admin Features**:
    -   [ ] **User Management**: Operator vs Admin roles.
    -   [ ] **Model Versioning**: Rollback to previous AI models.
    -   [ ] **Audit Logs**: Track who changed labels or deleted images.

## Architecture Overview
```mermaid
graph TD
    User[Operator] -->|Browser| UI[Web Interface]
    UI -->|API| Flask[Flask Backend (Python 3.12)]
    Flask -->|Capture| Cam[WebRTC / Camera]
    Flask -->|Inference| AI[Anomalib / PyTorch]
    AI -->|Load| Model[PatchCore Model]
    Flask -->|Store| FS[File System (Images)]
    Flask -->|Log| DB[CSV / SQLite Metadata]
```

## Technical Debt / Maintenance
-   **OpenVINO Export**: Investigate Windows permission issues for faster inference.
-   **Unit Tests**: Add coverage for `ai_engine.py` edge cases.
-   **Backup Strategy**: Implement auto-backup of `data/` to network drive.
