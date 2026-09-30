import subprocess
from datetime import datetime
from pathlib import Path

from faster_whisper import WhisperModel


# -----------------------------
# SETTINGS
# -----------------------------

RECORDING_SECONDS = 15
WHISPER_MODEL = "base.en"

# Create a folder for diary entries
DIARY_DIR = Path("diary_entries")
DIARY_DIR.mkdir(exist_ok=True)


# -----------------------------
# CREATE NEW ENTRY
# -----------------------------

# Give this entry a unique timestamp
timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")

audio_file = DIARY_DIR / f"{timestamp}_original.wav"
transcript_file = DIARY_DIR / f"{timestamp}_transcript.txt"


# -----------------------------
# RECORD AUDIO
# -----------------------------

print("\nTell me about your day.")
print(f"Recording for {RECORDING_SECONDS} seconds...\n")

subprocess.run([
    "arecord",
    "-d", str(RECORDING_SECONDS),
    "-f", "S16_LE",
    "-c", "1",
    "-r", "16000",
    str(audio_file)
], check=True)

print("\nRecording complete.")


# -----------------------------
# TRANSCRIBE AUDIO
# -----------------------------

print("Transcribing...")

model = WhisperModel(
    WHISPER_MODEL,
    compute_type="int8"
)

segments, info = model.transcribe(
    str(audio_file),
    beam_size=1
)

transcript = " ".join(
    segment.text.strip()
    for segment in segments
)


# -----------------------------
# SAVE TRANSCRIPT
# -----------------------------

with open(transcript_file, "w") as file:
    file.write(transcript)


# -----------------------------
# SHOW RESULT
# -----------------------------

print("\n-------------------------")
print("DIARY ENTRY")
print("-------------------------")
print(transcript)

print("\nSaved:")
print(f"Audio:      {audio_file}")
print(f"Transcript: {transcript_file}")