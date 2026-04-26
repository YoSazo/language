import Foundation

final class WebSocketService {
    enum Event {
        case connected
        case disconnected
        case text(String)
        case failure(String)
    }

    var onEvent: ((Event) -> Void)?

    private var session: URLSession?
    private var task: URLSessionWebSocketTask?
    private var isConnected = false
    private let sendQueue = DispatchQueue(label: "JapaneseCoach.WebSocketSendQueue")

    func connect(url: URL) {
        disconnect()
        session = URLSession(configuration: .default)
        task = session?.webSocketTask(with: url)
        task?.resume()
        isConnected = true
        DispatchQueue.main.async { self.onEvent?(.connected) }
        receiveLoop()
    }

    func disconnect() {
        isConnected = false
        task?.cancel(with: .goingAway, reason: nil)
        task = nil
        session?.invalidateAndCancel()
        session = nil
        DispatchQueue.main.async { self.onEvent?(.disconnected) }
    }

    func sendJSON(_ payload: [String: Any]) {
        guard let data = try? JSONSerialization.data(withJSONObject: payload),
              let text = String(data: data, encoding: .utf8) else { return }
        sendQueue.async { [weak self] in
            guard let self, let task = self.task else { return }
            task.send(.string(text)) { [weak self] error in
                if let error {
                    DispatchQueue.main.async {
                        self?.onEvent?(.failure(error.localizedDescription))
                    }
                }
            }
        }
    }

    func sendAudio(_ data: Data) {
        guard !data.isEmpty else { return }
        sendQueue.async { [weak self] in
            guard let self, let task = self.task else { return }
            task.send(.data(data)) { [weak self] error in
                if let error {
                    DispatchQueue.main.async {
                        self?.onEvent?(.failure(error.localizedDescription))
                    }
                }
            }
        }
    }

    private func receiveLoop() {
        guard let task, isConnected else { return }
        task.receive { [weak self] result in
            guard let self else { return }
            switch result {
            case .failure(let error):
                DispatchQueue.main.async {
                    self.onEvent?(.failure(error.localizedDescription))
                    self.onEvent?(.disconnected)
                }
            case .success(let message):
                switch message {
                case .string(let text):
                    DispatchQueue.main.async { self.onEvent?(.text(text)) }
                case .data:
                    break
                @unknown default:
                    break
                }
                self.receiveLoop()
            }
        }
    }
}
