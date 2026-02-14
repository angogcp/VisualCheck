# Product Requirements Document (PRD): QC-Check 02

## 1. Executive Summary
**QC-Check 02** is an AI-powered visual inspection system designed for specialty cable manufacturing. It digitizes the quality control process, replacing manual visual checks with a computer-vision-assisted workflow. The system captures high-resolution images of cable ends, analyzes them for defects (scratches, pinhole defects, soldering issues) using unsupervised anomaly detection (PatchCore), and generates digital inspection reports.

## 2. Problem Statement
-   **Manual Variability**: Human inspection is subjective and prone to fatigue, leading to missed defects (false negatives).
-   **Lack of Traceability**: Traditional inspection often lacks digital records of *why* an item was passed or rejected.
-   **Skill Gap**: Training new inspectors to identify subtle defects in specialty cables takes time.

## 3. Goals & Objectives
-   **Standardization**: specific AI models for each cable type to ensure consistent acceptance criteria.
-   **Traceability**: Save every inspection image (OK/NG) with timestamp, cable ID, and AI score.
-   **Efficiency**: Instant (<1s) feedback to the operator.
-   **Simplicity**: Touch-friendly, browser-based UI requiring no technical expertise to operate.

## 4. User Personas
-   **Operator**: Scans barcode, places cable, checks screen for AI verdict, packs or rejects. Needs large buttons, clear signals (Green/Red).
-   **Quality Manager**: Reviews "Gray Zone" images, retrains AI models, exports daily/monthly reports.
-   **Admin**: Manages hardware (camera, lighting), system updates, and backups.

## 5. Functional Requirements

### Phase 1: Capture & Digitalization (Completed)
-   **Camera Feed**: Live WebRTC preview (1280x720) with low latency.
-   **Image Capture**: One-click capture (Spacebar / Touch) with "Flash" effect.
-   **Metadata**: Associate images with unique Cable IDs.
-   **Gallery**: Review recent captures, filter by OK/NG, delete errors.
-   **Reporting**: Dashboard with daily pass rates, total inspection counts.
-   **Storage**: Local file system organization (`data/ok`, `data/ng`) + CSV metadata.

### Phase 2: AI Anomaly Detection (Completed)
-   **Engine**: Anomalib (PatchCore) for few-shot unsupervised learning.
-   **Training**: One-click training on "OK" samples (no labeling of defects required).
-   **Inference**: Real-time anomaly scoring (0-100%) and classification.
-   **Visualization**: (Future) Heatmap overlay showing defect location.
-   **Fallback**: Robust PyTorch inference if hardware acceleration (OpenVINO) is unavailable.

### Phase 3: Automation & Integration (Future)
-   **PLC Interface**: Signal tower light (Green/Red) control via GPIO/Modbus.
-   **Auto-Trigger**: Capture image automatically when cable is detected in ROI.
-   **Multi-Camera**: Simultaneous inspection of both cable ends.

## 6. Non-Functional Requirements
-   **Performance**: Inference time < 1.0 second on standard CPU.
-   **Compatibility**: Windows 10/11 IoT without reliance on cloud APIs (Privacy/Security).
-   **Reliability**: Auto-restart on crash, offline capability.

## 7. Technology Stack
-   **Backend**: Python 3.12, Flask, OpenCV (headless).
-   **AI/ML**: Anomalib 2.2, PyTorch, OpenVINO (optional).
-   **Frontend**: HTML5, Vanilla JS, CSS3 (Glassmorphism), WebRTC.
-   **Database**: File-system based (Images) + CSV/SQLite (Metadata).
