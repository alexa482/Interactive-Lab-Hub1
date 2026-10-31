"""Offline phrase trigger adapted from Lab 3/speech-scripts/listen.py."""
import re
from pathlib import Path
import numpy as np
import sherpa_onnx
import sounddevice as sd
from faster_whisper import WhisperModel
SAMPLE_RATE = 16000

def build_vad(model_path: Path, min_silence: float, min_speech: float):
    """Returns (detector, window_size)."""
    config = sherpa_onnx.VadModelConfig()
    config.silero_vad.model = str(model_path)
    config.silero_vad.min_silence_duration = min_silence
    config.silero_vad.min_speech_duration = min_speech
    config.sample_rate = SAMPLE_RATE
    detector = sherpa_onnx.VoiceActivityDetector(config, buffer_size_in_seconds=30)
    return detector, config.silero_vad.window_size


def normalized(text):
    return " ".join(re.findall(r"[a-z]+", text.lower()))


def wait_for_phrase(model_path, device=None):
    if not model_path.is_file():
        raise RuntimeError(f"Missing VAD model: {model_path}; see README setup")
    # Download tiny.en during setup; runtime never needs network access.
    recognizer = WhisperModel("tiny.en", device="cpu", compute_type="int8",
                              local_files_only=True)
    vad, window = build_vad(model_path, .5, .25)
    with sd.InputStream(channels=1, dtype="float32", samplerate=SAMPLE_RATE,
                        device=device) as stream:
        while True:
            chunk, overflow = stream.read(window)
            if overflow:
                vad.reset()
                continue
            vad.accept_waveform(chunk.reshape(-1))
            while not vad.empty():
                utterance = np.array(vad.front.samples, dtype=np.float32)
                vad.pop()
                segments, _ = recognizer.transcribe(utterance, beam_size=1,
                                                    language="en")
                text = normalized(" ".join(s.text for s in segments))
                if text == "have a colorful night":
                    return  # microphone closes before sensing starts
