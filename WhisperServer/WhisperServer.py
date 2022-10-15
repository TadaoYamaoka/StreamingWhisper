import whisper
import socket
import threading
import queue
import numpy as np
import argparse

SAMPLE_RATE = 16000
INTERVAL = 3
BUFFER_SIZE = 4096

parser = argparse.ArgumentParser()
parser.add_argument('--address', default='127.0.0.1')
parser.add_argument('--port', type=int, default=50000)
parser.add_argument('--model', default='base')
args = parser.parse_args()

print('Loading model...')
model = whisper.load_model(args.model)
print('Done')

s = socket.socket(socket.AF_INET)
s.bind((args.address, args.port))
s.listen()

q = queue.Queue()
b = np.ones(100) / 100

def recieve():
    while True:
        try:
            print('Listening...')
            cilent, address = s.accept()
            print(f'Connected from {address}')

            audio = np.empty(SAMPLE_RATE * INTERVAL + BUFFER_SIZE, dtype=np.float32)
            n = 0
            while True:
                while n < SAMPLE_RATE * INTERVAL:
                    cilent.settimeout(INTERVAL)
                    try:
                        data = cilent.recv(BUFFER_SIZE)
                    except socket.timeout:
                        break
                    finally:
                        cilent.settimeout(None)
                    data = np.frombuffer(data, dtype=np.int16)
                    audio[n:n+len(data)] = data.astype(np.float32) / 32768
                    n += len(data)
                if n > 0:
                    # find silent periods
                    m = n * 4 // 5
                    vol = np.convolve(audio[m:n] ** 2, b, 'same')
                    m += vol.argmin()
                    q.put(audio[:m])

                    audio_prev = audio
                    audio = np.empty(SAMPLE_RATE * INTERVAL + BUFFER_SIZE, dtype=np.float32)
                    audio[:n-m] = audio_prev[m:n]
                    n = n-m
        finally:
            cilent.close()

th_recieve = threading.Thread(target=recieve)
th_recieve.start()


options = whisper.DecodingOptions()

while True:
    audio = q.get()
    if (audio ** 2).max() > 0.001:
        audio = whisper.pad_or_trim(audio)

        # make log-Mel spectrogram and move to the same device as the model
        mel = whisper.log_mel_spectrogram(audio).to(model.device)

        # detect the spoken language
        _, probs = model.detect_language(mel)

        # decode the audio
        result = whisper.decode(model, mel, options)

        # print the recognized text
        print(f'{max(probs, key=probs.get)}: {result.text}')
