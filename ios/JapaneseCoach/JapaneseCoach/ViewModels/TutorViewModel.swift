import Foundation

@MainActor
final class TutorViewModel: ObservableObject {
    @Published var connectionState: ConnectionState = .disconnected
    @Published var selectedMode: TutorMode = .conversation
    @Published var isRecording = false
    @Published var statusText = "Enter your PC address and connect."
    @Published var helperText = "Stay in Japanese as much as possible. Use English help only when you truly need it."
    @Published var transcriptText = ""
    @Published var assistantText = ""
    @Published var englishHintText = ""
    @Published var modelText = ""
    @Published var vocabText = ""
    @Published var pronunciationText = ""

    let settings = AppSettings()

    private let webSocket = WebSocketService()
    private let audioCapture = AudioCaptureService()
    private let speech = SpeechService()

    init() {
        webSocket.onEvent = { [weak self] event in
            Task { @MainActor in
                self?.handle(event: event)
            }
        }
    }

    func connect() {
        guard let url = settings.websocketURL else {
            statusText = "That server address is not valid."
            return
        }
        connectionState = .connecting
        statusText = "Connecting to your PC..."
        webSocket.connect(url: url)
    }

    func disconnect() {
        if isRecording {
            endTalking()
        }
        webSocket.disconnect()
        connectionState = .disconnected
        statusText = "Disconnected."
    }

    func beginTalking() {
        guard connectionState == .connected, !isRecording else { return }

        if selectedMode == .shadowing && assistantText.isEmpty {
            statusText = "Say one line in Conversation mode first, then shadow it."
            return
        }

        Task {
            let granted = await audioCapture.requestPermission()
            guard granted else {
                statusText = "Microphone permission was denied."
                return
            }

            do {
                var payload: [String: Any] = [
                    "type": "start_turn",
                    "mode": selectedMode.socketMode,
                ]
                if selectedMode == .shadowing {
                    payload["target_text"] = assistantText
                }
                webSocket.sendJSON(payload)
                try audioCapture.startStreaming { [weak self] data in
                    self?.webSocket.sendAudio(data)
                }
                isRecording = true
                pronunciationText = ""
                statusText = "Listening..."
            } catch {
                statusText = error.localizedDescription
            }
        }
    }

    func endTalking() {
        guard isRecording else { return }
        audioCapture.stop()
        webSocket.sendJSON(["type": "end_audio"])
        isRecording = false
        statusText = "Sending..."
    }

    func explainLast() {
        guard connectionState == .connected else { return }
        webSocket.sendJSON(["type": "explain_last"])
    }

    func repeatLast() {
        speech.speakJapanese(assistantText)
    }

    func stopSpeaking() {
        speech.stop()
    }

    private func handle(event: WebSocketService.Event) {
        switch event {
        case .connected:
            connectionState = .connected
            statusText = "Connected. Starting session..."
            webSocket.sendJSON([
                "type": "hello",
                "deviceName": "iPhone",
                "appVersion": "0.1.0",
            ])
        case .disconnected:
            connectionState = .disconnected
            isRecording = false
        case .failure(let message):
            statusText = message
        case .text(let text):
            handleServerText(text)
        }
    }

    private func handleServerText(_ text: String) {
        guard let data = text.data(using: .utf8),
              let payload = try? JSONSerialization.jsonObject(with: data) as? [String: Any],
              let type = payload["type"] as? String else {
            statusText = "The server sent something unreadable."
            return
        }

        switch type {
        case "session_ready":
            assistantText = payload["greeting"] as? String ?? ""
            modelText = [payload["chatModel"], payload["utilityModel"]]
                .compactMap { $0 as? String }
                .joined(separator: " / ")
            updateVocabText(payload: payload)
            helperText = "Conversation is live. Hold to talk, release to send."
            statusText = "Connected and ready."
            if settings.autoSpeakGreeting {
                speech.speakJapanese(assistantText)
            }
        case "status":
            if let stage = payload["stage"] as? String {
                switch stage {
                case "listening":
                    statusText = "Listening..."
                case "transcribing":
                    statusText = "Transcribing..."
                case "thinking":
                    statusText = "Thinking..."
                default:
                    statusText = "Ready."
                }
            }
        case "turn_result":
            let result = TurnResult(
                mode: payload["mode"] as? String ?? "",
                transcript: payload["transcript"] as? String ?? "",
                assistantJapanese: payload["assistantJapanese"] as? String ?? "",
                assistantEnglishHint: payload["assistantEnglishHint"] as? String,
                pronunciationScore: payload["pronunciationScore"] as? Int,
                pronunciationFeedback: payload["pronunciationFeedback"] as? String,
                model: payload["model"] as? String,
                knownWords: payload["knownWords"] as? Int,
                totalWords: payload["totalWords"] as? Int
            )
            apply(result: result)
        case "explain_result":
            let english = payload["english"] as? String ?? ""
            let note = payload["note"] as? String ?? ""
            englishHintText = english
            helperText = note
            speech.speakEnglish(english)
            statusText = "Explained."
        case "repeat_result":
            if let japanese = payload["assistantJapanese"] as? String {
                speech.speakJapanese(japanese)
            }
        case "error":
            statusText = payload["message"] as? String ?? "Unknown server error."
        default:
            break
        }
    }

    private func apply(result: TurnResult) {
        transcriptText = result.transcript
        updateVocabText(knownWords: result.knownWords, totalWords: result.totalWords)

        switch result.mode {
        case "shadowing":
            pronunciationText = "Shadow score: \(result.pronunciationScore ?? 0)/100\n\(result.pronunciationFeedback ?? "")"
            helperText = result.pronunciationFeedback ?? ""
            statusText = "Shadow check finished."
        case "translate_help":
            assistantText = result.assistantJapanese
            englishHintText = result.assistantEnglishHint ?? result.transcript
            helperText = "Use that Japanese line, then switch back to Conversation and say it aloud."
            statusText = "Japanese line ready."
            if settings.autoSpeakJapanese {
                speech.speakJapanese(result.assistantJapanese)
            }
        default:
            assistantText = result.assistantJapanese
            englishHintText = ""
            pronunciationText = ""
            helperText = "Keep the conversation moving. If you get stuck, use Explain Last or How Do I Say This?"
            statusText = "Reply ready."
            if settings.autoSpeakJapanese {
                speech.speakJapanese(result.assistantJapanese)
            }
        }

        if let model = result.model {
            modelText = model
        }
    }

    private func updateVocabText(payload: [String: Any]) {
        updateVocabText(
            knownWords: payload["knownWords"] as? Int,
            totalWords: payload["totalWords"] as? Int
        )
    }

    private func updateVocabText(knownWords: Int?, totalWords: Int?) {
        guard let knownWords, let totalWords else { return }
        vocabText = "Known words: \(knownWords) / \(totalWords)"
    }
}
