import AVFoundation

enum AudioCaptureError: LocalizedError {
    case missingInputNode
    case converterUnavailable

    var errorDescription: String? {
        switch self {
        case .missingInputNode:
            return "Could not access the microphone input node."
        case .converterUnavailable:
            return "Could not create the audio converter for 16 kHz mono streaming."
        }
    }
}

final class AudioCaptureService {
    private let engine = AVAudioEngine()
    private var converter: AVAudioConverter?
    private var isStreaming = false

    func requestPermission() async -> Bool {
        await withCheckedContinuation { continuation in
            AVAudioSession.sharedInstance().requestRecordPermission { granted in
                continuation.resume(returning: granted)
            }
        }
    }

    func startStreaming(onChunk: @escaping (Data) -> Void) throws {
        guard !isStreaming else { return }

        let session = AVAudioSession.sharedInstance()
        try session.setCategory(.playAndRecord, mode: .measurement, options: [.defaultToSpeaker, .allowBluetooth])
        try session.setPreferredSampleRate(16_000)
        try session.setActive(true)

        let inputNode = engine.inputNode
        let inputFormat = inputNode.outputFormat(forBus: 0)
        guard let outputFormat = AVAudioFormat(
            commonFormat: .pcmFormatInt16,
            sampleRate: 16_000,
            channels: 1,
            interleaved: true
        ) else {
            throw AudioCaptureError.converterUnavailable
        }

        guard let converter = AVAudioConverter(from: inputFormat, to: outputFormat) else {
            throw AudioCaptureError.converterUnavailable
        }
        self.converter = converter

        inputNode.removeTap(onBus: 0)
        engine.stop()
        engine.reset()
        inputNode.installTap(onBus: 0, bufferSize: 2_048, format: inputFormat) { [weak self] buffer, _ in
            guard let self, let converter = self.converter else { return }
            var sourceBuffer: AVAudioPCMBuffer? = buffer
            let ratio = outputFormat.sampleRate / inputFormat.sampleRate
            let frameCapacity = AVAudioFrameCount(Double(buffer.frameLength) * ratio) + 32
            guard let convertedBuffer = AVAudioPCMBuffer(pcmFormat: outputFormat, frameCapacity: frameCapacity) else {
                return
            }

            var error: NSError?
            let status = converter.convert(to: convertedBuffer, error: &error) { _, outStatus in
                if let current = sourceBuffer {
                    outStatus.pointee = .haveData
                    sourceBuffer = nil
                    return current
                }
                outStatus.pointee = .endOfStream
                return nil
            }

            guard error == nil, status != .error else { return }
            guard let channelData = convertedBuffer.int16ChannelData else { return }
            let byteCount = Int(convertedBuffer.frameLength) * MemoryLayout<Int16>.size
            let data = Data(bytes: channelData.pointee, count: byteCount)
            if !data.isEmpty {
                onChunk(data)
            }
        }

        engine.prepare()
        try engine.start()
        isStreaming = true
    }

    func stop() {
        guard isStreaming || engine.isRunning else { return }
        engine.inputNode.removeTap(onBus: 0)
        engine.stop()
        engine.reset()
        converter = nil
        try? AVAudioSession.sharedInstance().setActive(false, options: [.notifyOthersOnDeactivation])
        isStreaming = false
    }
}
