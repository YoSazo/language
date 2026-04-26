import Foundation

final class AppSettings: ObservableObject {
    @Published var serverHost: String {
        didSet { UserDefaults.standard.set(serverHost, forKey: Keys.serverHost) }
    }

    @Published var autoSpeakJapanese: Bool {
        didSet { UserDefaults.standard.set(autoSpeakJapanese, forKey: Keys.autoSpeakJapanese) }
    }

    @Published var autoSpeakGreeting: Bool {
        didSet { UserDefaults.standard.set(autoSpeakGreeting, forKey: Keys.autoSpeakGreeting) }
    }

    private enum Keys {
        static let serverHost = "serverHost"
        static let autoSpeakJapanese = "autoSpeakJapanese"
        static let autoSpeakGreeting = "autoSpeakGreeting"
    }

    init() {
        serverHost = UserDefaults.standard.string(forKey: Keys.serverHost) ?? "192.168.1.10:8765"
        if UserDefaults.standard.object(forKey: Keys.autoSpeakJapanese) == nil {
            UserDefaults.standard.set(true, forKey: Keys.autoSpeakJapanese)
        }
        if UserDefaults.standard.object(forKey: Keys.autoSpeakGreeting) == nil {
            UserDefaults.standard.set(true, forKey: Keys.autoSpeakGreeting)
        }
        autoSpeakJapanese = UserDefaults.standard.bool(forKey: Keys.autoSpeakJapanese)
        autoSpeakGreeting = UserDefaults.standard.bool(forKey: Keys.autoSpeakGreeting)
    }

    var websocketURL: URL? {
        let trimmed = serverHost.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !trimmed.isEmpty else { return nil }
        if trimmed.hasPrefix("ws://") || trimmed.hasPrefix("wss://") {
            return URL(string: trimmed)
        }
        return URL(string: "ws://\(trimmed)/ws")
    }
}

