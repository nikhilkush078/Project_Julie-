# 🤖 Project Julie: The Interactive Emotion Bot

[![Python](https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![Flask](https://img.shields.io/badge/Flask-000000?style=for-the-badge&logo=flask&logoColor=white)](https://flask.palletsprojects.com/)
[![Arduino](https://img.shields.io/badge/-Arduino-00979D?style=for-the-badge&logo=Arduino&logoColor=white)](https://www.arduino.cc/)
[![Status](https://img.shields.io/badge/Status-Active-brightgreen?style=for-the-badge)]()

> [cite_start]**Project Julie** is a social robotics platform that transforms a standard smartphone into a responsive, emotive "face" for a 4-wheel robotic chassis[cite: 2, 3]. [cite_start]By leveraging a local web server, the bot can talk, show expressions, and interact in real-time[cite: 2].

---

## 🚀 Key Features

* [cite_start]**🎭 Dynamic Expressions:** Stream high-quality eye animations and videos to the bot's "face" using MJPEG streaming[cite: 4, 38].
* [cite_start]**🔊 Remote Voice:** Trigger synchronized audio playback on the mobile speaker directly from the laptop console[cite: 58].
* [cite_start]**👁️ Live Vision:** Monitor the bot's surroundings via a live feed using DroidCam or IP-Cam integration[cite: 5, 26].
* [cite_start]**⚡ Low Latency Control:** Uses Server-Sent Events (SSE) for near-instant command dispatch between the host and the bot[cite: 56].

---

## 🏗️ System Architecture

[cite_start]The project is divided into three distinct phases to ensure smooth interaction and control[cite: 28].

### 💻 1. Host Control (Laptop)
[cite_start]The "brain" of the operation runs a **Tkinter GUI** and a **Flask Backend**[cite: 30, 32].
* [cite_start]**Video Selection:** Choose animations that OpenCV processes into frames[cite: 37].
* [cite_start]**Network Broadcast:** Frames are mapped to a local URL (e.g., `/video_feed`) for the bot to access[cite: 38].

### 📱 2. Bot Face (Mobile)
[cite_start]A smartphone is mounted on the chassis and acts as the interactive interface[cite: 8].
* [cite_start]**Handshake:** The mobile browser connects to the laptop's IP and port[cite: 46].
* [cite_start]**Bypass Protocol:** A simple user tap enables "Silent Audio Start" to satisfy browser security and allow remote sound[cite: 47].

### 🛠️ 3. Physical Hardware
* [cite_start]**Chassis:** 4-wheel drive system[cite: 3].
* [cite_start]**Controller:** Arduino connected to the same network or via radio control[cite: 25].

---

## 🛠️ Tech Stack

| Component | Technology |
| :--- | :--- |
| **Language** | Python 3.x |
| **GUI** | Tkinter |
| **Web Framework** | Flask |
| **Vision** | OpenCV, DroidCam |
| **Communication** | SSE (Server-Sent Events) |

---

## 🎮 How to Launch

1.  [cite_start]**Start the Host:** Run the main Python script on your laptop[cite: 36].
2.  [cite_start]**Network Setup:** Ensure both the laptop and smartphone are on the same Wi-Fi[cite: 4, 46].
3.  [cite_start]**Client Connection:** Enter the generated IP address into the mobile browser[cite: 23].
4.  [cite_start]**Engage:** Tap the mobile screen to enable media, then control animations and audio from the Tkinter dashboard[cite: 43, 56].

---

## ✍️ Author
**Sanchit Gupta**
[cite_start]*Electrical Engineering* [cite: 59]

---
[cite_start]*Developed for Technical Documentation 2026* [cite: 59]
