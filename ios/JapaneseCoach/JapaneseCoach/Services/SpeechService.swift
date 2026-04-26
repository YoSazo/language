import AVFoundation

final class SpeechService: NSObject {
    private let synthesizer = AVSpeechSynthesizer()

    func speakJapanese(_ text: String) {
        speak(text, locale: "ja-JP", rate: 0.48)
    }

    func speakEnglish(_ text: String) {
        speak(text, locale: "en-US", rate: 0.46)
    }

    func stop() {
        synthesizer.stopSpeaking(at: .immediate)
    }

    private func speak(_ text: String, locale: String, rate: Float) {
        guard !text.isEmpty else { return }
        stop()
        let utterance = AVSpeechUtterance(string: text)
        utterance.voice = AVSpeechSynthesisVoice(language: locale)
        utterance.rate = rate
        utterance.prefersAssistiveTechnologySettings = true
        synthesizer.speak(utterance)
    }
}

