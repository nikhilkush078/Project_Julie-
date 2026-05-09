import os
import io
import json
import queue
import threading
import time
import socket
import cv2
from PIL import Image, ImageTk
import tkinter as tk
from tkinter import ttk, messagebox
from flask import Flask, Response, render_template_string, send_from_directory, request

VIDEOS_DIR = "videos"
AUDIO_DIR = "audios"   # <-- put mp3/wav/ogg files here
HTTP_PORT = 8080
VIDEO_WIDTH = 920
VIDEO_HEIGHT = 640

# Global frame storage for streaming (video)
current_frame_jpeg = None
frame_lock = threading.Lock()

# ----------------------------
# Audio event pub/sub (for phones)
# ----------------------------
_audio_clients = []             # list[queue.Queue]
_audio_clients_lock = threading.Lock()
_last_audio_event = None        # remember last event (optional replay on new connections)

def _broadcast_audio_event(event: dict):
    global _last_audio_event
    with _audio_clients_lock:
        dead = []
        for q in _audio_clients:
            try:
                q.put_nowait(event)
            except Exception:
                dead.append(q)
        for d in dead:
            if d in _audio_clients:
                _audio_clients.remove(d)
    _last_audio_event = event

class VideoController:
    def __init__(self):
        self.cap = None
        self.current_video = None
        self.playing = False
        self.loop = True
        self.lock = threading.Lock()

    def open_video(self, path):
        with self.lock:
            if self.cap is not None:
                self.cap.release()
            cap = cv2.VideoCapture(path)
            if not cap.isOpened():
                raise IOError(f"Cannot open video: {path}")
            self.cap = cap
            self.current_video = path
            self.playing = True

    def read_frame(self):
        with self.lock:
            if self.cap is None:
                return None, None
            ret, frame = self.cap.read()
            if not ret:
                if self.loop:
                    self.cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                    ret, frame = self.cap.read()
                else:
                    self.playing = False
                    return None, None
            fps = self.cap.get(cv2.CAP_PROP_FPS) or 24.0
            return frame, fps

    def stop(self):
        with self.lock:
            self.playing = False
            if self.cap:
                self.cap.release()
                self.cap = None
            self.current_video = None

controller = VideoController()

# Flask app
app = Flask(__name__)

# ----------------------------
# HTML (phone shows ONLY the video; audio is hidden)
# ----------------------------
INDEX_HTML = """
<!doctype html>
<html>
<head>
  <title>Live Video Stream</title>
  <meta name="viewport" content="width=device-width, initial-scale=1.0, user-scalable=no">
  <meta name="apple-mobile-web-app-capable" content="yes">
  <style>
    html, body {
      margin: 0; padding: 0; height: 100%; background: black; overflow: hidden;
      -webkit-user-select:none; -webkit-touch-callout:none;
      font-family: system-ui, -apple-system, Segoe UI, Roboto, Arial, sans-serif;
    }
    #overlay {
      position: fixed; top: 0; left: 0; width: 100%; height: 100%;
      background: rgba(0,0,0,0.85); color: white;
      display: flex; justify-content: center; align-items: center; flex-direction: column;
      font-size: 20px; cursor: pointer; z-index: 9999; user-select:none; text-align:center; padding: 24px;
    }
    #overlay small { opacity: 0.85; margin-top: 8px; font-size: 14px; }
    #stream {
      width: 100vw; height: 100vh;
      object-fit: contain;
      display: none;
      background: black;
    }
    /* Hidden audio element (no UI on phone) */
    #audio-player { display: none; }
  </style>
</head>
<body>
  <div id="overlay">
    <div>📺 Tap to enter fullscreen & start video</div>
    <small>Audio is remote-controlled from the laptop.</small>
  </div>
  <img id="stream" src="" alt="Video Stream" />
  <audio id="audio-player" preload="auto"></audio>

  <script>
    const overlay = document.getElementById('overlay');
    const stream = document.getElementById('stream');
    const audioPlayer = document.getElementById('audio-player');
    let evtSource = null;

    function startSSE() {
      if (evtSource) return;
      evtSource = new EventSource("{{ url_for('audio_events') }}");
      evtSource.onmessage = (e) => {
        try {
          const msg = JSON.parse(e.data || "{}");
          if (msg.type === "play" && msg.file) {
            const url = "{{ url_for('serve_audio', filename='__DUMMY__') }}".replace("__DUMMY__", encodeURIComponent(msg.file));
            // cache-buster
            const finalUrl = url + "?t=" + Date.now();
            // Ensure audio can play
            try { audioPlayer.pause(); } catch(e){}
            audioPlayer.src = finalUrl;
            audioPlayer.play().catch(()=>{ /* if blocked, will play on next user gesture */});
          }
        } catch (err) {
          console.warn("Bad SSE message:", err);
        }
      };
      evtSource.onerror = () => {
        // Try to reconnect after a short delay
        try { evtSource.close(); } catch(e){}
        evtSource = null;
        setTimeout(startSSE, 1500);
      };
    }

    overlay.addEventListener('click', () => {
      // Request fullscreen
      const el = document.documentElement;
      if (el.requestFullscreen) el.requestFullscreen();
      else if (el.webkitRequestFullscreen) el.webkitRequestFullscreen();
      else if (el.msRequestFullscreen) el.msRequestFullscreen();

      // Start streaming (video only)
      stream.src = "{{ url_for('video_feed') }}";
      stream.style.display = 'block';
      overlay.style.display = 'none';

      // "Unlock" audio autoplay policies with a short silent audio
      audioPlayer.src = "{{ url_for('silence_wav') }}";
      audioPlayer.play().catch(()=>{ /* ignore */});

      // Start listening for remote audio commands
      startSSE();
    });
  </script>
</body>
</html>
"""

@app.route('/')
def index():
    cur = controller.current_video or "None"
    cur = os.path.basename(cur) if cur != "None" else cur
    return render_template_string(INDEX_HTML, current=cur)

def mjpeg_generator():
    global current_frame_jpeg
    while True:
        with frame_lock:
            frame = current_frame_jpeg
        if frame:
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')
        time.sleep(0.02)

@app.route('/video_feed')
def video_feed():
    return Response(mjpeg_generator(),
                    mimetype='multipart/x-mixed-replace; boundary=frame')

# -------- Serve audio files (phone will fetch these when laptop triggers) --------
@app.route('/audios/<path:filename>')
def serve_audio(filename):
    return send_from_directory(AUDIO_DIR, filename)

# -------- Tiny silent WAV to unlock audio policies on first tap --------
_SILENCE_WAV_BYTES = None
def _make_silence_wav(duration_sec=0.2, rate=44100, sampwidth=2, channels=1):
    import wave, struct
    buf = io.BytesIO()
    with wave.open(buf, 'wb') as w:
        w.setnchannels(channels)
        w.setsampwidth(sampwidth)  # 2 bytes = 16-bit
        w.setframerate(rate)
        frames = int(duration_sec * rate)
        silence_frame = struct.pack('<h', 0)  # 16-bit PCM silence
        w.writeframes(silence_frame * frames)
    return buf.getvalue()

@app.route('/silence.wav')
def silence_wav():
    global _SILENCE_WAV_BYTES
    if _SILENCE_WAV_BYTES is None:
        _SILENCE_WAV_BYTES = _make_silence_wav()
    headers = {
        "Content-Type": "audio/wav",
        "Cache-Control": "no-store"
    }
    return Response(_SILENCE_WAV_BYTES, headers=headers)

# -------- SSE: push audio play commands to phones --------
def _audio_event_stream():
    q = queue.Queue()
    with _audio_clients_lock:
        _audio_clients.append(q)
        last = _last_audio_event
    # Optional: send last event so late joiners catch up once
    if last:
        try:
            yield f"data: {json.dumps(last)}\n\n"
        except Exception:
            pass
    try:
        # Heartbeat to keep connection alive
        last_ping = time.time()
        while True:
            try:
                item = q.get(timeout=5.0)
                yield f"data: {json.dumps(item)}\n\n"
            except queue.Empty:
                # Send a ping every ~20s
                if time.time() - last_ping > 20:
                    yield "event: ping\ndata: {}\n\n"
                    last_ping = time.time()
    except GeneratorExit:
        pass
    finally:
        with _audio_clients_lock:
            if q in _audio_clients:
                _audio_clients.remove(q)

@app.route('/audio_events')
def audio_events():
    headers = {
        "Content-Type": "text/event-stream",
        "Cache-Control": "no-cache",
        "Connection": "keep-alive",
        # Helpful if behind proxies that buffer (not critical on dev server)
        "X-Accel-Buffering": "no",
    }
    return Response(_audio_event_stream(), headers=headers)

def run_flask():
    import logging
    logging.getLogger('werkzeug').setLevel(logging.ERROR)
    app.run(host="0.0.0.0", port=HTTP_PORT, threaded=True, use_reloader=False)

class VideoApp(tk.Tk):
    def __init__(self, video_files, audio_files):
        super().__init__()
        self.title("Video Player + LAN Streamer")
        self.geometry("1200x820")

        self.fullscreen = False  # Track fullscreen state

        self.video_frame = ttk.Frame(self)
        self.video_frame.pack(side="left", fill="both", expand=True)

        self.canvas = tk.Canvas(self.video_frame, width=VIDEO_WIDTH, height=VIDEO_HEIGHT, bg='black')
        self.canvas.pack()

        self.controls_frame = ttk.Frame(self, width=300)
        self.controls_frame.pack(side="right", fill="y")

        ip = get_local_ip()
        stream_url = f"http://{ip}:{HTTP_PORT}/"
        ttk.Label(self.video_frame, text=f"Stream URL: {stream_url}", foreground="blue").pack(pady=4)

        # -------- Video buttons (unchanged behavior) --------
        ttk.Label(self.controls_frame, text="🎬 Videos", font=("Segoe UI", 11, "bold")).pack(anchor="w", padx=6, pady=(6,2))
        if video_files:
            for idx, vf in enumerate(video_files[:10]):
                btn = ttk.Button(self.controls_frame, text=f"Play {idx+1}: {os.path.basename(vf)}",
                                 command=lambda p=vf: self.play_video(p))
                btn.pack(fill='x', pady=2, padx=6)
        else:
            ttk.Label(self.controls_frame, text="No videos found.", foreground="gray").pack(anchor="w", padx=8, pady=2)

        stop_btn = ttk.Button(self.controls_frame, text="Stop Video", command=self.stop_video)
        stop_btn.pack(fill='x', pady=(6,10), padx=6)

        # -------- Audio buttons (NEW: trigger playback on phone) --------
        ttk.Separator(self.controls_frame).pack(fill='x', padx=6, pady=6)
        ttk.Label(self.controls_frame, text="🔊 Remote Audio (plays on phone)", font=("Segoe UI", 11, "bold")).pack(anchor="w", padx=6, pady=(2,2))

        if audio_files:
            for idx, af in enumerate(audio_files[:20]):
                name = os.path.basename(af)
                btn = ttk.Button(self.controls_frame, text=f"Audio {idx+1}: {name}",
                                 command=lambda fn=name: self.play_audio_on_clients(fn))
                btn.pack(fill='x', pady=2, padx=6)
        else:
            ttk.Label(self.controls_frame, text="No audio files found.", foreground="gray").pack(anchor="w", padx=8, pady=2)

        self.status_var = tk.StringVar(value="No video loaded")
        ttk.Label(self.controls_frame, textvariable=self.status_var).pack(pady=6)

        self.after(10, self.update_frame)

        # Bind keys for fullscreen toggle
        self.bind("<F11>", self.toggle_fullscreen)
        self.bind("<Escape>", self.exit_fullscreen)

    def toggle_fullscreen(self, event=None):
        self.fullscreen = not self.fullscreen
        self.attributes("-fullscreen", self.fullscreen)

    def exit_fullscreen(self, event=None):
        if self.fullscreen:
            self.fullscreen = False
            self.attributes("-fullscreen", False)

    def play_video(self, path):
        try:
            controller.open_video(path)
            self.status_var.set(f"Playing video: {os.path.basename(path)}")
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def stop_video(self):
        controller.stop()
        self.status_var.set("Video stopped")

    def play_audio_on_clients(self, filename):
        # Broadcast an SSE to all connected phones to play this audio file
        event = {"type": "play", "file": filename, "ts": time.time()}
        _broadcast_audio_event(event)
        self.status_var.set(f"Triggered audio on clients: {filename}")

    def update_frame(self):
        global current_frame_jpeg
        if controller.playing:
            frame, fps = controller.read_frame()
            if frame is not None:
                rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                img = Image.fromarray(rgb)
                img = img.resize((VIDEO_WIDTH, VIDEO_HEIGHT))
                imgtk = ImageTk.PhotoImage(img)
                self.canvas.create_image(VIDEO_WIDTH//2, VIDEO_HEIGHT//2, image=imgtk, anchor="center")
                self.canvas.image = imgtk

                _, jpeg = cv2.imencode('.jpg', cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR))
                with frame_lock:
                    current_frame_jpeg = jpeg.tobytes()
        self.after(10, self.update_frame)

def list_video_files(directory):
    exts = {'.mp4', '.avi', '.mov', '.mkv', '.webm', '.wmv'}
    if not os.path.isdir(directory):
        return []
    return [os.path.join(directory, f) for f in os.listdir(directory)
            if os.path.splitext(f)[1].lower() in exts]

def list_audio_files(directory):
    exts = {'.mp3', '.wav', '.ogg'}
    if not os.path.isdir(directory):
        return []
    return [os.path.join(directory, f) for f in os.listdir(directory)
            if os.path.splitext(f)[1].lower() in exts]

def get_local_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except:
        return "127.0.0.1"

if __name__ == "__main__":
    videos = list_video_files(VIDEOS_DIR)
    audios = list_audio_files(AUDIO_DIR)

    # Start Flask server
    threading.Thread(target=run_flask, daemon=True).start()

    # Start desktop GUI
    app_gui = VideoApp(videos, audios)
    app_gui.mainloop()
