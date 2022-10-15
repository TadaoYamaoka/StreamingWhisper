using NAudio.Wave;
using System.Net;
using System.Net.Sockets;

const int SAMPLE_RATE = 16000;

var capture = new WasapiLoopbackCapture();
// optionally we can set the capture waveformat here: e.g. capture.WaveFormat = new WaveFormat(44100, 16,2);
capture.WaveFormat = new WaveFormat(SAMPLE_RATE, 16, 1);

// socket client
var host = args.Length > 0 ? args[0] : "127.0.0.1";
var port = args.Length > 1 ? Int32.Parse(args[1]) : 50000;
var tcpClient = new System.Net.Sockets.TcpClient(host, port);
var stream = tcpClient.GetStream();

capture.DataAvailable += (s, a) =>
{
    stream.Write(a.Buffer, 0, a.BytesRecorded);
};

capture.RecordingStopped += (s, a) =>
{
    capture.Dispose();
};

capture.StartRecording();
while (capture.CaptureState != NAudio.CoreAudioApi.CaptureState.Stopped)
{
    Thread.Sleep(500);
}