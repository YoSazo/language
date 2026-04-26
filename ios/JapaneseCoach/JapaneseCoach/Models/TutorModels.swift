import Foundation

enum TutorMode: String, CaseIterable, Identifiable {
    case conversation
    case translateHelp
    case shadowing

    var id: String { rawValue }

    var title: String {
        switch self {
        case .conversation:
            return "Conversation"
        case .translateHelp:
            return "How Do I Say This?"
        case .shadowing:
            return "Shadow Last Line"
        }
    }

    var subtitle: String {
        switch self {
        case .conversation:
            return "Speak Japanese and keep the conversation moving."
        case .translateHelp:
            return "Speak English and get natural Japanese back."
        case .shadowing:
            return "Repeat the last line and get a closeness score."
        }
    }

    var socketMode: String {
        switch self {
        case .conversation:
            return "conversation"
        case .translateHelp:
            return "translate_help"
        case .shadowing:
            return "shadowing"
        }
    }
}

enum ConnectionState: String {
    case disconnected
    case connecting
    case connected
}

struct TurnResult {
    let mode: String
    let transcript: String
    let assistantJapanese: String
    let assistantEnglishHint: String?
    let pronunciationScore: Int?
    let pronunciationFeedback: String?
    let model: String?
    let knownWords: Int?
    let totalWords: Int?
}

